from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("crear-pago/", views.crear_pago, name="crear_pago"),
]