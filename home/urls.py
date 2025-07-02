from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path("crear-pago/", views.crear_pago, name="crear_pago"),
    path("obtener-token/", views.obtener_access_token, name="obtener_token"),

    path("moov/sdk/", views.moov_sdk_auth, name="sdk"),
    path("moov/sdk/accounts/", views.moov_sdk_list_accounts, name="moov-sdk-accounts"),

    path("contacto/", views.contacto, name="contacto"),


    # wompi urls
    # transacción 3DS directa
    path('pago-directo/', views.transaccion3ds_compra, name='transaccion3ds_compra'),

    # resultado exitoso de la transacción 3DS
    path('pago-directo/exitoso/<int:transaccion3ds_id>/', views.transaccion3ds_exitosa, name='transaccion3ds_exitosa'),

    # resultado fallido
    path('pago-directo/fallido/', views.transaccion3ds_fallida, name='transaccion3ds_fallida'),

    # para verificar pago via AJAX
    path('verificar-pago/<str:transaccion_id>/', views.verificar_pago, name='verificar_pago'),

    # si deseas exponer la obtención de token manualmente
    path('obtener-access-token/', views.obtener_access_token, name='obtener_access_token'),

]