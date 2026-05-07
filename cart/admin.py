from django.contrib import admin
from .models import CartItem, LiveLocationPing, Order, Reservation, EquipmentMovement

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'equipment', 'quantity', 'rental_date', 'return_date', 'with_driver')

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'equipment', 'rental_date', 'return_date', 'status', 'total_price')
    list_filter = ('status',)
    search_fields = ('user__username', 'equipment__name')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_amount', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(LiveLocationPing)
class LiveLocationPingAdmin(admin.ModelAdmin):
    list_display = ('id', 'reservation', 'latitude', 'longitude', 'created_at')
    list_filter = ('created_at',)
    raw_id_fields = ('reservation',)


@admin.register(EquipmentMovement)
class EquipmentMovementAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'equipment', 'reservation', 'user', 'movement_type',
        'old_location_name', 'new_location_name', 'created_at'
    )
    list_filter = ('movement_type', 'created_at', 'equipment')
    search_fields = ('equipment__name', 'user__username', 'old_location_name', 'new_location_name')
