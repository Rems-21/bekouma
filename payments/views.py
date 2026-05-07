import json
import uuid
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from accounts.kyc import kyc_redirect_message, user_can_rent
from cart.models import CartItem, EquipmentMovement, Order, Reservation

from .models import Payment
from .notchpay import (
    extract_transaction,
    initialize_checkout,
    retrieve_payment_for_local_order,
    transaction_status_complete,
    verify_webhook_signature,
)
from .payment_completion import mark_payment_completed, mark_payment_failed


def _payment_return_signer() -> TimestampSigner:
    return TimestampSigner(salt='bekouma.payments.return')


def _sign_payment_return(order_id: int, payment_id: int) -> str:
    return _payment_return_signer().sign(f'{order_id}:{payment_id}')


def _unsign_payment_return(sig: str) -> tuple[int, int] | None:
    try:
        raw = _payment_return_signer().unsign(sig, max_age=7 * 86400)
        a, b = raw.split(':', 1)
        return int(a), int(b)
    except (BadSignature, SignatureExpired, ValueError):
        return None


@login_required
def checkout(request):
    if not user_can_rent(request.user):
        messages.warning(request, kyc_redirect_message())
        return redirect('accounts:kyc')
    items = CartItem.objects.filter(user=request.user).select_related('equipment')
    if not items.exists():
        messages.error(request, 'Votre panier est vide.')
        return redirect('cart:view')

    total = sum(item.subtotal for item in items)
    rental_date = items.first().rental_date
    return_date = items.first().return_date

    context = {
        'items': items,
        'total': total,
        'rental_date': rental_date,
        'return_date': return_date,
    }
    return render(request, 'payments/checkout.html', context)


@login_required
def select_location(request):
    if not user_can_rent(request.user):
        messages.warning(request, kyc_redirect_message())
        return redirect('accounts:kyc')
    items = CartItem.objects.filter(user=request.user).select_related('equipment')
    if not items.exists():
        messages.error(request, 'Votre panier est vide.')
        return redirect('cart:view')

    items_locations = []
    for item in items:
        items_locations.append({
            'item_id': item.id,
            'equipment_name': item.equipment.name,
            'lat': item.equipment.latitude if item.equipment.latitude else 4.0511,
            'lng': item.equipment.longitude if item.equipment.longitude else 9.7679,
            'location': item.equipment.location_name or '',
        })

    context = {
        'items': items,
        'total': sum(item.subtotal for item in items),
        'items_locations_json': json.dumps(items_locations),
    }
    return render(request, 'payments/location.html', context)


def _bek_ref_from_notch_payload(data: dict) -> str | None:
    """Référence locale BEK-… (Notch : merchant_reference / trxref, pas reference trx.test_…)."""
    for key in ('merchant_reference', 'trxref'):
        v = data.get(key)
        if v and str(v).startswith('BEK-'):
            return str(v)
    ref = data.get('reference')
    if ref and str(ref).startswith('BEK-'):
        return str(ref)
    tx = data.get('transaction')
    if isinstance(tx, dict):
        for key in ('merchant_reference', 'trxref'):
            v = tx.get(key)
            if v and str(v).startswith('BEK-'):
                return str(v)
        r = tx.get('reference')
        if r and str(r).startswith('BEK-'):
            return str(r)
    return None


def _notch_trx_ref_from_payload(data: dict) -> str | None:
    ref = data.get('reference')
    if ref and not str(ref).startswith('BEK-'):
        return str(ref)
    tx = data.get('transaction')
    if isinstance(tx, dict):
        r = tx.get('reference')
        if r and not str(r).startswith('BEK-'):
            return str(r)
    return None


def _payment_from_notch_webhook_data(data: dict) -> Payment | None:
    bek = _bek_ref_from_notch_payload(data)
    if bek:
        p = Payment.objects.filter(transaction_id=bek).first()
        if p:
            return p
    trx = _notch_trx_ref_from_payload(data)
    if trx:
        return Payment.objects.filter(
            gateway_data__notchpay_initialize__transaction__reference=trx,
        ).first()
    return None


