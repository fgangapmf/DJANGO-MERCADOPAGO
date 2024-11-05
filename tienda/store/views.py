from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .models import Product, Order
import mercadopago
import os
from dotenv import load_dotenv
import json

load_dotenv()
# Lista de productos desde BD
def product_list(request):
    """
    Vista para mostrar la lista de productos disponibles
    """
    products = Product.objects.all()
    return render(request, 'store/product_list.html', {
        'products': products
    })
def create_preference(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)
        
        # PRIMERO: Crear orden en nuestra base de datos
        order = Order.objects.create(product=product)
        
        # Inicializar SDK de MercadoPago
        sdk = mercadopago.SDK(os.getenv('MERCADOPAGO_ACCESS_TOKEN'))
        
        # Construir URLs absolutas
        base_url = request.build_absolute_uri('/')[:-1]
        
        # DESPUÉS: Usar order.id en las URLs
        preference_data = {
            "items": [
                {
                    "title": product.name,
                    "quantity": 1,
                    "currency_id": "CLP",
                    "unit_price": float(product.price),
                    "description": product.description[:200],
                }
            ],
            "back_urls": {
                "success": f"{base_url}{reverse('store:payment_success', args=[order.id])}",
                "failure": f"{base_url}{reverse('store:payment_failure', args=[order.id])}",
                "pending": f"{base_url}{reverse('store:payment_pending', args=[order.id])}"
            },
            "auto_return": "approved",
            "external_reference": str(order.id),
            "notification_url": f"{base_url}/webhook",
        }
        
        # Debug: Imprimir datos de preferencia
        print("Preference Data:", json.dumps(preference_data, indent=2))
        
        # Crear la preferencia en MercadoPago
        preference_response = sdk.preference().create(preference_data)
        
        # Debug: Imprimir respuesta
        print("Preference Response:", json.dumps(preference_response, indent=2))
        
        # Verificar si la respuesta es exitosa . Consideramos tambièn la respuesta 201.
        if preference_response["status"] in [200, 201]:
            # Obtener la URL de pago
            init_point = preference_response["response"]["init_point"]
            
            # En modo desarrollo, usar sandbox_init_point
            if os.getenv('DEBUG', 'False').lower() == 'true':
                init_point = preference_response["response"]["sandbox_init_point"]
            
            # Redirigir directamente a la página de pago de MercadoPago
            return redirect(init_point)
        else:
            error_detail = json.dumps(preference_response, indent=2)
            return render(request, 'store/error.html', {
                'error': f"Error al crear preferencia. Detalles: {error_detail}"
            })
            
    except Exception as e:
        import traceback
        print(f"Error completo: {str(e)}")
        print(traceback.format_exc())
        
        # Si hay un error, intentar eliminar la orden si fue creada
        if 'order' in locals():
            try:
                order.delete()
            except:
                pass
                
        return render(request, 'store/error.html', {
            'error': f"Error al procesar el pago: {str(e)}"
        })

def payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    payment_id = request.GET.get('payment_id')
    status = request.GET.get('status')
    
    # Actualizar la orden
    order.payment_id = payment_id
    order.payment_status = 'completed'
    order.save()
    
    return render(request, 'store/payment_success.html', {
        'order': order,
        'payment_id': payment_id,
        'status': status
    })

#En caso de error en el pago
def payment_failure(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    error = request.GET.get('error')
    
    order.payment_status = 'failed'
    order.save()
    
    return render(request, 'store/payment_failure.html', {
        'order': order,
        'error': error
    })

#Pago en estado pendiente
def payment_pending(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    order.payment_status = 'pending'
    order.save()
    
    return render(request, 'store/payment_pending.html', {
        'order': order
    })

# Webhook para recibir notificaciones de MercadoPago. Esto permite gestionar la respuesta del servicio.
@csrf_exempt
def webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if data["type"] == "payment":
                payment_id = data["data"]["id"]
                
                # Inicializar SDK
                sdk = mercadopago.SDK(os.getenv('MERCADOPAGO_ACCESS_TOKEN'))
                
                # Obtener información del pago
                payment_info = sdk.payment().get(payment_id)
                
                if payment_info["status"] == 200:
                    payment = payment_info["response"]
                    external_reference = payment.get("external_reference")
                    
                    if external_reference:
                        try:
                            order = Order.objects.get(id=external_reference)
                            order.payment_id = payment_id
                            order.payment_status = payment["status"]
                            order.save()
                        except Order.DoesNotExist:
                            return HttpResponse(status=404)
                
                return HttpResponse(status=200)
        except Exception as e:
            print(f"Webhook error: {str(e)}")
            return HttpResponse(status=400)
    
    return HttpResponse(status=200)