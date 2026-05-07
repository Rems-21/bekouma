"""Finalisation idempotente d'un paiement réussi (webhook, retour client, simulation)."""
from __future__ import annotations

from django.db import transaction

from accounts.models import Notification
from blockchain.utils import record_transaction
from cart.models import CartItem, Order
from .models import Payment


def mark_payment_completed(payment: Payment, gateway_extra: dict | None = None) -> bool:
    """
    Passe la commande en payée, confirme les réservations, chaîne blockchain, vide le panier.
    Verrouille le paiement pour éviter un double traitement concurrent (webhook + callback).
    """
    with transaction.atomic():
        locked = Payment.objects.select_for_update().get(pk=payment.pk)
        if locked.status == 'completed':
            return False

        locked.status = 'completed'
        if gateway_extra:
            base = locked.gateway_data if isinstance(locked.gateway_data, dict) else {}
            locked.gateway_data = {**base, **gateway_extra}
        locked.save()

        order = Order.objects.select_for_update().get(pk=locked.order_id)
        order.status = 'paid'
        order.save()

        for res in order.reservations.all():
            res.status = 'confirmed'
            block = record_transaction('reservation_confirmed', {
                'reservation_id': res.pk,
                'equipment': res.equipment.name,
                'user': res.user.username,
                'amount': res.total_price,
                'rental_date': str(res.rental_date),
                'return_date': str(res.return_date),
            })
            res.blockchain_hash = block.hash
            res.save()

        block = record_transaction('payment_completed', {
            'order_id': order.pk,
            'amount': order.total_amount,
            'payment_ref': locked.transaction_id,
            'user': order.user.username,
        })
        order.blockchain_hash = block.hash
        order.save()

        CartItem.objects.filter(user=order.user).delete()

        Notification.objects.create(
            user=order.user,
            notification_type='payment',
            title='Paiement confirmé',
            message=f'Votre paiement de {order.total_amount:,} FCFA a été confirmé. Commande #{order.pk}.',
            link=f'/contrats/generate/{order.pk}/',
        )
    return True


def mark_payment_failed(payment: Payment, gateway_extra: dict | None = None) -> None:
    with transaction.atomic():
        locked = Payment.objects.select_for_update().get(pk=payment.pk)
        if locked.status == 'completed':
            return
        locked.status = 'failed'
        if gateway_extra:
            base = locked.gateway_data if isinstance(locked.gateway_data, dict) else {}
            locked.gateway_data = {**base, **gateway_extra}
        locked.save()
