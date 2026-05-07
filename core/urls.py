from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('a-propos/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path(
        'live/suivi/<uuid:token>/',
        views.live_tracking_mobile,
        name='live_tracking_mobile',
    ),
    path(
        'live/suivi/<uuid:token>/ping/',
        views.live_tracking_ping,
        name='live_tracking_ping',
    ),
    path(
        'tracking/',
        views.staff_declared_zone_monitor,
        name='staff_zone_monitor',
    ),
    path(
        'tracking/positions.json',
        views.staff_zone_monitor_positions_json,
        name='staff_zone_monitor_json',
    ),
]
