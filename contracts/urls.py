from django.urls import path
from . import views

app_name = 'contracts'

urlpatterns = [
    path('generate/<int:order_id>/', views.generate_contract, name='generate'),
    path('<int:pk>/download/', views.download_contract, name='download'),
]
