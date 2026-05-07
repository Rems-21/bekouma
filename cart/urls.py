from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_view, name='view'),
    path('add/<int:equipment_id>/', views.add_to_cart, name='add'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove'),
    path('update/<int:item_id>/', views.update_cart_item, name='update'),
    path('clear/', views.clear_cart, name='clear'),
    path('cancel/<int:reservation_id>/', views.cancel_reservation, name='cancel'),
    path('reservation/<int:reservation_id>/location/', views.update_reservation_location, name='update_location'),
    path('api/count/', views.cart_count, name='count'),
]
