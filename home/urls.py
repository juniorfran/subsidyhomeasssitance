from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path("crear-pago/", views.crear_pago, name="crear_pago"),
    path("obtener-token/", views.obtener_access_token, name="obtener_token"),

    path("moov/sdk/", views.moov_sdk_auth, name="sdk"),
    path("moov/sdk/accounts/", views.moov_sdk_list_accounts, name="moov-sdk-accounts"),

    path("contacto/", views.contacto, name="contacto"),

]