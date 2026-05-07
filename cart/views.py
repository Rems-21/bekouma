from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import CartItem, Reservation, Order, EquipmentMovement
from equipment.models import Equipment
from accounts.models import Notification
from accounts.kyc import kyc_redirect_message, user_can_rent
from datetime import date, timedelta

@login_required
def cart_view(request):
    items = CartItem.objects.filter(user=request.user).select_related('equipment')
    total = sum(item.subtotal for item in items)
    
    if items.exists():
        rental_date = items.first().rental_date
        return_date = items.first().return_date
    else:
        rental_date = None
        return_date = None
    
    context = {
        'items': items,
        'total': total,
        'rental_date': rental_date,
        'return_date': return_date,
    }
    return render(request, 'cart/cart.html', context)

@login_required
def add_to_cart(request, equipment_id):
    if request.method == 'POST':
        if not user_can_rent(request.user):
            messages.warning(request, kyc_redirect_message())
            return redirect('accounts:kyc')
        equipment = get_object_or_404(Equipment, id=equipment_id)
        rental_date_str = request.POST.get('rental_date')
        return_date_str = request.POST.get('return_date')
        with_driver = request.POST.get('with_driver') == 'on'
        quantity = int(request.POST.get('quantity', 1))
        
        if not rental_date_str or not return_date_str:
            messages.error(request, 'Veuillez sélectionner les dates de location.')
            return redirect('equipment:detail', slug=equipment.slug)
        
        from datetime import datetime
        rental_date = datetime.strptime(rental_date_str, '%Y-%m-%d').date()
        return_date = datetime.strptime(return_date_str, '%Y-%m-%d').date()
        
        if rental_date < date.today():
            messages.error(request, 'La date de location ne peut pas être dans le passé.')
            return redirect('equipment:detail', slug=equipment.slug)
        
        if return_date <= rental_date:
            messages.error(request, 'La date de retour doit être après la date de location.')
            return redirect('equipment:detail', slug=equipment.slug)
        
        existing_items = CartItem.objects.filter(user=request.user)
        if existing_items.exists():
            first_item = existing_items.first()
            if first_item.rental_date != rental_date or first_item.return_date != return_date:
                messages.error(request, 'Tous les éléments du panier doivent avoir les mêmes dates de prise et de retour. Videz votre panier pour choisir de nouvelles dates.')
                return redirect('equipment:detail', slug=equipment.slug)
        
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            equipment=equipment,
            rental_date=rental_date,
            defaults={
                'return_date': return_date,
                'with_driver': with_driver,
                'quantity': quantity,
            }
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.with_driver = with_driver
            cart_item.save()
        
        messages.success(request, f'{equipment.name} ajouté au panier.')
        if request.GET.get('redirect') == 'checkout':
            return redirect('payments:checkout')
        return redirect('cart:view')
    return redirect('equipment:list')

@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    item.delete()
    messages.success(request, 'Article retiré du panier.')
    return redirect('cart:view')

@login_required
def clear_cart(request):
    CartItem.objects.filter(user=request.user).delete()
    messages.success(request, 'Panier vidé.')
    return redirect('cart:view')

@login_required
def update_cart_item(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(CartItem, id=item_id, user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        with_driver = request.POST.get('with_driver') == 'on'
        item.quantity = max(1, quantity)
        item.with_driver = with_driver
        item.save()
    return redirect('cart:view')

@login_required
def cancel_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    if reservation.status in ['pending', 'confirmed']:
        refund = reservation.calculate_cancellation_refund()
        days_before = (reservation.rental_date - date.today()).days
        
        reservation.status = 'cancelled'
        reservation.cancellation_refund = refund
        reservation.save()
        
        if days_before >= 3:
            refund_pct = "90%"
        elif days_before >= 2:
            refund_pct = "50%"
        else:
            refund_pct = "0%"
        
        Notification.objects.create(
            user=request.user,
            notification_type='cancellation',
            title='Réservation annulée',
            message=f'Votre réservation #{reservation.pk} a été annulée. Remboursement: {refund_pct} ({refund:,} FCFA).',
            link=f'/comptes/reservations/',
        )
        
        messages.success(request, f'Réservation annulée. Remboursement de {refund_pct} ({refund:,} FCFA).')
    else:
        messages.error(request, 'Cette réservation ne peut pas être annulée.')
    return redirect('accounts:reservations')

def cart_count(request):
    if request.user.is_authenticated:
        count = CartItem.objects.filter(user=request.user).count()
    else:
        count = 0
    return JsonResponse({'count': count})


@login_required
def update_reservation_location(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    if request.method != 'POST':
        return redirect('accounts:reservations')

    if reservation.status not in ['pending', 'confirmed', 'active']:
        messages.error(request, "Impossible de modifier l'emplacement pour cette réservation.")
        return redirect('accounts:reservations')

    # Verrouillage : une fois l'emplacement déclaré lors de la commande, il n'est plus modifiable.
    if (
        reservation.declared_latitude is not None
        and reservation.declared_longitude is not None
        and reservation.declared_location_name
    ):
        messages.error(request, "Emplacement verrouillé : il ne peut pas être modifié après la commande.")
        return redirect('accounts:reservations')

    try:
        lat = float(request.POST.get('latitude', '').strip())
        lng = float(request.POST.get('longitude', '').strip())
    except (AttributeError, ValueError):
        messages.error(request, "Coordonnées invalides. Déplacez le marqueur puis réessayez.")
        return redirect('accounts:reservations')

    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        messages.error(request, "Coordonnées hors limites.")
        return redirect('accounts:reservations')

    location_name = (request.POST.get('location_name') or '').strip()[:255]
    if not location_name:
        location_name = f"{lat:.6f}, {lng:.6f}"

    old_lat = reservation.equipment.latitude
    old_lng = reservation.equipment.longitude
    old_name = reservation.equipment.location_name or ''

    reservation.declared_latitude = lat
    reservation.declared_longitude = lng
    reservation.declared_location_name = location_name
    reservation.location_declared_at = timezone.now()
    reservation.save(update_fields=[
        'declared_latitude',
        'declared_longitude',
        'declared_location_name',
        'location_declared_at',
        'updated_at',
    ])

    reservation.equipment.latitude = lat
    reservation.equipment.longitude = lng
    reservation.equipment.location_name = location_name
    reservation.equipment.save(update_fields=['latitude', 'longitude', 'location_name', 'updated_at'])

    EquipmentMovement.objects.create(
        equipment=reservation.equipment,
        reservation=reservation,
        user=request.user,
        movement_type='updated',
        old_latitude=old_lat,
        old_longitude=old_lng,
        old_location_name=old_name,
        new_latitude=lat,
        new_longitude=lng,
        new_location_name=location_name,
    )

    Notification.objects.create(
        user=request.user,
        notification_type='system',
        title='Emplacement mis à jour',
        message=(
            f"Nouvel emplacement déclaré pour la réservation #{reservation.pk} : "
            f"{reservation.declared_location_name}."
        ),
        link='/comptes/reservations/',
    )
    messages.success(request, "Nouvel emplacement enregistré avec succès.")
    return redirect('accounts:reservations')
