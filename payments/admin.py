from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'currency', 'status', 'transaction_id', 'created_at')
    list_filter = ('status', 'currency')
    search_fields = ('transaction_id', 'user__username')
