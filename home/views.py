import base64
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
import requests
from .models import ContactMessage, Service, PaymentLink, MoovConfig
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