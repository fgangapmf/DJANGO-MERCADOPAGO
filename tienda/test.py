import mercadopago
import os
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    try:
        sdk = mercadopago.SDK(os.getenv('MERCADOPAGO_ACCESS_TOKEN'))
        
        # Intenta obtener los métodos de pago (operación simple)
        result = sdk.payment_methods().list_all()
        
        print("Status:", result["status"])
        print("Response:", result["response"])
        
        return result["status"] == 200
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing MercadoPago connection...")
    success = test_connection()
    print(f"Test {'successful' if success else 'failed'}")