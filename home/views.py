import base64
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
import requests
from .models import Clientes, ContactMessage, Service, PaymentLink, MoovConfig, Transaccion3DS, Transaccion3DS_Respuesta, TransaccionCompra3DS, wompi_config
from django.views import View
from django.contrib import messages

# SDK
from moovio_sdk import Moov
from moovio_sdk.models import components


def home(request):
    servicios = Service.objects.filter(es_activo=True).order_by("orden")

    pago_url = request.session.pop("pago_url", None)
    pago_ok = request.session.pop("pago_ok", False)

    return render(request, "home.html", {
        "servicios": servicios,
        "pago_url": pago_url,
        "pago_ok": pago_ok
    })


####### SDK ##########

def moov_sdk_auth(request):
    """
    Vista funcional para probar autenticación con el SDK de Moov
    """
    config = get_object_or_404(MoovConfig, activo=True)
    try:
        with Moov(
            x_moov_version="v2024.01.00",
            security=components.Security(
                username=config.username,
                password=config.password,
            ),
        ) as moov:
            res = moov.authentication.create_access_token(
                grant_type=components.GrantType.CLIENT_CREDENTIALS,
                client_id=config.client_id,
                client_secret=config.client_secret,
                scope="/accounts.read /accounts.write"
            )

            return JsonResponse(res.dict(), safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def obtener_access_token(request):
    """
    Obtiene token con configuración de MoovConfig en base de datos
    """
    config = get_object_or_404(MoovConfig, activo=True)

    url = f"https://api.moov.io/oauth2/token"

    credentials = f"{config.username}:{config.password}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
        "x-moov-version": "v2024.01.00"
    }

    data = {
        "grant_type": "client_credentials",
        "scope": "accounts:read accounts:write payment-links:write transfers:write"
    }

    print("🔵 Solicitando token a Moov...")

    response = requests.post(url, data=data, headers=headers)

    if response.status_code == 200:
        token_data = response.json()
        print(f"✅ Token recibido: {token_data['access_token']}")
        return JsonResponse(token_data)
    else:
        return JsonResponse({
            "error": "No se pudo obtener el token",
            "status": response.status_code,
            "response": response.text
        }, status=500)


