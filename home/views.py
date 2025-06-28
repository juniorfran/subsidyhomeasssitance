from django.shortcuts import render, redirect
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse
from .models import Service, PaymentLink

# SDK
from moovio_sdk import Moov
from moovio_sdk.models import components


def home(request):
    """
    Renderiza la página de inicio con los servicios activos
    """
    servicios = Service.objects.filter(es_activo=True).order_by("orden")
    return render(request, "home.html", {"servicios": servicios})


def crear_pago(request):
    """
    Procesa el formulario de pago desde el modal y redirige al enlace de pago generado por Moov
    """
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        correo = request.POST.get("correo")
        monto = request.POST.get("monto")
        descripcion = request.POST.get("descripcion", "")

        print("==== NUEVA SOLICITUD DE PAGO ====")
        print(f"Nombre: {nombre}")
        print(f"Correo: {correo}")
        print(f"Monto: {monto}")
        print(f"Descripción: {descripcion}")

        try:
            print("Iniciando creación de link de pago con Moov SDK...")

            with Moov(
                x_moov_version="v2024.01.00",
                security=components.Security(
                    username=settings.MOOV_USERNAME,
                    password=settings.MOOV_PASSWORD,
                ),
            ) as moov:
                print("✅ SDK autenticado correctamente")

                res = moov.payment_links.create(
                    account_id=settings.MOOV_ACCOUNT_ID,
                    partner_account_id=settings.MOOV_PARTNER_ACCOUNT_ID,
                    merchant_payment_method_id=settings.MOOV_MERCHANT_PAYMENT_METHOD_ID,
                    amount={
                        "currency": "USD",
                        "value": int(float(monto) * 100),
                    },
                    display={
                        "title": "Pago Hispanic Assistance",
                        "description": descripcion or "Pago desde formulario web",
                        "call_to_action": components.CallToAction.PAY,
                    },
                    customer={
                        "require_phone": False,
                    },
                    payment={
                        "allowed_methods": [
                            components.CollectionPaymentMethodType.CARD_PAYMENT,
                            components.CollectionPaymentMethodType.ACH_DEBIT_COLLECT,
                        ],
                    },
                )

                print("✅ Payment link creado exitosamente")
                print(f"Enlace generado: {res.link}")
                print(f"Detalles completos de respuesta: {res}")

                # Guardar en base de datos
                pago = PaymentLink.objects.create(
                    nombre=nombre,
                    correo=correo,
                    monto=monto,
                    descripcion=descripcion,
                    link=res.link
                )

                print(f"✅ Link guardado en la base de datos: {pago.link}")
                print("Redirigiendo al cliente...")

                return redirect(res.link)

        except Exception as e:
            print(f"❌ Error al generar link de pago: {e}")
            return render(request, "pago_error.html", {"error": str(e)})

    # Si no es POST
    print("⚠️ Solicitud GET recibida en crear_pago, redireccionando al home")
    return redirect(reverse("home"))

