from django.contrib import admin
from .models import HeroSlide, SiteInfo

@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active')
    list_editable = ('order', 'is_active')

@admin.register(SiteInfo)
class SiteInfoAdmin(admin.ModelAdmin):
    pass