def crear_pago(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        correo = request.POST.get("correo")
        monto = request.POST.get("monto")
        descripcion = request.POST.get("descripcion", "")

        config = get_object_or_404(MoovConfig, activo=True)

        print("==== NUEVA SOLICITUD DE PAGO ====")
        print(f"Nombre: {nombre}")
        print(f"Correo: {correo}")
        print(f"Monto: {monto}")
        print(f"Descripción: {descripcion}")

        try:
            with Moov(
                x_moov_version="v2024.01.00",
                security=components.Security(
                    username=config.username,
                    password=config.password,
                ),
            ) as moov:
                res = moov.payment_links.create(
                    account_id=config.account_id,
                    partner_account_id=config.partner_account_id,
                    merchant_payment_method_id=config.merchant_payment_method_id,
                    amount={
                        "currency": "USD",
                        "value": int(float(monto) * 100)
                    },
                    display={
                        "title": "Pago Hispanic Assistance",
                        "description": descripcion or "Pago desde formulario web",
                        "callToAction": "pay"
                    },
                    customer={
                        "requirePhone": False
                    },
                    payment={
                        "allowedMethods": [
                            "card-payment",
                            "ach-debit-collect"
                        ]
                    },
                )
                pago_url = res.result.link

                PaymentLink.objects.create(
                    nombre=nombre,
                    correo=correo,
                    monto=monto,
                    descripcion=descripcion,
                    link=pago_url
                )

                print(f"✅ Link guardado en BD: {pago_url}")


                # guardar en session
                request.session["pago_url"] = pago_url
                request.session["pago_ok"] = True

                # REDIRECT al home
                return redirect(reverse("home"))
            

        except Exception as e:
            print(f"❌ Error al generar link de pago: {e}")
            return render(request, "pago_error.html", {"error": str(e)})

    print("⚠️ Solicitud GET recibida en crear_pago, redirigiendo al home")
    return redirect(reverse("home"))


def moov_sdk_list_accounts(request):
    accounts = []
    payment_methods = []
    error = None

    try:
        config = get_object_or_404(MoovConfig, activo=True)

        with Moov(
            x_moov_version="v2024.01.00",
            security=components.Security(
                username=config.username,
                password=config.password,
            ),
        ) as moov:
            res_accounts = moov.accounts.list(
                type_=components.AccountType.BUSINESS,
                skip=0,
                count=20
            )
            accounts = res_accounts.result

            res_methods = moov.payment_methods.list(
                account_id=config.account_id
            )
            payment_methods = res_methods.result

    except Exception as e:
        error = str(e)

    return render(request, "list_accounts.html", {
        "accounts": accounts,
        "payment_methods": payment_methods,
        "error": error
    })

def contacto(request):
    if request.method == "POST":
        nombre = request.POST.get("name")
        email = request.POST.get("email")
        asunto = request.POST.get("subject")
        mensaje = request.POST.get("message")

        # validación simple
        if not nombre or not email or not asunto or not mensaje:
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect(reverse("home") + "#contact")
        
        # guardar en la base de datos
        ContactMessage.objects.create(
            nombre=nombre,
            email=email,
            asunto=asunto,
            mensaje=mensaje
        )

        messages.success(request, "¡Mensaje enviado correctamente, nos pondremos en contacto contigo pronto!")
        return redirect(reverse("home") + "#contact")

    return redirect(reverse("home"))


#################### TRANSACCION 3DS WOMPI #######################

from django.db import transaction
from django.core.exceptions import ImproperlyConfigured

def make_wompi_get_request(endpoint, access_token):
    url = f"https://api.wompi.sv/{endpoint}"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {access_token}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error during GET request: {e}")
        return None

def authenticate_wompi(client_id, client_secret):
    url = "https://id.wompi.sv/connect/token"
    payload = {
        "grant_type": "client_credentials",
        "audience": "wompi_api",
        "client_id": client_id,
        "client_secret": client_secret
    }
    headers = {"content-type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"Error during authentication: {e}")
        return None


def get_wompi_config():

    try:
        config = wompi_config.objects.latest('created_at')
        return config
    except wompi_config.DoesNotExist:
        raise ImproperlyConfigured("No se encontro ninguna configuración de Wompi en la base de datos")


def crear_transaccion_3ds(numeroTarjeta, cvv, mesVencimiento, anioVencimiento, monto, nombre, apellido, email, ciudad, direccion, telefono, client_id, client_secret, **kwargs):
    
    # Cargar la configuración de Wompi
    wompi_config = get_wompi_config()
    Client_id = wompi_config.client_id
    Client_secret = wompi_config.client_secret

    # Autenticarse y obtener el token
    access_token = authenticate_wompi(Client_id, Client_secret)
    
    if not access_token:
        print("Error: No se pudo obtener el token de acceso")
        return None
    
    try:
        # Construir la solicitud JSON
        request_data = {
            "tarjetaCreditoDebido": {
                "numeroTarjeta": numeroTarjeta,
                "cvv": cvv,
                "mesVencimiento": mesVencimiento,
                "anioVencimiento": anioVencimiento
            },
            "monto": monto,
            "urlRedirect": "https://volcanosm.net/internet",
            "nombre": nombre,
            "apellido": apellido,
            "email": email,
            "ciudad": ciudad,
            "direccion": direccion,
            "idPais": "SV",
            "idRegion": "SV-SM",
            "codigoPostal": "2401",
            "telefono": telefono,
            **kwargs
        }
        # Log request data
        print("Request Data:", request_data)
        
        # Realizar la solicitud POST para la transacción 3DS
        response = requests.post("https://api.wompi.sv/TransaccionCompra/3Ds", json=request_data, headers=get_wompi_headers(access_token))
        response.raise_for_status()
        transaccion_data = response.json()
        
        # Log response status and content
        print("Response Status Code:", response.status_code)
        if response.content:
            print("Response Content:", response.content)
        else:
            print("Response content is empty")
        
        # Guardar la información de la transacción en la base de datos
        transaccion3ds = Transaccion3DS.objects.create(
            #cliente=get_object_or_404(Clientes, pk=client_id),  # Asumiendo que `client_id` es el ID del cliente
            numeroTarjeta=numeroTarjeta,
            mesVencimiento=mesVencimiento,
            anioVencimiento=anioVencimiento,
            cvv=cvv,
            monto=monto,
            nombre=nombre,
            apellido=apellido,
            email=email,
            ciudad=ciudad,
            direccion=direccion,
            telefono=telefono,
            estado=True
        )
        
        transaccion3ds_respuesta = Transaccion3DS_Respuesta.objects.create(
            transaccion3ds=transaccion3ds,
            idTransaccion=transaccion_data["idTransaccion"],
            esReal=transaccion_data["esReal"],
            urlCompletarPago3Ds=transaccion_data["urlCompletarPago3Ds"],
            monto=transaccion_data["monto"]
        )
        
        return transaccion_data
    
    
    
    except requests.exceptions.RequestException as e:
        print(f"Error during POST request: {e}")
        if e.response is not None:
            if e.response.content:
                print(f"Response content: {e.response.content}")
            else:
                print("Error: Response content is empty")
        return None


def get_wompi_headers(access_token):
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }


#Transaccion comprar acceso

def transaccion3ds_compra(request):
    """
    Procesa un pago 3DS sin asociarlo a un producto/acceso, solo registrando
    los datos del cliente y la transacción.
    """
    # Cargar configuración de Wompi
    wompi_config = get_wompi_config()
    Client_id = wompi_config.client_id
    Client_secret = wompi_config.client_secret

    # Obtener token
    access_token = authenticate_wompi(Client_id, Client_secret)

    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        direccion = request.POST.get('direccion')
        ciudad = request.POST.get('ciudad')
        email = "juniorfran@hotmail.es"
        telefono = 60447435
        numtarjeta = request.POST.get('numtarjeta')
        cvv = request.POST.get('cvv')
        dui = request.POST.get('dui')
        mesvencimiento = request.POST.get('mesvencimiento')
        aniovencimiento = request.POST.get('aniovencimiento')

        monto = float(request.POST.get('monto', 1))

        if monto <= 0:
            return render(request, 'pago_fallido.html', {
                "error_message": "El monto debe ser mayor a 0"
            })

        try:
            with transaction.atomic():
                # Crear la transacción 3DS
                transaccion_data = crear_transaccion_3ds(
                    #acceso_id=None,  # no hay producto asociado
                    numeroTarjeta=str(numtarjeta),
                    cvv=str(cvv),
                    mesVencimiento=mesvencimiento,
                    anioVencimiento=aniovencimiento,
                    monto=monto,
                    nombre=nombre,
                    apellido=apellido,
                    email=email,
                    ciudad=ciudad,
                    direccion=direccion,
                    telefono=telefono,
                    client_id=Client_id,
                    client_secret=Client_secret
                )
                print(transaccion_data)

                # Guarda la transacción local
                transaccion3ds = Transaccion3DS.objects.create(
                    #acceso=None,
                    numeroTarjeta=numtarjeta,
                    mesVencimiento=mesvencimiento,
                    anioVencimiento=aniovencimiento,
                    cvv=cvv,
                    monto=monto,
                    nombre=nombre,
                    apellido=apellido,
                    email=email,
                    ciudad=ciudad,
                    direccion=direccion,
                    telefono=telefono,
                )

                # Respuesta 3DS
                transaccion3ds_respuesta = Transaccion3DS_Respuesta.objects.create(
                    transaccion3ds=transaccion3ds,
                    idTransaccion=transaccion_data.get("idTransaccion", ""),
                    esReal=transaccion_data.get("esReal", True),
                    urlCompletarPago3Ds=transaccion_data.get("urlCompletarPago3Ds", ""),
                    monto=monto
                )

                # Crea cliente
                cliente = Clientes.objects.create(
                    nombre=nombre,
                    apellido=apellido,
                    direccion=direccion,
                    dui=dui,
                    email=email,
                    telefono=telefono,
                )

                # Registra la compra
                TransaccionCompra3DS.objects.create(
                    transaccion3ds=transaccion3ds,
                    transaccion3ds_respuesta=transaccion3ds_respuesta,
                    #cliente=cliente,
                    #acceso=None,
                )

                # redirigir para confirmar
                return redirect('transaccion3ds_exitosa', transaccion3ds_id=transaccion3ds.id)

        except Exception as e:
            print(f"Error en transacción 3DS: {e}")
            return render(request, 'pago_fallido.html', {
                "error_message": str(e)
            })

    # si es GET
    return redirect('home')

    
# Nueva vista para mostrar el mensaje de éxito

def transaccion3ds_exitosa(request, transaccion3ds_id):

    transaccion3ds_compra = get_object_or_404(TransaccionCompra3DS, pk=transaccion3ds_id)
    #tipo_acceso = transaccion3ds_compra.acceso.acceso_tipo
    
    #acceso = transaccion3ds_compra.acceso
    transaccion3ds_respuesta = transaccion3ds_compra.transaccion3ds_respuesta
    #cliente = transaccion3ds_compra.cliente

    idtransac = transaccion3ds_respuesta.idTransaccion
    consulta_transaccion = consultar_transaccion_3ds(idtransac)
    es_aprobada = consulta_transaccion.get('esAprobada', False)

    context = {
        'transaccion_compra': transaccion3ds_compra,
        #'cliente': cliente,
        'transaccion3ds_respuesta': transaccion3ds_respuesta,
        'es_aprobada': es_aprobada,
        'consulta_transaccion': consulta_transaccion,
    }
    
    return render(request, 'transaccion_exitosa.html', context)


def transaccion3ds_fallida(request):

    
    return render(request, 'pago_fallido.html')


def consultar_transaccion_3ds(id_transaccion):
    # Cargar la configuración de Wompi
    wompi_config = get_wompi_config()
    Client_id = wompi_config.client_id
    Client_secret = wompi_config.client_secret

    # Autenticar con Wompi
    access_token = authenticate_wompi(Client_id, Client_secret)
    
    if not access_token:
        print("Error: 'id_transaccion' not provided.")
        return None
    
    endpoint = f"TransaccionCompra/{id_transaccion}"
    transaccion_info = make_wompi_get_request(endpoint, access_token)
    
    if transaccion_info:
        # Imprimir la información del enlace de pago
        print("Información de la transaccion:")
        print(transaccion_info)
        print("este es el id del enlace", id_transaccion)
        return transaccion_info
    else:
        print("Error: Failed to obtain information for the provided 'id_transaccion'.")
        return None
    
def verificar_pago(request, transaccion_id):
    # Obtén la transacción y verifica su estado
    transaccion = get_object_or_404(Transaccion3DS_Respuesta, idTransaccion=transaccion_id)
    consulta_transaccion = consultar_transaccion_3ds(transaccion.idTransaccion)
    es_aprobada = consulta_transaccion['esAprobada']

    return JsonResponse({'es_aprobada': es_aprobada})