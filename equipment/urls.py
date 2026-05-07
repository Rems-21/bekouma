from django.urls import path
from . import views

app_name = 'equipment'

urlpatterns = [
    path('', views.equipment_list, name='list'),
    path('carte/', views.equipment_map, name='map'),
    path('<slug:slug>/', views.equipment_detail, name='detail'),
    path('api/availability/<int:pk>/', views.equipment_availability, name='availability'),
]
