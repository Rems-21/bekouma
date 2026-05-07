"""Données pour l'écran staff suivi zones + positions live (téléphone)."""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from cart.models import LiveLocationPing, Reservation
from equipment.models import Equipment

from .location_utils import haversine_km


def _live_max_age():
    return int(getattr(settings, 'LIVE_TRACKING_MAX_AGE_MINUTES', 45))


def ensure_live_tracking_token(reservation: Reservation) -> uuid.UUID | None:
    """Crée ou renouvelle le jeton de suivi GPS pour une réservation dans la fenêtre de location."""
    if reservation.status in ('cancelled', 'completed'):
        return None
    today = date.today()
    if reservation.return_date < today or reservation.rental_date > today:
        return None

    now = timezone.now()
    exp = timezone.make_aware(
        datetime.combine(reservation.return_date + timedelta(days=2), time(23, 59, 59)),
        timezone.get_current_timezone(),
    )
    if reservation.live_tracking_token and reservation.live_tracking_expires and reservation.live_tracking_expires > now:
        return reservation.live_tracking_token

    reservation.live_tracking_token = uuid.uuid4()
    reservation.live_tracking_expires = exp
    reservation.save(update_fields=['live_tracking_token', 'live_tracking_expires', 'updated_at'])
    return reservation.live_tracking_token


def get_reservation_for_live_token(token: uuid.UUID) -> Reservation | None:
    return (
        Reservation.objects.filter(
            live_tracking_token=token,
            live_tracking_expires__gt=timezone.now(),
        )
        .select_related('equipment', 'user')
        .first()
    )


def _latest_pings_by_reservation(reservation_ids: list[int], since) -> dict[int, LiveLocationPing]:
    if not reservation_ids:
        return {}
    pings = (
        LiveLocationPing.objects.filter(reservation_id__in=reservation_ids, created_at__gte=since)
        .order_by('-created_at')
    )
    out: dict[int, LiveLocationPing] = {}
    for p in pings:
        if p.reservation_id not in out:
            out[p.reservation_id] = p
    return out


