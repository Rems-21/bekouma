from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from .models import Equipment, Category
from datetime import date, timedelta
import json

def equipment_list(request):
    equipments = Equipment.objects.filter(is_available=True)
    categories = Category.objects.all()
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    
    if query:
        equipments = equipments.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    if category_id:
        equipments = equipments.filter(category_id=category_id)
    
    context = {
        'equipments': equipments,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
    }
    return render(request, 'equipment/list.html', context)

def equipment_detail(request, slug):
    equipment = get_object_or_404(Equipment, slug=slug)
    related = Equipment.objects.filter(
        category=equipment.category, is_available=True
    ).exclude(id=equipment.id)[:4]
    context = {
        'equipment': equipment,
        'related_equipments': related,
        'daily_price_js': equipment.daily_price_for_user(getattr(request, 'user', None)),
    }
    return render(request, 'equipment/detail.html', context)

def equipment_availability(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    today = date.today()
    unavailable = list(
        equipment.unavailable_dates.filter(date__gte=today).values_list('date', flat=True)
    )
    from cart.models import Reservation
    reserved_dates = Reservation.objects.filter(
        equipment=equipment,
        rental_date__gte=today,
        status__in=['pending', 'confirmed', 'active']
    ).values_list('rental_date', flat=True)
    
    fully_booked = []
    for d in reserved_dates:
        count = Reservation.objects.filter(
            equipment=equipment, rental_date=d,
            status__in=['pending', 'confirmed', 'active']
        ).count()
        if count >= equipment.quantity_total:
            fully_booked.append(d)
    
    all_unavailable = set([d.isoformat() for d in unavailable] + [d.isoformat() for d in fully_booked])
    return JsonResponse({'unavailable_dates': list(all_unavailable)})

def equipment_map(request):
    equipments = Equipment.objects.filter(is_available=True).exclude(latitude=0, longitude=0)
    data = []
    for e in equipments:
        data.append({
            'id': e.id,
            'name': e.name,
            'slug': e.slug,
            'lat': e.latitude,
            'lng': e.longitude,
            'location': e.location_name,
            'price': e.price_per_day,
            'price_entreprise': e.price_per_day_entreprise,
            'image': e.image.url if e.image else '',
            'category': e.category.name,
        })
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'equipments': data})
    return render(request, 'equipment/map.html', {'equipments_json': json.dumps(data)})
