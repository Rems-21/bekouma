from django.db import models
from django.conf import settings

class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart_items')
    equipment = models.ForeignKey('equipment.Equipment', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    with_driver = models.BooleanField(default=False)
    rental_date = models.DateField()
    return_date = models.DateField()
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'equipment', 'rental_date')
    
    def __str__(self):
        return f"{self.equipment.name} - {self.user.username}"
    
    @property
    def num_days(self):
        return max(1, (self.return_date - self.rental_date).days)
    
    @property
    def subtotal(self):
        rate = self.equipment.daily_price_for_user(self.user)
        base = rate * self.num_days * self.quantity
        if self.with_driver and self.equipment.requires_driver:
            base += self.equipment.driver_price_per_day * self.num_days
        return base

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('active', 'En cours'),
        ('completed', 'Terminée'),
        ('cancelled', 'Annulée'),
        ('late', 'En retard'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reservations')
    equipment = models.ForeignKey('equipment.Equipment', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    with_driver = models.BooleanField(default=False)
    rental_date = models.DateField()
    return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.PositiveIntegerField(default=0)
    driver_price = models.PositiveIntegerField(default=0)
    penalty_amount = models.PositiveIntegerField(default=0)
    late_fee = models.PositiveIntegerField(default=0)
    cancellation_refund = models.PositiveIntegerField(default=0)
    declared_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    declared_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    declared_location_name = models.CharField(max_length=255, blank=True)
    location_declared_at = models.DateTimeField(null=True, blank=True)
    live_tracking_token = models.UUIDField(null=True, blank=True, db_index=True)
    live_tracking_expires = models.DateTimeField(null=True, blank=True)
    blockchain_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Reservation #{self.pk} - {self.equipment.name}"
    
    @property
    def num_days(self):
        return max(1, (self.return_date - self.rental_date).days)
    
    def calculate_late_fee(self):
        if self.actual_return_date and self.actual_return_date > self.return_date:
            late_days = (self.actual_return_date - self.return_date).days
            return int(self.total_price * 0.02 * late_days)
        return 0
    
    def calculate_cancellation_refund(self):
        from datetime import date
        if self.status != 'pending' and self.status != 'confirmed':
            return 0
        days_before = (self.rental_date - date.today()).days
        if days_before >= 3:
            return int(self.total_price * 0.90)
        elif days_before >= 2:
            return int(self.total_price * 0.50)
        else:
            return 0

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('paid', 'Payée'),
        ('failed', 'Échouée'),
        ('refunded', 'Remboursée'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    reservations = models.ManyToManyField(Reservation, related_name='orders')
    total_amount = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_reference = models.CharField(max_length=100, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    blockchain_hash = models.CharField(max_length=64, blank=True)
    rental_date = models.DateField(null=True)
    return_date = models.DateField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Order #{self.pk} - {self.user.username}"


class EquipmentMovement(models.Model):
    MOVEMENT_CHOICES = [
        ('declared', 'Déclaration initiale'),
        ('updated', 'Mise à jour emplacement'),
        ('admin_adjustment', 'Ajustement administrateur'),
    ]

    equipment = models.ForeignKey('equipment.Equipment', on_delete=models.CASCADE, related_name='movements')
    reservation = models.ForeignKey('Reservation', on_delete=models.SET_NULL, null=True, blank=True, related_name='movements')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='equipment_movements')
    movement_type = models.CharField(max_length=30, choices=MOVEMENT_CHOICES, default='updated')

    old_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    old_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    old_location_name = models.CharField(max_length=255, blank=True)

    new_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    new_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    new_location_name = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.equipment.name} - {self.get_movement_type_display()} ({self.created_at:%d/%m/%Y %H:%M})"


class LiveLocationPing(models.Model):
    """Position GPS envoyée depuis le téléphone (URL de suivi) pour le centre opérationnel."""

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name='live_pings',
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy_m = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reservation', 'created_at']),
        ]

    def __str__(self):
        return f'Ping rés. #{self.reservation_id} @ {self.created_at:%H:%M:%S}'
