from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('location/', views.select_location, name='location'),
    path('initiate/', views.initiate_payment, name='initiate'),
    path('notify/', views.payment_notify, name='notify'),
    path('return/', views.payment_return, name='return'),
    path('sync/<int:order_id>/', views.sync_order_payment, name='sync_order'),
    path('simulate/<int:order_id>/', views.simulate_payment, name='simulate'),
]
