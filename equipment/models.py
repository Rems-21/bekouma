from django.conf import settings
from django.db import models


def _enterprise_extra_fcfa() -> int:
    return int(getattr(settings, 'EQUIPMENT_ENTERPRISE_PRICE_EXTRA_FCFA', 10000))


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class Equipment(models.Model):
    CONDITION_CHOICES = [
        ('excellent', 'Excellent'),
        ('bon', 'Bon'),
        ('correct', 'Correct'),
        ('usage', 'Usagé'),
    ]
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='equipments')
    description = models.TextField()
    price_per_day = models.PositiveIntegerField(
        help_text='Tarif journalier particulier (FCFA). Entreprise : ce montant + EQUIPMENT_ENTERPRISE_PRICE_EXTRA_FCFA (défaut 10 000).',
    )
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='bon')
    image = models.ImageField(upload_to='equipment/')
    image2 = models.ImageField(upload_to='equipment/', blank=True, null=True)
    image3 = models.ImageField(upload_to='equipment/', blank=True, null=True)
    image4 = models.ImageField(upload_to='equipment/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    requires_driver = models.BooleanField(default=False, help_text="Engin nécessitant un chauffeur")
    driver_price_per_day = models.PositiveIntegerField(default=0, help_text="Prix chauffeur par jour en FCFA")
    latitude = models.FloatField(default=0)
    longitude = models.FloatField(default=0)
    location_name = models.CharField(max_length=200, blank=True)
    quantity_total = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

    @property
    def price_per_day_entreprise(self) -> int:
        return int(self.price_per_day) + _enterprise_extra_fcfa()

    def daily_price_for_user(self, user) -> int:
        """Tarif / jour selon le type de compte (particulier vs entreprise)."""
        if user and getattr(user, 'is_authenticated', False) and getattr(user, 'user_type', '') == 'entreprise':
            return self.price_per_day_entreprise
        return int(self.price_per_day)

    def get_available_quantity(self, date):
        from cart.models import Reservation
        reserved = Reservation.objects.filter(
            equipment=self,
            rental_date=date,
            status__in=['pending', 'confirmed', 'active']
        ).count()
        return max(0, self.quantity_total - reserved)

class EquipmentUnavailableDate(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='unavailable_dates')
    date = models.DateField()
    reason = models.CharField(max_length=200, blank=True)
    
    class Meta:
        unique_together = ('equipment', 'date')
    
    def __str__(self):
        return f"{self.equipment.name} - {self.date}"
