from django.contrib import admin
from .models import ContactMessage, Service, PaymentLink, MoovConfig

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