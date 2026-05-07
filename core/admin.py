from django.contrib import admin
from .models import HeroSlide, SiteInfo

@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active')
    list_editable = ('order', 'is_active')

@admin.register(SiteInfo)
class SiteInfoAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('company_name', 'slogan', 'phone', 'email', 'address', 'about_text')}),
        ('Réseaux sociaux', {'fields': ('facebook', 'instagram', 'twitter', 'whatsapp')}),
        (
            'Google Search Console',
            {
                'fields': ('google_verification_filename', 'google_verification_file_content'),
                'description': 'Méthode « fichier HTML » : coller le nom exact du fichier et la ligne de contenu fournis par Google.',
            },
        ),
    )
