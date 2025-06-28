from django.contrib import admin
from .models import Service

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("nombre", "es_activo", "orden", "precio", "created_at")
    list_filter = ("es_activo",)
    search_fields = ("nombre", "descripcion")
    ordering = ("orden",)