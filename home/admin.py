from django.contrib import admin
from .models import ContactMessage, MoovBusinessAccount, Service, PaymentLink, MoovConfig

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "precio",
        "es_activo",
        "orden",
        "created_at",
        "updated_at",
    )
    list_filter = ("es_activo",)
    search_fields = ("nombre", "descripcion")
    ordering = ("orden",)

@admin.register(PaymentLink)
class PaymentLinkAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "correo",
        "monto",
        "link",
        "creado_en",
    )
    search_fields = ("nombre", "correo", "link")

@admin.register(MoovConfig)
class MoovConfigAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "account_id",
        "partner_account_id",
        "activo",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")
    search_fields = ("nombre", "account_id", "partner_account_id")
    list_filter = ("activo",)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("nombre", "email", "asunto", "enviado_en")
    search_fields = ("nombre", "email", "asunto", "mensaje")
    list_filter = ("enviado_en",)

from .models import (
    Clientes,
    wompi_config,
    Transaccion3DS,
    Transaccion3DS_Respuesta,
    TransaccionCompra3DS,
)

@admin.register(Clientes)
class ClientesAdmin(admin.ModelAdmin):
    list_display = ("nombre", "apellido", "email", "telefono", "fecha_creacion")
    search_fields = ("nombre", "apellido", "email", "telefono")
    readonly_fields = ("fecha_creacion", "fecha_modificacion")

@admin.register(wompi_config)
class WompiConfigAdmin(admin.ModelAdmin):
    list_display = ("cuenta", "client_id", "created_at")
    readonly_fields = ("created_at",)

@admin.register(Transaccion3DS)
class Transaccion3DSAdmin(admin.ModelAdmin):
    list_display = ("nombre", "apellido", "monto", "email", "fecha_creacion", "estado")
    search_fields = ("nombre", "apellido", "email", "numeroTarjeta")
    readonly_fields = ("fecha_creacion", "fecha_modificacion")

@admin.register(Transaccion3DS_Respuesta)
class Transaccion3DSRespuestaAdmin(admin.ModelAdmin):
    list_display = ("idTransaccion", "monto", "esReal", "fecha_creacion")
    readonly_fields = ("fecha_creacion", "fecha_modificacion")

@admin.register(TransaccionCompra3DS)
class TransaccionCompra3DSAdmin(admin.ModelAdmin):
    list_display = ("transaccion3ds", "transaccion3ds_respuesta", "estado", "fecha_creacion")
    readonly_fields = ("fecha_creacion", "fecha_modificacion")

@admin.register(MoovBusinessAccount)
class MoovBusinessAccountAdmin(admin.ModelAdmin):
    list_display = ["legal_name", "moov_account_id", "fecha_creacion"]
    search_fields = ["legal_name", "email"]