"""
URL configuration for RAOLY BTP project.
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

from payments.views import payment_notify

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('comptes/', include('accounts.urls')),
    path('equipements/', include('equipment.urls')),
    path('panier/', include('cart.urls')),
    path('paiements/', include('payments.urls')),
    # Raccourci (/notify ou /notify/) si l’URL enregistrée chez Notch Pay n’inclut pas /paiements/
    re_path(r'^notify/?$', payment_notify),
    path('contrats/', include('contracts.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
