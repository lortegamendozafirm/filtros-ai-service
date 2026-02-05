import requests
import json
import time

# Tu URL real (sacada de tus mensajes anteriores)
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwZNe5k5FHGZTx9IOCEaR_94dzKLe1bxVi96VcGmYyBgYw3cDcfj5UqB_gftYtww785/exec"

def test_connection():
    print(f"📡 Conectando a Apps Script...")
    print(f"🔗 URL: {APPS_SCRIPT_URL}")

    payload = {
        "nombre": "PRUEBA DE CONEXIÓN - TEST",
        "carpetaId": "", # Opcional, lo dejamos vacío para probar
        "emailSA": "test@example.com"
    }

    try:
        start_time = time.time()
        
        # IMPORTANTE: Apps Script redirige (302), por eso allow_redirects=True es vital
        response = requests.post(
            APPS_SCRIPT_URL, 
            json=payload, 
            timeout=30, # Damos 30 segundos
            allow_redirects=True 
        )
        
        duration = time.time() - start_time
        
        print("\n--- RESULTADO ---")
        print(f"⏱️ Tiempo: {duration:.2f} segundos")
        print(f"🔢 Código de estado: {response.status_code}")
        
        try:
            print(f"📄 Respuesta JSON: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"📄 Respuesta Texto: {response.text}")

        if response.status_code == 200:
            print("\n✅ ÉXITO: El Apps Script funciona y es accesible desde aquí.")
        else:
            print("\n❌ ERROR: El servidor respondió, pero con error.")

    except requests.exceptions.ConnectTimeout:
        print("\n❌ TIMEOUT DE CONEXIÓN: No se pudo establecer conexión TCP.")
        print("Esto indica un bloqueo de red (Firewall/ISP) o URL incorrecta.")
    except Exception as e:
        print(f"\n❌ ERROR GENERAL: {e}")

if __name__ == "__main__":
    test_connection()