@login_required
def initiate_payment(request):
    if request.method != 'POST':
        return redirect('payments:location')
    if not user_can_rent(request.user):
        messages.warning(request, kyc_redirect_message())
        return redirect('accounts:kyc')
    items = CartItem.objects.filter(user=request.user).select_related('equipment')
    if not items.exists():
        return redirect('cart:view')

    total = sum(item.subtotal for item in items)
    rental_date = items.first().rental_date
    return_date = items.first().return_date

    order = Order.objects.create(
        user=request.user,
        total_amount=total,
        rental_date=rental_date,
        return_date=return_date,
    )

    reservations = []
    for item in items:
        driver_cost = 0
        if item.with_driver and item.equipment.requires_driver:
            driver_cost = item.equipment.driver_price_per_day * item.num_days

        lat_raw = request.POST.get(f'latitude_{item.id}', '')
        lng_raw = request.POST.get(f'longitude_{item.id}', '')
        loc_name = (request.POST.get(f'location_name_{item.id}', '') or '').strip()
        try:
            declared_lat = float(lat_raw) if lat_raw else float(item.equipment.latitude or 0)
            declared_lng = float(lng_raw) if lng_raw else float(item.equipment.longitude or 0)
        except ValueError:
            declared_lat = float(item.equipment.latitude or 0)
            declared_lng = float(item.equipment.longitude or 0)

        if not loc_name:
            loc_name = item.equipment.location_name or f"{declared_lat:.6f}, {declared_lng:.6f}"

        old_lat = item.equipment.latitude
        old_lng = item.equipment.longitude
        old_loc = item.equipment.location_name or ''

        res = Reservation.objects.create(
            user=request.user,
            equipment=item.equipment,
            quantity=item.quantity,
            with_driver=item.with_driver,
            rental_date=item.rental_date,
            return_date=item.return_date,
            total_price=item.subtotal,
            driver_price=driver_cost,
            declared_latitude=declared_lat,
            declared_longitude=declared_lng,
            declared_location_name=loc_name,
            location_declared_at=timezone.now(),
        )

        item.equipment.latitude = declared_lat
        item.equipment.longitude = declared_lng
        item.equipment.location_name = loc_name
        item.equipment.save(update_fields=['latitude', 'longitude', 'location_name', 'updated_at'])

        EquipmentMovement.objects.create(
            equipment=item.equipment,
            reservation=res,
            user=request.user,
            movement_type='declared',
            old_latitude=old_lat,
            old_longitude=old_lng,
            old_location_name=old_loc,
            new_latitude=declared_lat,
            new_longitude=declared_lng,
            new_location_name=loc_name,
        )

        reservations.append(res)

    order.reservations.set(reservations)

    payment_ref = f"BEK-{order.pk}-{uuid.uuid4().hex[:8].upper()}"
    order.payment_reference = payment_ref
    order.save()

    payment = Payment.objects.create(
        user=request.user,
        order=order,
        amount=total,
        transaction_id=payment_ref,
        payment_method='notchpay',
    )

    # `sig` : finalisation possible au retour Notch Pay même si l’utilisateur n’a pas de session
    # sur le même hôte que le callback (ex. payé via ngrok alors que la session était sur localhost).
    callback = request.build_absolute_uri(reverse('payments:return')) + '?' + urlencode({
        'order_id': str(order.pk),
        'sig': _sign_payment_return(order.pk, payment.pk),
    })

    auth_url, init_payload, err = initialize_checkout(
        amount=int(total),
        currency='XAF',
        reference=payment_ref,
        description=f'Location matériel RAOLY BTP — commande #{order.pk}',
        callback_url=callback,
        email=request.user.email,
        phone=getattr(request.user, 'phone', None),
        customer_name=request.user.get_full_name() or request.user.username,
    )

    if init_payload:
        payment.gateway_data = {'notchpay_initialize': init_payload}
        payment.save(update_fields=['gateway_data', 'updated_at'])

    if auth_url:
        return HttpResponseRedirect(auth_url)

    messages.error(
        request,
        err or 'Impossible de démarrer le paiement Notch Pay. Vérifiez NOTCHPAY_PUBLIC_KEY et le réseau.',
    )
    context = {
        'order': order,
        'payment': payment,
        'total': total,
        'transaction_id': payment_ref,
        'notchpay_error': err,
    }
    return render(request, 'payments/pay.html', context)


