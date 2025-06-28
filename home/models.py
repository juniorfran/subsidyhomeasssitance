from django.db import models

# Create your models here.
class Service(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Título del servicio")
    descripcion = models.TextField(verbose_name="Descripción")
    icono = models.CharField(max_length=100, blank=True, null=True, verbose_name="Icono (opcional, FontAwesome o Bootstrap Icon)")
    imagen = models.ImageField(upload_to="services/", blank=True, null=True, verbose_name="Imagen (opcional)")
    es_activo = models.BooleanField(default=True, verbose_name="Activo")
    orden = models.PositiveIntegerField(default=0, verbose_name="Orden de aparición")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")

    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Precio)")

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"

    def __str__(self):
        return self.nombre
    
class PaymentLink(models.Model):
    nombre = models.CharField(max_length=150)
    correo = models.EmailField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.TextField(blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} - {self.monto}"