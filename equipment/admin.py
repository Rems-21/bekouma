from django.contrib import admin

from .models import Category, Equipment, EquipmentUnavailableDate


def _entreprise_tarif(obj):
    return f'{obj.price_per_day_entreprise:,} F'.replace(',', ' ')


_entreprise_tarif.short_description = 'Tarif jour entreprise'


class EquipmentUnavailableDateInline(admin.TabularInline):
    model = EquipmentUnavailableDate
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'price_per_day',
        _entreprise_tarif,
        'condition',
        'is_available',
        'requires_driver',
        'quantity_total',
    )
    list_filter = ('category', 'condition', 'is_available', 'requires_driver')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [EquipmentUnavailableDateInline]
