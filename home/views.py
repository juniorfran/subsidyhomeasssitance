import base64
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
import requests
from .models import Clientes, ContactMessage, MoovBusinessAccount, Service, PaymentLink, MoovConfig, Transaccion3DS, Transaccion3DS_Respuesta, TransaccionCompra3DS, wompi_config
from django.views import View
from django.contrib import messages
from django.core.mail import send_mail

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

def crear_cuenta_business(request):
    if request.method == "POST":
        legal_name = request.POST.get("legal_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        address_line1 = request.POST.get("address_line1")
        address_line2 = request.POST.get("address_line2")
        city = request.POST.get("city")
        state = request.POST.get("state")
        postal_code = request.POST.get("postal_code")
        country = request.POST.get("country", "US")
        website = request.POST.get("website")
        ein_number = request.POST.get("ein_number")

        accepted_ip = request.META.get("REMOTE_ADDR", "0.0.0.0")
        accepted_user_agent = request.META.get("HTTP_USER_AGENT", "unknown")
        accepted_date = timezone.now()

        print("=== DATOS RECIBIDOS DEL FORMULARIO ===")
        print(f"legal_name: {legal_name}")
        print(f"email: {email}")
        print(f"phone: {phone}")
        print(f"address_line1: {address_line1}")
        print(f"city: {city}")
        print(f"state: {state}")
        print(f"postal_code: {postal_code}")
        print(f"country: {country}")
        print(f"website: {website}")
        print(f"ein_number: {ein_number}")
        print("=====================================")

        try:
            with Moov(
                x_moov_version="v2024.01.00",
                security=components.Security(
                    username=settings.MOOV_CLIENT_ID,
                    password=settings.MOOV_CLIENT_SECRET,
                ),
            ) as moov:
                payload = {
                    "account_type": components.CreateAccountType.BUSINESS,
                    "profile": components.CreateProfile(
                        business=components.CreateBusinessProfile(
                            legal_business_name=legal_name or "Mi Empresa S.A. de C.V.",
                            email=email or "soporte@miempresa.com",
                            phone={"number": phone or "5551234567", "country_code": "1"},
                            address={
                                "address_line1": address_line1 or "Av. Siempre Viva 123",
                                "address_line2": address_line2 or "",
                                "city": city or "San Salvador",
                                "state_or_province": state or "SS",
                                "postal_code": postal_code or "1101",
                                "country": country or "US"
                            },
                            type="LLC",
                            website=website or "https://miempresa.com",
                            description="Mi Empresa dedicada a servicios tecnológicos"
                        )
                    ),
                    "metadata": {
                        "cliente_interno": "mi_id_123"
                    },
                    "terms_of_service": {
                        "accepted_date": accepted_date.isoformat(),
                        "accepted_ip": accepted_ip,
                        "accepted_user_agent": accepted_user_agent,
                        "accepted_domain": request.get_host(),
                    },
                    "customer_support": {
                        "phone": {
                            "number": phone or "5551234567",
                            "country_code": "1",
                        },
                        "email": email or "soporte@miempresa.com",
                        "address": {
                            "address_line1": address_line1 or "Av. Siempre Viva 123",
                            "address_line2": address_line2 or "",
                            "city": city or "San Salvador",
                            "state_or_province": state or "SS",
                            "postal_code": postal_code or "1101",
                            "country": country or "US"
                        },
                    },
                    "settings": {
                        "card_payment": {
                            "statement_descriptor": "MiEmpresa",
                        },
                        "ach_payment": {
                            "company_name": "MiEmpresa"
                        },
                    }
                }

                print("=== PAYLOAD ENVIADO A MOOV ===")
                print(payload)
                print("===================================")

                res = moov.accounts.create(**payload)

                print("=== RESPUESTA DE MOOV ===")
                print(res)
                print("===============================")

                account_id = res.result.account_id

                moov.accounts.request_capabilities(
                    account_id=account_id,
                    request_body=[
                        components.CapabilityName.TRANSFERS,
                        components.CapabilityName.SEND_FUNDS,
                        components.CapabilityName.COLLECT_FUNDS,
                        components.CapabilityName.WALLET,
                    ]
                )

                MoovBusinessAccount.objects.create(
                    legal_name=legal_name,
                    email=email,
                    phone=phone,
                    address_line1=address_line1,
                    address_line2=address_line2,
                    city=city,
                    state=state,
                    postal_code=postal_code,
                    country=country,
                    website=website,
                    ein_number=ein_number,
                    accepted_ip=accepted_ip,
                    accepted_user_agent=accepted_user_agent,
                    accepted_date=accepted_date,
                    moov_account_id=account_id,
                )

                return redirect("cuenta_exitosa")

        except Exception as e:
            print("=== ERROR DE MOOV ===")
            print(f"{e}")
            print("=======================")
            return render(request, "crear_cuenta.html", {"error": str(e)})

    return render(request, "crear_cuenta.html")


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

# def crear_transaccion_3ds(numeroTarjeta, cvv, mesVencimiento, anioVencimiento, monto, nombre, apellido, email, ciudad, direccion, telefono, client_id, client_secret, **kwargs):
    
#     # Cargar la configuración de Wompi
#     wompi_config = get_wompi_config()
#     Client_id = wompi_config.client_id
#     Client_secret = wompi_config.client_secret

#     # Autenticarse y obtener el token
#     access_token = authenticate_wompi(Client_id, Client_secret)
    
#     if not access_token:
#         print("Error: No se pudo obtener el token de acceso")
#         return None
    
#     try:
#         # Construir la solicitud JSON
#         request_data = {
#             "tarjetaCreditoDebido": {
#                 "numeroTarjeta": numeroTarjeta,
#                 "cvv": cvv,
#                 "mesVencimiento": mesVencimiento,
#                 "anioVencimiento": anioVencimiento
#             },
#             "monto": monto,
#             "urlRedirect": "https://xsoporte.contaspro.cloud/",
#             "nombre": nombre,
#             "apellido": apellido,
#             "email": email,
#             "ciudad": ciudad,
#             "direccion": direccion,
#             "idPais": "US",
#             "idRegion": "US-CA",
#             "codigoPostal": "90007",
#             "telefono": telefono,
#             **kwargs
#         }
#         # Log request data
#         print("Request Data:", request_data)
        
#         # Realizar la solicitud POST para la transacción 3DS
#         response = requests.post("https://api.wompi.sv/TransaccionCompra/3Ds", json=request_data, headers=get_wompi_headers(access_token))
#         response.raise_for_status()
#         transaccion_data = response.json()
        
#         # Log response status and content
#         print("Response Status Code:", response.status_code)
#         if response.content:
#             print("Response Content:", response.content)
#         else:
#             print("Response content is empty")
        
#         # Guardar la información de la transacción en la base de datos
#         transaccion3ds = Transaccion3DS.objects.create(
#             #cliente=get_object_or_404(Clientes, pk=client_id),  # Asumiendo que `client_id` es el ID del cliente
#             numeroTarjeta=numeroTarjeta,
#             mesVencimiento=mesVencimiento,
#             anioVencimiento=anioVencimiento,
#             cvv=cvv,
#             monto=monto,
#             nombre=nombre,
#             apellido=apellido,
#             email=email,
#             ciudad=ciudad,
#             direccion=direccion,
#             telefono=telefono,
#             estado=True
#         )
        
#         transaccion3ds_respuesta = Transaccion3DS_Respuesta.objects.create(
#             transaccion3ds=transaccion3ds,
#             idTransaccion=transaccion_data["idTransaccion"],
#             esReal=transaccion_data["esReal"],
#             urlCompletarPago3Ds=transaccion_data["urlCompletarPago3Ds"],
#             monto=transaccion_data["monto"]
#         )
        
#         return transaccion3ds, transaccion3ds_respuesta, transaccion_data
    
    
    
#     except requests.exceptions.RequestException as e:
#         print(f"Error during POST request: {e}")
#         if e.response is not None:
#             if e.response.content:
#                 print(f"Response content: {e.response.content}")
#             else:
#                 print("Error: Response content is empty")
#         return None


def crear_transaccion_3ds(
    numeroTarjeta, cvv, mesVencimiento, anioVencimiento, monto,
    nombre, apellido, email, ciudad, direccion, telefono,
    url_redirect
):
    """
    Crea la transacción 3DS en Wompi y maneja errores HTTP comunes y de red.
    Devuelve: (trans, resp, data) o lanza excepción con mensaje detallado.
    """

    # 1. Obtener credenciales del modelo wompi_config
    try:
        config = wompi_config.objects.latest('created_at')
        client_id     = config.client_id
        client_secret = config.client_secret
    except Exception as e:
        raise Exception(f"❌ Error obteniendo configuración Wompi: {e}")

    # 2. Autenticación
    access_token = authenticate_wompi(client_id, client_secret)
    if not access_token:
        raise Exception("❌ No se pudo obtener el token de acceso desde Wompi (¿Credenciales erróneas o API inalcanzable?).")

    # 3. Validar datos antes de enviar
    # Campos raíz
    campos_raiz = ["monto", "nombre", "apellido", "email", "ciudad", "direccion", "telefono"]
    for campo in campos_raiz:
        if not locals()[campo]:
            raise ValueError(f"El campo {campo} es obligatorio y no puede estar vacío")
    # Campos tarjeta
    for campo in ["numeroTarjeta", "cvv", "mesVencimiento", "anioVencimiento"]:
        if not locals()[campo]:
            raise ValueError(f"El campo {campo} es obligatorio y no puede estar vacío")
    if float(monto) <= 0:
        raise ValueError("El monto debe ser mayor a 0")

    # 4. Preparar payload y headers
    request_data = {
        "tarjetaCreditoDebido": {
            "numeroTarjeta": numeroTarjeta,
            "cvv": cvv,
            "mesVencimiento": mesVencimiento,
            "anioVencimiento": anioVencimiento
        },
        "monto": monto,
        "urlRedirect": url_redirect,
        "nombre": nombre,
        "apellido": apellido,
        "email": email,
        "ciudad": ciudad,
        "direccion": direccion,
        "idPais": "US",
        "idRegion": "US-CA",
        "codigoPostal": "90007",
        "telefono": telefono
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    # 5. Llamar a la API de Wompi con manejo de errores robusto
    try:
        response = requests.post(
            "https://api.wompi.sv/TransaccionCompra/3Ds",
            json=request_data,
            headers=headers,
            timeout=15
        )
    except requests.exceptions.Timeout:
        raise Exception("⏱️ La solicitud a Wompi ha excedido el tiempo de espera (timeout).")
    except requests.exceptions.ConnectionError:
        raise Exception("🔌 No hay conexión con la API de Wompi. ¿Problema de red o la API no responde?")
    except requests.exceptions.RequestException as e:
        raise Exception(f"❌ Error general de conexión con Wompi: {e}")

    # 6. Procesar la respuesta HTTP
    if response.status_code == 200:
        data = response.json()
        # Verificar que esté todo lo necesario
        if "idTransaccion" not in data or "urlCompletarPago3Ds" not in data:
            raise Exception("⚠️ Respuesta de Wompi incompleta: falta 'idTransaccion' o 'urlCompletarPago3Ds'")
    elif response.status_code == 400:
        raise Exception(f"❌ [400] Solicitud incorrecta: {response.text}")
    elif response.status_code == 401:
        raise Exception(f"🔒 [401] No autorizado. Token inválido o credenciales incorrectas: {response.text}")
    elif response.status_code == 403:
        raise Exception(f"🚫 [403] Acceso prohibido: {response.text}")
    elif response.status_code == 404:
        raise Exception(f"🔎 [404] API Wompi no encontrada o endpoint incorrecto: {response.text}")
    elif response.status_code == 422:
        raise Exception(f"❌ [422] Entidad no procesable (campos inválidos): {response.text}")
    elif response.status_code >= 500:
        raise Exception(f"🛑 [5xx] Error interno del servidor Wompi. Puede estar en mantenimiento o con problemas: {response.text}")
    else:
        raise Exception(f"⚠️ [HTTP {response.status_code}] Respuesta inesperada de Wompi: {response.text}")

    # 7. Guardar en base de datos
    try:
        trans = Transaccion3DS.objects.create(
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
        resp = Transaccion3DS_Respuesta.objects.create(
            transaccion3ds=trans,
            idTransaccion=data["idTransaccion"],
            esReal=data["esReal"],
            urlCompletarPago3Ds=data["urlCompletarPago3Ds"],
            monto=data["monto"]
        )
    except Exception as e:
        raise Exception(f"❌ Error guardando transacción en la base de datos: {e}")

    # 8. Retornar lo necesario
    return trans, resp, data



def get_wompi_headers(access_token):
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

#Transaccion comprar acceso
# def transaccion3ds_compra(request):
#     """
#     Procesa un pago 3DS sin asociarlo a un producto/acceso, solo registrando
#     los datos del cliente y la transacción.
#     """
#     wompi_config = get_wompi_config()
#     Client_id = wompi_config.client_id
#     Client_secret = wompi_config.client_secret

#     if request.method == 'POST':
#         nombre = request.POST.get('nombre')
#         apellido = request.POST.get('apellido')
#         direccion = request.POST.get('direccion')
#         ciudad = "Los Angeles"  # Puedes cambiar esto si es necesario
#         email_client = request.POST.get('email')
#         email = "xsoportelatino@gmail.com"
#         telefono = 72421660
#         numtarjeta = request.POST.get('numtarjeta')
#         cvv = request.POST.get('cvv')
#         dui = "053208781"
#         mesvencimiento = request.POST.get('mesvencimiento')
#         aniovencimiento = request.POST.get('aniovencimiento')

#         monto = float(request.POST.get('monto', 1))

#         if monto <= 0:
#             return render(request, 'pago_fallido.html', {
#                 "error_message": "El monto debe ser mayor a 0"
#             })

#         try:
#             with transaction.atomic():
#                 # llamar a crear_transaccion_3ds que ya crea y devuelve las instancias
#                 transaccion3ds, transaccion3ds_respuesta, transaccion_data = crear_transaccion_3ds(
#                     numeroTarjeta=str(numtarjeta),
#                     cvv=str(cvv),
#                     mesVencimiento=mesvencimiento,
#                     anioVencimiento=aniovencimiento,
#                     monto=monto,
#                     nombre=nombre,
#                     apellido=apellido,
#                     email=email,
#                     ciudad=ciudad,
#                     direccion=direccion,
#                     telefono=telefono,
#                     client_id=Client_id,
#                     client_secret=Client_secret
#                 )
#                 print(transaccion_data)

#                 # ya NO vuelvas a crear la transacción, solo registra el cliente
#                 cliente = Clientes.objects.create(
#                     nombre=nombre,
#                     apellido=apellido,
#                     direccion=direccion,
#                     dui=dui,
#                     email=email,
#                     telefono=telefono,
#                 )

#                 # Registra la compra
#                 TransaccionCompra3DS.objects.create(
#                     transaccion3ds=transaccion3ds,
#                     transaccion3ds_respuesta=transaccion3ds_respuesta,
#                     #cliente=cliente,
#                 )

#                 # crea la compra
#                 compra = TransaccionCompra3DS.objects.create(
#                     transaccion3ds=transaccion3ds,
#                     transaccion3ds_respuesta=transaccion3ds_respuesta,
#                 )
#                 print(f"DEBUG - Se creó TransaccionCompra3DS con id: {compra.id}")

#                 # -------- ENVIAR CORREO DE CONFIRMACIÓN ------------
#                 asunto = "Confirmación de pago - X Soporte Latino"
#                 mensaje = (
#                     f"Estimado {nombre} {apellido},\n\n"
#                     f"Gracias por realizar su pago de ${monto:.2f}.\n"
#                     f"Su referencia de transacción es: {transaccion3ds_respuesta.idTransaccion}.\n\n"
#                     f"Saludos,\n"
#                     f"Equipo de X Soporte Latino"
#                 )
#                 send_mail(
#                     subject=asunto,
#                     message=mensaje,
#                     from_email="xsoportelatino@gmail.com",
#                     recipient_list=[email_client],
#                     fail_silently=False,
#                 )
#                 print(f"Correo de confirmación enviado a {email_client}")
#                 # -----------------------------------------------------

#                 # redirige con el id correcto
#                 return redirect('transaccion3ds_exitosa', transaccion3ds_id=compra.id)

#         except Exception as e:
#             print(f"Error en transacción 3DS: {e}")
#             return render(request, 'pago_fallido.html', {
#                 "error_message": str(e)
#             })

#     return redirect('home')
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def transaccion3ds_compra(request):
    if request.method != "POST":
        return redirect("home")

      # 1) Recolectar datos del formulario
    try:
        nombre       = request.POST["nombre"]
        apellido     = request.POST["apellido"]
        direccion    = request.POST["direccion"]
        ciudad       = "Los Angeles"
        email        = "xsoportelatino@gmail.com"
        telefono     = "72421660"
        numtarjeta   = request.POST["numtarjeta"].replace(" ", "")
        cvv          = request.POST["cvv"]
        mes          = request.POST["mesvencimiento"]
        anio         = request.POST["aniovencimiento"]
        monto        = float(request.POST.get("monto", 1))
    except Exception as e:
        return JsonResponse({
            "error": f"Error recolectando datos del formulario: {e}"
        }, status=400)

    if monto <= 0:
        return JsonResponse({
            "error": "Monto inválido. Debe ser mayor a 0."
        }, status=400)

    # 2) Autenticación Wompi
    try:
        cfg = wompi_config.objects.latest('created_at')
        token = authenticate_wompi(cfg.client_id, cfg.client_secret)
        if not token:
            raise Exception("No se pudo obtener el token de acceso desde Wompi. Verifique sus credenciales o intente más tarde.")
    except Exception as e:
        return JsonResponse({
            "error": f"Error de autenticación con Wompi: {e}"
        }, status=502)

    url_redirect = "https://xsoporte.contaspro.cloud/pago-directo/exitoso/"

    # 3) Llamar al API 3DS y guardar Transaccion3DS + Respuesta
    try:
        trans, resp, data = crear_transaccion_3ds(
            numeroTarjeta=numtarjeta,
            cvv=cvv,
            mesVencimiento=mes,
            anioVencimiento=anio,
            monto=monto,
            nombre=nombre,
            apellido=apellido,
            email=email,
            ciudad=ciudad,
            direccion=direccion,
            telefono=telefono,
            url_redirect=url_redirect
        )
    except ValueError as ve:
        return JsonResponse({
            "error": str(ve)
        }, status=400)
    except requests.exceptions.Timeout:
        return JsonResponse({
            "error": "La solicitud a Wompi excedió el tiempo de espera (timeout). Por favor intenta de nuevo."
        }, status=504)
    except requests.exceptions.ConnectionError:
        return JsonResponse({
            "error": "No hay conexión con la API de Wompi. Puede ser un problema temporal de red."
        }, status=503)
    except requests.exceptions.HTTPError as err:
        # Errores HTTP específicos
        status_code = err.response.status_code if err.response else 500
        detail = ""
        try:
            detail = err.response.json().get('error', err.response.text)
        except Exception:
            detail = err.response.text if err.response else str(err)
        return JsonResponse({
            "error": f"Error HTTP {status_code} de Wompi: {detail}"
        }, status=status_code)
    except Exception as e:
        return JsonResponse({
            "error": f"Error inesperado al crear la transacción: {e}"
        }, status=500)

    # 4) Crear el registro de compra UNA VEZ que ya existen trans y resp
    try:
        with transaction.atomic():
            cliente = Clientes.objects.create(
                nombre=nombre,
                apellido=apellido,
                direccion=direccion,
                email=email,
                telefono=telefono
            )
            compra = TransaccionCompra3DS.objects.create(
                transaccion3ds=trans,
                transaccion3ds_respuesta=resp,
            )
    except Exception as e:
        return JsonResponse({
            "error": f"Error guardando el registro de compra en base de datos: {e}"
        }, status=500)

    # 5) Devolver al JS la URL de 3DS para redirigir al emisor
    return JsonResponse({
        "url3ds": resp.urlCompletarPago3Ds
    }, status=200)



def pago_directo_view(request):
    return render(request, "transaccion_3ds.html")

# Nueva vista para mostrar el mensaje de éxito
def transaccion3ds_exitosa(request):
    # Wompi redirige a .../exitoso/?idTransaccion=<uuid>&otros=params
    id_transac = request.GET.get('idTransaccion')
    if not id_transac:
        return render(request, 'pago_fallido.html', {
            'error_message': 'No se recibió el identificador de transacción.'
        })

    # 1) Buscamos la respuesta Wompi
    resp = get_object_or_404(Transaccion3DS_Respuesta, idTransaccion=id_transac)

    # 2) Encontramos la TransaccionCompra3DS que tenga esa respuesta
    compra = get_object_or_404(TransaccionCompra3DS,
                               transaccion3ds_respuesta=resp)

    # 3) Verificamos si aprobó
    consulta = consultar_transaccion_3ds(id_transac)
    es_aprobada = consulta.get('esAprobada', False)

    return render(request, 'transaccion_exitosa.html', {
        'transaccion_compra': compra,
        'transaccion3ds_respuesta': resp,
        'es_aprobada': es_aprobada,
        'consulta_transaccion': consulta,
    })

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

def wompi_regiones(request):
    wompi_config = get_wompi_config()
    Client_id = wompi_config.client_id
    Client_secret = wompi_config.client_secret

    access_token = authenticate_wompi(Client_id, Client_secret)
    
    endpoint = "/api/Regiones"
    url = f"https://api.wompi.sv/{endpoint}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    regiones = []
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        print("========== RESPUESTA COMPLETA WOMPI ==========")
        print(data)
        print("===============================================")
        
        if isinstance(data, list):
            print("✅ data es LISTA")
            regiones = data
        elif isinstance(data, dict) and "data" in data:
            print("✅ data es DICCIONARIO con clave 'data'")
            regiones = data["data"]
        else:
            print("⚠️ data es otro tipo no esperado")
            regiones = []
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener regiones desde Wompi: {e}")
        regiones = []
    
    print("========== REGIONES FINAL ==========")
    print(regiones)
    print("====================================")

    return render(request, "regiones.html", {"regiones": regiones})
