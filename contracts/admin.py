from django.contrib import admin
from .models import Contract

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('contract_number', 'user', 'order', 'generated_at', 'blockchain_hash')
    search_fields = ('contract_number', 'user__username')
    readonly_fields = ('blockchain_hash',)
