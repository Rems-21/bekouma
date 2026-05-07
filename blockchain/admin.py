from django.contrib import admin
from .models import Block

@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('index', 'timestamp', 'hash', 'previous_hash')
    readonly_fields = ('index', 'timestamp', 'data', 'hash', 'previous_hash')
