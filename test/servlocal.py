import asyncio
import os
import threading
import time
import uuid
from http.server import SimpleHTTPRequestHandler, HTTPServer
from gtts import gTTS
import google.generativeai as genai
import mini.mini_sdk as MiniSdk
from mini.apis.api_sound import PlayAudio
from mini import AudioStorageType, MiniApiResultType
from dotenv import load_dotenv

# Cargar variables de entorno desde keys.env
load_dotenv("keys.env")

# Configurar claves
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Variables globales
SERVER_PORT = 8000
SERVER_HOST = "0.0.0.0"
server_thread = None
http_server = None
local_ip = None


# Handler clase HTTP
class AudioHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.getcwd(), **kwargs)

    def log_message(self, format, *args):
        # Silenciar mensajes de log del servidor
        pass


def ObtenerRespuestaChatbot(mensaje: str) -> str:
    """
    Obtiene una respuesta del chatbot
    """
    try:
        # Configurar modelo
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Crear chat
        chat = model.start_chat(history=[])

        # Obtener respuesta
        response = chat.send_message(mensaje)

        # Extraer texto de la respuesta
        return response.text

    except Exception as e:
        print(f"Error al comunicarse con Gemini: {e}")
        return "Ha ocurrido un error al procesar tu mensaje."


def GetIPLocal():
    """
    Obtiene la dirección IP local del dispositivo.
    """
    import socket
    try:
        # Crear un socket y conectarlo a un servidor externo
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print(f"Error al obtener la IP local: {e}")
        return "127.0.0.1"


def StartHTTPServer():
    """
    Inicia un servidor HTTP en un hilo separado
    """
    global http_server, server_thread

    try:
        http_server = HTTPServer((SERVER_HOST, SERVER_PORT), AudioHandler)
        server_thread = threading.Thread(target=http_server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        print(f"Servidor HTTP iniciado en http://{SERVER_HOST}:{SERVER_PORT}")
    except Exception as e:
        print(f"Error al iniciar el servidor HTTP: {e}")


def StopHTTPServer():
    """
    Detiene servidor HTTP
    """
    global http_server
    if http_server:
        http_server.shutdown()
        print("Servidor HTTP detenido")


async def GenerarReproducirTTS(texto: str):
    """
    Genera archivo de audio TTS y lo manda al robot usando servidor local
    """
    try:
        timestamp = int(time.time())
        audio_filename = f"respuesta_{timestamp}.mp3"

        # Convertir texto a audio
        tts = gTTS(text=texto, lang='es')
        tts.save(audio_filename)

        # Verificar si el archivo existe
        if not os.path.exists(audio_filename):
            raise FileNotFoundError(f"El archivo no fue generado en la ruta: {audio_filename}")
        print(f"Archivo de audio generado exitosamente: {audio_filename}")

        # Construir URL usando la IP local
        global local_ip
        audio_url = f"http://{local_ip}:{SERVER_PORT}/{audio_filename}"
        print(f"URL del audio: {audio_url}")

        # Reproducir el audio en el robot
        for intento in range(1, 4):
            print(f"Intento {intento} de reproducir audio...")

            # Reproducir el archivo de audio en el robot
            block = PlayAudio(
                url=audio_url,
                storage_type=AudioStorageType.NET_PUBLIC,
                volume=1.0
            )
            result_type, response = await block.execute()

            if result_type == MiniApiResultType.Success and response.isSuccess:
                print("Audio reproducido exitosamente")
                break
            else:
                print(f"Error al reproducir audio: {response.resultCode}")
                if intento < 3:
                    print("Reintentando en 2 segundos...")
                    await asyncio.sleep(2)

        # Eliminar el archivo después de reproducirlo
        os.remove(audio_filename)

    except Exception as e:
        print(f"Error durante la generación o reproducción de TTS: {e}")


async def _run():
    try:
        global local_ip
        local_ip = GetIPLocal()
        print(f"IP local: {local_ip}")

        # Iniciar servidor HTTP
        StartHTTPServer()

        print("Buscando el robot...")
        device = await MiniSdk.get_device_by_name("20256", 10)
        if device:
            print("Robot encontrado, conectando...")
            is_connected = await MiniSdk.connect(device)
            if not is_connected:
                print("No se pudo conectar al robot")
                StopHTTPServer()
                return

            print("Entrando en modo programa...")
            success = await MiniSdk.enter_program()
            if not success:
                print("No se pudo entrar en modo programa")
                StopHTTPServer()
                return

            # # Prueba de audio
            # print("Realizando prueba de audio...")
            # await GenerarReproducirTTS(
            #     "Prueba de audio. Si escuchas este mensaje, la configuración está funcionando correctamente.")

            print("Iniciando interacción con Gemini...")
            while True:
                mensaje = input("Escribe un mensaje para Gemini (o 'salir' para terminar): ")
                if mensaje.lower() == 'salir':
                    break

                # Respuesta del chatbot
                respuesta = ObtenerRespuestaChatbot(mensaje)
                print(f"Respuesta de Gemini: {respuesta}")

                # Generar y reproducir TTS
                await GenerarReproducirTTS(respuesta)

            print("Saliendo del modo programa...")
            await MiniSdk.quit_program()

            print("Liberando recursos...")
            await MiniSdk.release()
        else:
            print("No se encontró el robot")

        # Detener el servidor HTTP
        StopHTTPServer()

    except Exception as e:
        print(f"Error en la ejecución: {e}")
        StopHTTPServer()


MiniSdk.set_robot_type(MiniSdk.RobotType.MINI)


def main():
    asyncio.run(_run())


if __name__ == '__main__':
    main()