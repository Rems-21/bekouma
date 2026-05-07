import json
import uuid
from datetime import date

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from cart.models import LiveLocationPing, Reservation
from equipment.models import Category, Equipment

from .models import HeroSlide, SiteInfo
from .staff_zone_data import build_staff_zone_monitor_data, ensure_live_tracking_token, get_reservation_for_live_token


def _staff_user(u):
    return u.is_authenticated and u.is_staff


def home(request):
    slides = HeroSlide.objects.filter(is_active=True)
    categories = Category.objects.all()
    featured = Equipment.objects.filter(is_available=True)[:8]
    site_info = SiteInfo.objects.first()

    context = {
        'slides': slides,
        'categories': categories,
        'featured_equipments': featured,
        'site_info': site_info,
    }
    return render(request, 'core/home.html', context)


def about(request):
    site_info = SiteInfo.objects.first()
    return render(request, 'core/about.html', {'site_info': site_info})


def contact(request):
    site_info = SiteInfo.objects.first()
    return render(request, 'core/contact.html', {'site_info': site_info})


@user_passes_test(_staff_user)
def staff_declared_zone_monitor(request):
    default_radius = float(getattr(settings, 'DECLARED_ZONE_ALERT_RADIUS_KM', 3))
    try:
        radius_km = float(request.GET.get('radius_km', default_radius))
    except (TypeError, ValueError):
        radius_km = default_radius
    radius_km = max(0.1, min(radius_km, 200.0))

    data = build_staff_zone_monitor_data(request, radius_km)
    json_path = reverse('core:staff_zone_monitor_json')
    qs = request.META.get('QUERY_STRING', '')
    positions_poll_url = request.build_absolute_uri(json_path + ('?' + qs if qs else ''))

    return render(
        request,
        'core/staff_zone_monitor.html',
        {
            'radius_km': radius_km,
            'default_radius_km': default_radius,
            'fleet_json': json.dumps(data['fleet']),
            'deviation_markers_json': json.dumps(data['deviation_markers']),
            'alerts_json': json.dumps(data['alerts']),
            'tracking_links_json': json.dumps(data['tracking_links']),
            'positions_poll_url': positions_poll_url,
            'server_clock_iso': data['server_clock_iso'],
            'today': data['today'],
            'stats': data['stats'],
        },
    )


@user_passes_test(_staff_user)
def staff_zone_monitor_positions_json(request):
    default_radius = float(getattr(settings, 'DECLARED_ZONE_ALERT_RADIUS_KM', 3))
    try:
        radius_km = float(request.GET.get('radius_km', default_radius))
    except (TypeError, ValueError):
        radius_km = default_radius
    radius_km = max(0.1, min(radius_km, 200.0))

    data = build_staff_zone_monitor_data(request, radius_km)
    return JsonResponse(
        {
            'fleet': data['fleet'],
            'deviations': data['deviation_markers'],
            'alerts': data['alerts'],
            'stats': data['stats'],
            'tracking_links': data['tracking_links'],
            'server_clock_iso': data['server_clock_iso'],
        }
    )


def live_tracking_mobile(request, token):
    try:
        uid = uuid.UUID(str(token))
    except (ValueError, TypeError):
        return render(request, 'core/live_tracking_mobile.html', {'error': 'Lien invalide.', 'ping_url': ''}, status=404)

    reservation = get_reservation_for_live_token(uid)
    if not reservation:
        return render(
            request,
            'core/live_tracking_mobile.html',
            {'error': 'Lien expiré ou désactivé.', 'ping_url': ''},
            status=410,
        )

    ping_url = request.build_absolute_uri(
        request.path.rstrip('/') + '/ping/'
    )
    return render(
        request,
        'core/live_tracking_mobile.html',
        {
            'error': '',
            'ping_url': ping_url,
            'equipment_name': reservation.equipment.name,
            'reservation_id': reservation.pk,
        },
    )


@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def live_tracking_ping(request, token):
    if request.method == 'OPTIONS':
        return JsonResponse({'ok': True})

    try:
        uid = uuid.UUID(str(token))
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'invalid_token'}, status=400)

    reservation = get_reservation_for_live_token(uid)
    if not reservation:
        return JsonResponse({'ok': False, 'error': 'expired'}, status=410)

    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'json'}, status=400)

    try:
        lat = float(body.get('latitude'))
        lng = float(body.get('longitude'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'coordinates'}, status=400)

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
        return JsonResponse({'ok': False, 'error': 'out_of_range'}, status=400)

    acc = body.get('accuracy')
    try:
        acc_f = float(acc) if acc is not None else None
    except (TypeError, ValueError):
        acc_f = None

    LiveLocationPing.objects.create(
        reservation=reservation,
        latitude=lat,
        longitude=lng,
        accuracy_m=acc_f,
    )
    return JsonResponse({'ok': True})

def google_verification(request):
    site_info = SiteInfo.objects.first()
    if site_info and site_info.google_verification_code:
        return render(request, 'core/google2c82be27c4a4a6e2.html', {'code': site_info})
    else:
        return render(request, 'core/google2c82be27c4a4a6e2.html', {'code': ''}, status=404)