def build_staff_zone_monitor_data(request, radius_km: float) -> dict[str, Any]:
    today = date.today()
    reservations = (
        Reservation.objects.filter(
            rental_date__lte=today,
            return_date__gte=today,
        )
        .exclude(status__in=['cancelled', 'completed'])
        .select_related('equipment', 'user')
        .order_by('return_date', 'equipment__name')
    )
    res_list = list(reservations)
    res_ids = [r.pk for r in res_list]
    since = timezone.now() - timedelta(minutes=_live_max_age())
    latest_ping = _latest_pings_by_reservation(res_ids, since)

    res_ids_by_eq: dict[int, list[int]] = defaultdict(list)
    for r in res_list:
        res_ids_by_eq[r.equipment_id].append(r.pk)

    outside: list[dict[str, Any]] = []
    inside: list[dict[str, Any]] = []
    no_declared_zone: list[Reservation] = []
    no_equipment_position: list[dict[str, Any]] = []

    def _current_for_reservation(res: Reservation) -> tuple[float, float, bool]:
        """(lat, lng, from_live)"""
        ping = latest_ping.get(res.pk)
        if ping:
            return float(ping.latitude), float(ping.longitude), True
        eq = res.equipment
        elat, elng = float(eq.latitude or 0), float(eq.longitude or 0)
        return elat, elng, False

    for res in res_list:
        eq = res.equipment
        d_lat = res.declared_latitude
        d_lng = res.declared_longitude

        if d_lat is None or d_lng is None:
            no_declared_zone.append(res)
            continue

        elat, elng, from_live = _current_for_reservation(res)
        if elat == 0 and elng == 0 and not from_live:
            no_equipment_position.append(
                {
                    'reservation': res,
                    'decl_lat': float(d_lat),
                    'decl_lng': float(d_lng),
                }
            )
            continue

        dist = haversine_km(float(d_lat), float(d_lng), elat, elng)
        row = {
            'reservation': res,
            'distance_km': round(dist, 2),
            'decl_lat': float(d_lat),
            'decl_lng': float(d_lng),
            'current_lat': elat,
            'current_lng': elng,
            'from_live': from_live,
        }
        if dist > radius_km:
            outside.append(row)
        else:
            inside.append(row)

    deviation_markers: list[dict[str, Any]] = []
    for row in outside:
        res = row['reservation']
        eq = res.equipment
        deviation_markers.append(
            {
                'kind': 'outside',
                'equipment': eq.name,
                'reservation_id': res.pk,
                'decl': [row['decl_lat'], row['decl_lng']],
                'curr': [row['current_lat'], row['current_lng']],
                'distance_km': row['distance_km'],
                'from_live': row['from_live'],
            }
        )

    now = timezone.localtime(timezone.now())
    hub_lat, hub_lng = 4.0511, 9.7679

    fleet: list[dict[str, Any]] = []
    for eq in Equipment.objects.select_related('category').all().order_by('name'):
        best_ping: LiveLocationPing | None = None
        for rid in res_ids_by_eq.get(eq.pk, []):
            p = latest_ping.get(rid)
            if p and (best_ping is None or p.created_at > best_ping.created_at):
                best_ping = p

        if best_ping:
            plat, plng = float(best_ping.latitude), float(best_ping.longitude)
            has_fix = True
            has_live = True
            live_age_sec = int((timezone.now() - best_ping.created_at).total_seconds())
        else:
            elat, elng = float(eq.latitude or 0), float(eq.longitude or 0)
            has_fix = not (elat == 0 and elng == 0)
            plat, plng = (elat, elng) if has_fix else (hub_lat, hub_lng)
            has_live = False
            live_age_sec = None

        fleet.append(
            {
                'id': eq.pk,
                'name': eq.name,
                'slug': eq.slug,
                'base_lat': plat,
                'base_lng': plng,
                'has_fix': has_fix,
                'has_live': has_live,
                'live_age_sec': live_age_sec,
                'location': (eq.location_name or '')[:120],
                'category': eq.category.name if eq.category_id else '',
                'is_available': eq.is_available,
            }
        )

    late_reservations = list(
        Reservation.objects.filter(
            Q(status='late')
            | Q(
                return_date__lt=today,
                status__in=['pending', 'confirmed', 'active'],
            ),
        )
        .exclude(status__in=['cancelled', 'completed'])
        .select_related('equipment', 'user')
        .order_by('return_date')
    )

    alerts: list[dict[str, Any]] = []
    tstr = now.strftime('%H:%M:%S')
    for row in outside:
        res = row['reservation']
        src = ' (GPS live)' if row.get('from_live') else ''
        alerts.append(
            {
                'severity': 'critical',
                'time': tstr,
                'title': 'HORS ZONE',
                'body': (
                    f'{res.equipment.name} — rés. #{res.pk} — '
                    f'{row["distance_km"]:.2f} km du point déclaré{src} '
                    f'({res.user.get_full_name() or res.user.username})'
                ),
            }
        )
    for res in no_declared_zone:
        alerts.append(
            {
                'severity': 'warning',
                'time': tstr,
                'title': 'ZONE NON DÉCLARÉE',
                'body': (
                    f'{res.equipment.name} — rés. #{res.pk} — '
                    f'{res.get_status_display()}'
                ),
            }
        )
    for item in no_equipment_position:
        res = item['reservation']
        alerts.append(
            {
                'severity': 'warning',
                'time': tstr,
                'title': 'POSITION ENGIN ABSENTE',
                'body': (
                    f'{res.equipment.name} — rés. #{res.pk} — coordonnées 0;0 en base, pas de ping live'
                ),
            }
        )
    for res in late_reservations:
        alerts.append(
            {
                'severity': 'critical',
                'time': tstr,
                'title': 'LOCATIVE EN RETARD',
                'body': (
                    f'{res.equipment.name} — rés. #{res.pk} — '
                    f'retour prévu {res.return_date:%d/%m/%Y} ({res.get_status_display()})'
                ),
            }
        )
    if not alerts:
        alerts.append(
            {
                'severity': 'info',
                'time': tstr,
                'title': 'SYSTÈME NOMINAL',
                'body': 'Aucune alerte active sur les critères surveillés.',
            }
        )

    alerts_count = sum(1 for a in alerts if a['severity'] in ('critical', 'warning'))

    tracking_links: list[dict[str, Any]] = []
    for res in res_list:
        tok = ensure_live_tracking_token(res)
        if tok:
            path = reverse('core:live_tracking_mobile', kwargs={'token': str(tok)})
            url = request.build_absolute_uri(path) if request else path
            tracking_links.append(
                {
                    'reservation_id': res.pk,
                    'equipment': res.equipment.name,
                    'user': res.user.get_full_name() or res.user.username,
                    'url': url,
                    'expires': res.live_tracking_expires.isoformat() if res.live_tracking_expires else '',
                }
            )

    stats = {
        'fleet_total': len(fleet),
        'rentals_window': len(res_list),
        'outside_count': len(outside),
        'alerts_count': alerts_count,
    }

    return {
        'radius_km': radius_km,
        'fleet': fleet,
        'deviation_markers': deviation_markers,
        'alerts': alerts,
        'stats': stats,
        'tracking_links': tracking_links,
        'today': today,
        'server_clock_iso': now.isoformat(),
    }
