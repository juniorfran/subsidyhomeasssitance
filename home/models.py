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
    

##############3 wompi models tansaccion 3ds ####################

class Clientes (models.Model):
    nombre = models.CharField( max_length=50)
    apellido = models.CharField( max_length=50)
    direccion = models.TextField()
    dui = models.CharField(max_length=50)
    email = models.EmailField()
    telefono = models.CharField(max_length=20)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.nombre} - {self.apellido}"


class wompi_config (models.Model):
    cuenta = models.CharField(max_length=800, blank=True, null=True)
    client_id = models.TextField(max_length=800, blank=True, null=True)
    client_secret = models.TextField(max_length=800, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    #funcion str
    def __str__(self):
        return self.cuenta
    
    class Meta:
        verbose_name = "Configuración Wompi"
        verbose_name_plural = "Configuraciones Wompi"
   
class Transaccion3DS(models.Model):
    #acceso = models.ForeignKey(Accesos, on_delete=models.CASCADE, related_name='transaccion3ds_acceso')
    numeroTarjeta = models.CharField(max_length=150)
    mesVencimiento = models.CharField(max_length=50)
    anioVencimiento = models.CharField(max_length=50)
    cvv = models.CharField(max_length=50)
    monto = models.CharField(max_length=50)
    nombre = models.CharField(max_length=150)
    apellido = models.CharField(max_length=150)
    email = models.CharField(max_length=150)
    ciudad = models.CharField(max_length=50)
    direccion = models.TextField()
    telefono = models.CharField( max_length=50)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
    fecha_modificacion = models.DateTimeField(auto_now=True, null=True)
    estado = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.nombre} - {self.apellido}"
    
class Transaccion3DS_Respuesta(models.Model):
    transaccion3ds = models.ForeignKey(Transaccion3DS, on_delete=models.CASCADE, related_name='transaccion3ds_respuesta_set')
    idTransaccion = models.CharField(max_length=150)
    esReal = models.BooleanField(default=True)
    urlCompletarPago3Ds = models.URLField(max_length=500)
    monto = models.CharField(max_length=50)
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
    fecha_modificacion = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return f"{self.transaccion3ds} - {self.idTransaccion}"
    
class TransaccionCompra3DS(models.Model):
    transaccion3ds = models.ForeignKey(Transaccion3DS, on_delete=models.CASCADE, related_name='transaccion3ds_set')
    transaccion3ds_respuesta = models.ForeignKey(Transaccion3DS_Respuesta, on_delete=models.CASCADE, related_name='transaccion3ds_respuesta_set')
    #cliente = models.ForeignKey(Clientes, on_delete=models.CASCADE, related_name='cliente_transaccion3ds_set')
    #acceso = models.ForeignKey(Accesos, on_delete=models.CASCADE, related_name='acceso_transaccion3ds_set')
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
    fecha_modificacion = models.DateTimeField(auto_now=True, null=True)
    estado = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.transaccion3ds} - {self.fecha_creacion}"