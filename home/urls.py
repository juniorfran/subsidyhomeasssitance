from django.shortcuts import render
from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path("crear-pago/", views.crear_pago, name="crear_pago"),
    path("obtener-token/", views.obtener_access_token, name="obtener_token"),
    path("moov/sdk/", views.moov_sdk_auth, name="sdk"),
    path("moov/sdk/accounts/", views.moov_sdk_list_accounts, name="moov-sdk-accounts"),
    path("contacto/", views.contacto, name="contacto"),
    path("crear-cuenta/", views.crear_cuenta_business, name="crear_cuenta_empresa"),
    path("cuenta-exitosa/", lambda r: render(r, "cuenta_exitosa.html"), name="cuenta_exitosa"),


    # wompi urls
    # transacción 3DS directa
    path('pago-directo/', views.transaccion3ds_compra, name='transaccion3ds_compra'),

    # resultado exitoso de la transacción 3DS
    path('pago-directo/exitoso/', views.transaccion3ds_exitosa, name='transaccion3ds_exitosa'),

    # resultado fallido
    path('pago-directo/fallido/', views.transaccion3ds_fallida, name='transaccion3ds_fallida'),

    # para verificar pago via AJAX
    path('verificar-pago/<str:transaccion_id>/', views.verificar_pago, name='verificar_pago'),

    # si deseas exponer la obtención de token manualmente
    path('obtener-access-token/', views.obtener_access_token, name='obtener_access_token'),

    path("wompi/regiones/", views.wompi_regiones, name="wompi_regiones"),

    path("pago_servicios/", views.pago_directo_view, name="pago_directo"),

]