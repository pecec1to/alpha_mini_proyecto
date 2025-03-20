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
import subprocess
import platform

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
bluetooth_device = None
USAR_BLUETOOTH = False  # Usar Bluetooth (True) o el robot (False)


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
        # Configurar el modelo
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Crear el chat
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
    Obtiene la dirección IP local del dispositivo
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
        return "127.0.0.1"  # Fallback a localhost


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
    Detiene el servidor HTTP
    """
    global http_server
    if http_server:
        http_server.shutdown()
        print("Servidor HTTP detenido")


def ListarDispBluetooth():
    """
    Lista los dispositivos Bluetooth disponibles
    """
    sistema = platform.system()

    if sistema == "Windows":
        try:
            print("Listando dispositivos Bluetooth en Windows...")
            # Usar PowerShell para listar dispositivos Bluetooth
            result = subprocess.run(
                ["powershell", "-Command", "Get-PnpDevice -Class Bluetooth"],
                capture_output=True, text=True
            )
            print(result.stdout)
            return result.stdout
        except Exception as e:
            print(f"Error al listar dispositivos Bluetooth en Windows: {e}")

    # elif sistema == "Linux":
    #     try:
    #         print("Listando dispositivos Bluetooth en Linux...")
    #         # Usar bluetoothctl para listar dispositivos
    #         result = subprocess.run(
    #             ["bluetoothctl", "devices"],
    #             capture_output=True, text=True
    #         )
    #         print(result.stdout)
    #         return result.stdout
    #     except Exception as e:
    #         print(f"Error al listar dispositivos Bluetooth en Linux: {e}")
    #
    # elif sistema == "Darwin":  # macOS
    #     try:
    #         print("Listando dispositivos Bluetooth en macOS...")
    #         # Usar system_profiler para listar dispositivos
    #         result = subprocess.run(
    #             ["system_profiler", "SPBluetoothDataType"],
    #             capture_output=True, text=True
    #         )
    #         print(result.stdout)
    #         return result.stdout
    #     except Exception as e:
    #         print(f"Error al listar dispositivos Bluetooth en macOS: {e}")
    #
    # else:
    #     print(f"Sistema operativo no soportado: {sistema}")

    return "No se pudieron listar los dispositivos Bluetooth"


def ConectarDispBluetooth(mac_address=None):
    """
    Conecta a un dispositivo Bluetooth por dirección MAC
    """
    global bluetooth_device

    sistema = platform.system()

    if mac_address is None:
        print("No se proporcionó una dirección MAC. Listando dispositivos disponibles...")
        ListarDispBluetooth()
        mac_address = input("Introduce la dirección MAC del dispositivo Bluetooth: ")

    if sistema == "Windows":
        try:
            print(f"Conectando al dispositivo Bluetooth {mac_address} en Windows...")
            # Usar PowerShell para conectar al dispositivo
            result = subprocess.run(
                ["powershell", "-Command", f"Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
                                           f"$asyncOperation = [Windows.Devices.Bluetooth.BluetoothDevice]::FromBluetoothAddressAsync('{mac_address}'); "
                                           f"$device = $asyncOperation.AsTask().GetAwaiter().GetResult(); "
                                           f"$device.DeviceId"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"Conectado exitosamente al dispositivo: {mac_address}")
                bluetooth_device = mac_address
                return True
            else:
                print(f"Error al conectar: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error al conectar al dispositivo Bluetooth en Windows: {e}")
            return False

    # elif sistema == "Linux":
    #     try:
    #         print(f"Conectando al dispositivo Bluetooth {mac_address} en Linux...")
    #         # Usar bluetoothctl para conectar
    #         result = subprocess.run(
    #             ["bluetoothctl", "connect", mac_address],
    #             capture_output=True, text=True
    #         )
    #         if "Connection successful" in result.stdout:
    #             print(f"Conectado exitosamente al dispositivo: {mac_address}")
    #             bluetooth_device = mac_address
    #             return True
    #         else:
    #             print(f"Error al conectar: {result.stdout}")
    #             return False
    #     except Exception as e:
    #         print(f"Error al conectar al dispositivo Bluetooth en Linux: {e}")
    #         return False
    #
    # elif sistema == "Darwin":  # macOS
    #     try:
    #         print(f"Conectando al dispositivo Bluetooth {mac_address} en macOS...")
    #         # En macOS, usamos BluetoothConnector (necesita estar instalado)
    #         result = subprocess.run(
    #             ["BluetoothConnector", mac_address, "--connect"],
    #             capture_output=True, text=True
    #         )
    #         if result.returncode == 0:
    #             print(f"Conectado exitosamente al dispositivo: {mac_address}")
    #             bluetooth_device = mac_address
    #             return True
    #         else:
    #             print(f"Error al conectar: {result.stderr}")
    #             return False
    #     except Exception as e:
    #         print(f"Error al conectar al dispositivo Bluetooth en macOS: {e}")
    #         print("Asegúrate de tener BluetoothConnector instalado: brew install bluetoothconnector")
    #         return False

    else:
        print(f"Sistema operativo no soportado: {sistema}")
        return False


def ReproducirAudioBluetooth(audio_path):
    """
    Reproduce un archivo de audio a través de un dispositivo Bluetooth.
    """
    global bluetooth_device

    if bluetooth_device is None:
        print("No hay ningún dispositivo Bluetooth conectado.")
        return False

    sistema = platform.system()

    try:
        if sistema == "Windows":
            # En Windows, usamos el reproductor predeterminado
            subprocess.run(["start", audio_path], shell=True)
            return True

        elif sistema == "Linux":
            # En Linux, usamos mpg123 o mplayer
            try:
                subprocess.run(["mpg123", audio_path], check=True)
                return True
            except:
                try:
                    subprocess.run(["mplayer", audio_path], check=True)
                    return True
                except:
                    print("No se pudo reproducir el audio. Asegúrate de tener mpg123 o mplayer instalados.")
                    return False

        elif sistema == "Darwin":  # macOS
            # En macOS, usamos afplay
            subprocess.run(["afplay", audio_path])
            return True

        else:
            print(f"Sistema operativo no soportado: {sistema}")
            return False

    except Exception as e:
        print(f"Error al reproducir audio por Bluetooth: {e}")
        return False


async def GenerarReproducirTTS(texto: str):
    """
    Genera un archivo de audio TTS y lo reproduce en el robot o por Bluetooth.
    """
    try:
        # Generar un nombre único para el archivo
        unique_id = str(uuid.uuid4())[:8]
        timestamp = int(time.time())
        audio_filename = f"respuesta_{unique_id}_{timestamp}.mp3"

        # Convertir texto a audio
        tts = gTTS(text=texto, lang='es')
        tts.save(audio_filename)

        # Verificar si el archivo existe
        if not os.path.exists(audio_filename):
            raise FileNotFoundError(f"El archivo no fue generado en la ruta: {audio_filename}")
        print(f"Archivo de audio generado exitosamente: {audio_filename}")

        # Reproducir según la configuración
        if USAR_BLUETOOTH:
            # Reproducir por Bluetooth
            print("Reproduciendo audio por Bluetooth...")
            success = ReproducirAudioBluetooth(audio_filename)
            if success:
                print("Audio reproducido exitosamente por Bluetooth")
            else:
                print("Error al reproducir audio por Bluetooth")
        else:
            # Reproducir en el robot
            global local_ip
            audio_url = f"http://{local_ip}:{SERVER_PORT}/{audio_filename}"
            print(f"URL del audio: {audio_url}")

            # Reproducir el audio en el robot
            for intento in range(1, 4):
                print(f"Intento {intento} de reproducir audio en el robot...")

                # Reproducir el archivo de audio en el robot
                block = PlayAudio(
                    url=audio_url,
                    storage_type=AudioStorageType.NET_PUBLIC,
                    volume=1.0
                )
                result_type, response = await block.execute()

                if result_type == MiniApiResultType.Success and response.isSuccess:
                    print("Audio reproducido exitosamente en el robot")
                    break
                else:
                    print(f"Error al reproducir audio en el robot: {response.resultCode}")
                    if intento < 3:
                        print("Reintentando en 2 segundos...")
                        await asyncio.sleep(2)

        # Mantener el archivo por un tiempo antes de eliminarlo
        await asyncio.sleep(5)

        # Eliminar el archivo después de reproducirlo
        if os.path.exists(audio_filename):
            os.remove(audio_filename)

    except Exception as e:
        print(f"Error durante la generación o reproducción de TTS: {e}")


async def _run():
    try:
        global local_ip, USAR_BLUETOOTH
        local_ip = GetIPLocal()
        print(f"IP local: {local_ip}")

        # Preguntar al usuario si quiere usar Bluetooth o el robot
        opcion = input("¿Deseas reproducir el audio por Bluetooth (B) o en el robot (R)? [B/R]: ").upper()
        if opcion == 'B':
            USAR_BLUETOOTH = True
            print("Modo Bluetooth activado")

            # Listar dispositivos Bluetooth
            ListarDispBluetooth()

            # Conectar a un dispositivo Bluetooth
            mac_address = input("Introduce la dirección MAC del dispositivo Bluetooth (deja en blanco para cancelar): ")
            if mac_address:
                conectado = ConectarDispBluetooth(mac_address)
                if not conectado:
                    print("No se pudo conectar al dispositivo Bluetooth. Cambiando a modo robot.")
                    USAR_BLUETOOTH = False
        else:
            USAR_BLUETOOTH = False
            print("Modo robot activado")

        # Iniciar el servidor HTTP (necesario para el robot)
        if not USAR_BLUETOOTH:
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
            else:
                print("No se encontró el robot")
                StopHTTPServer()
                return

        # Prueba de audio
        print("Realizando prueba de audio...")
        await GenerarReproducirTTS(
            "Prueba de audio. Si escuchas este mensaje, la configuración está funcionando correctamente.")

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

        # Limpiar recursos
        if not USAR_BLUETOOTH:
            print("Saliendo del modo programa...")
            await MiniSdk.quit_program()

            print("Liberando recursos...")
            await MiniSdk.release()

            # Detener el servidor HTTP
            StopHTTPServer()

    except Exception as e:
        print(f"Error en la ejecución: {e}")
        if not USAR_BLUETOOTH:
            StopHTTPServer()


MiniSdk.set_robot_type(MiniSdk.RobotType.MINI)


def main():
    asyncio.run(_run())


if __name__ == '__main__':
    main()