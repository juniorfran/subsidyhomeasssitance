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
    
class MoovConfig(models.Model):
    """
    Almacena las credenciales y parámetros para Moov.
    """

    nombre = models.CharField(
        max_length=100,
        default="Configuración Moov",
        help_text="Nombre de referencia de esta configuración"
    )
    
    # credenciales
    username = models.CharField(max_length=255, help_text="Moov public key (username)")
    password = models.CharField(max_length=255, help_text="Moov private key (password)")
    
    # datos de cuenta
    account_id = models.CharField(max_length=255, help_text="Account ID principal")
    partner_account_id = models.CharField(max_length=255, help_text="Partner Account ID")
    merchant_payment_method_id = models.CharField(max_length=255, help_text="Merchant Payment Method ID")
    
    # opcional: token de cliente OAuth
    client_id = models.CharField(max_length=255, help_text="Client ID OAuth", blank=True, null=True)
    client_secret = models.CharField(max_length=255, help_text="Client Secret OAuth", blank=True, null=True)
    
    # timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    activo = models.BooleanField(default=True, help_text="Marca si esta configuración está activa")

    class Meta:
        verbose_name = "Configuración Moov"
        verbose_name_plural = "Configuraciones Moov"

    def __str__(self):
        return f"{self.nombre} (Account ID: {self.account_id})"
    
class ContactMessage(models.Model):
    """
    Guarda los mensajes enviados desde el formulario de contacto.
    """
    nombre = models.CharField(max_length=150, verbose_name="Nombre")
    email = models.EmailField(verbose_name="Correo Electrónico")
    asunto = models.CharField(max_length=200, verbose_name="Asunto")
    mensaje = models.TextField(verbose_name="Mensaje")
    enviado_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de envío")

    class Meta:
        verbose_name = "Mensaje de Contacto"
        verbose_name_plural = "Mensajes de Contacto"

    def __str__(self):
        return f"{self.nombre} ({self.email}) - {self.asunto}"