@csrf_exempt
def payment_notify(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'ignored'})

    raw = request.body.decode('utf-8')
    signature = request.META.get('HTTP_X_NOTCH_SIGNATURE')

    hash_key = (getattr(settings, 'NOTCHPAY_WEBHOOK_HASH', None) or '').strip()
    if hash_key:
        if not verify_webhook_signature(raw, signature, hash_key):
            return JsonResponse({'error': 'signature invalide'}, status=403)
    elif not settings.DEBUG:
        return JsonResponse({'error': 'webhook non configuré'}, status=503)

    try:
        event = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalide'}, status=400)

    if not isinstance(event, dict):
        return JsonResponse({'error': 'payload invalide'}, status=400)

    # Notch Pay envoie souvent "event" ; d'autres docs utilisent "type"
    event_type = (event.get('type') or event.get('event') or '').strip()
    data = event.get('data')
    if not isinstance(data, dict):
        return JsonResponse({'status': 'ok', 'note': 'no data'})

    payment = _payment_from_notch_webhook_data(data)
    if not payment:
        return JsonResponse({'status': 'ok', 'note': 'unknown reference'})

    if event_type == 'payment.complete':
        mark_payment_completed(payment, {'notchpay_webhook': event})
    elif event_type in ('payment.failed', 'payment.canceled', 'payment.expired'):
        mark_payment_failed(payment, {'notchpay_webhook': event})

    return JsonResponse({'status': 'ok'})


def payment_return(request):
    """
    Retour utilisateur après paiement Notch Pay.
    Non protégé par login_required : la synchro s’appuie sur `sig` (lien signé) pour pouvoir
    confirmer le paiement même quand le navigateur n’a pas de cookie de session sur l’hôte du callback.
    """
    order_id = request.GET.get('order_id')
    sig = request.GET.get('sig')
    order = None
    payment = None

    if order_id and sig:
        ids = _unsign_payment_return(sig)
        if ids:
            oid, pid = ids
            if str(oid) == str(order_id):
                order = Order.objects.filter(pk=oid).first()
                if order:
                    payment = order.payments.filter(pk=pid).first()

    if order is None and request.user.is_authenticated and order_id:
        order = Order.objects.filter(pk=order_id, user=request.user).first()
        if order:
            payment = order.payments.order_by('-pk').first()

    if order is None or payment is None:
        messages.error(
            request,
            'Lien de retour invalide ou expiré. Si le paiement a réussi, connectez-vous puis vérifiez vos réservations.',
        )
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        return redirect(reverse('accounts:login'))

    if order.status != 'paid' and payment.status == 'pending' and order.payment_reference:
        remote = retrieve_payment_for_local_order(order, payment)
        tx = extract_transaction(remote)
        if transaction_status_complete(tx):
            mark_payment_completed(payment, {'notchpay_callback_sync': remote})

    order.refresh_from_db()
    if order.status == 'paid':
        if request.user.is_authenticated and request.user.pk == order.user_id:
            messages.success(request, 'Paiement confirmé. Vous pouvez télécharger votre contrat.')
            return redirect('contracts:generate', order_id=order.pk)
        contract_url = reverse('contracts:generate', kwargs={'order_id': order.pk})
        messages.info(
            request,
            'Paiement confirmé. Connectez-vous pour accéder à votre contrat et à vos notifications.',
        )
        return redirect_to_login(contract_url)

    return render(request, 'payments/return.html', {'order_id': order_id})


@login_required
def sync_order_payment(request, order_id):
    """Re-interroge Notch Pay (utile si le retour auto n’a pas vu le statut « complete »)."""
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    if order.status == 'paid':
        messages.info(request, 'Cette commande est déjà payée.')
        return redirect('contracts:generate', order_id=order.pk)
    payment = order.payments.order_by('-pk').first()
    if not payment or payment.status != 'pending' or not order.payment_reference:
        messages.error(request, 'Aucun paiement en attente pour cette commande.')
        return redirect('accounts:dashboard')
    remote = retrieve_payment_for_local_order(order, payment)
    tx = extract_transaction(remote)
    if transaction_status_complete(tx):
        mark_payment_completed(payment, {'notchpay_manual_sync': remote})
        messages.success(request, 'Paiement confirmé.')
        return redirect('contracts:generate', order_id=order.pk)
    messages.warning(
        request,
        'Notch Pay ne signale pas encore le paiement comme terminé. Réessayez dans quelques instants.',
    )
    return redirect('accounts:dashboard')


@login_required
def simulate_payment(request, order_id):
    """Pour le développement — simule un paiement réussi."""
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    payment = order.payments.first()

    if payment and payment.status == 'pending':
        mark_payment_completed(payment, {'source': 'simulate'})
        messages.success(request, 'Paiement simulé avec succès !')
        return redirect('contracts:generate', order_id=order.pk)

    messages.error(request, 'Impossible de traiter ce paiement.')
    return redirect('accounts:dashboard')
