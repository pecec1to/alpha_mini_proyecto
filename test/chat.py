import asyncio
import os
import subprocess
from dotenv import load_dotenv
from gtts import gTTS
import google.generativeai as genai
import mini.mini_sdk as MiniSdk
from mini.apis.api_sound import PlayAudio
from mini import AudioStorageType, MiniApiResultType

# Cargar variables de entorno desde keys.env
load_dotenv("keys.env")

# Configurar claves desde variables de entorno
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Configurar Google API
genai.configure(api_key=GOOGLE_API_KEY)

def obtener_respuesta_chatbot(mensaje: str) -> str:
    """
    Gets a response from the Gemini chatbot.
    """
    try:
        # Configure the model
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Create the chat
        chat = model.start_chat(history=[])

        # Get response
        response = chat.send_message(mensaje)

        # Extract text from the response
        return response.text

    except Exception as e:
        print(f"Error al comunicarse con Gemini: {e}")
        return "Ha ocurrido un error al procesar tu mensaje."


# Function to copy files to the repository
def copiarARepo(audio_path: str):
    try:
        # Clone repository if not already cloned
        if not os.path.exists("audio"):
            print("Clonando el repositorio...")
            subprocess.run(["git", "clone", "https://github.com/pecec1to/audio.git"], check=True)

        # Copy file to repository using correct syntax for Windows
        print(f"Copiando archivo {audio_path} al repositorio...")
        subprocess.run(["copy", audio_path, "audio\\respuesta_chatbot.mp3"], shell=True, check=True)

        # Change to repository directory
        current_dir = os.getcwd()
        os.chdir("audio")

        # Add file to repository
        print("Añadiendo archivo al repositorio...")
        subprocess.run(["git", "add", "respuesta_chatbot.mp3"], check=True)

        # Commit
        print("Haciendo commit...")
        subprocess.run(["git", "commit", "-m", "Añadir archivo de audio"], check=True)

        # Push
        print("Subiendo cambios a GitHub...")
        subprocess.run(["git", "push", "origin", "main"], check=True)

        print("Archivo subido a GitHub.")

        # Return to original directory
        os.chdir(current_dir)
    except subprocess.CalledProcessError as e:
        print(f"Error al subir el archivo a GitHub: {e}")


async def generar_reproducir_tts_chatbot(mensaje_usuario: str):
    """
    Generates and plays the chatbot response as audio.
    """
    try:
        # Get response from chatbot
        print("Obteniendo respuesta de Gemini...")
        respuesta = obtener_respuesta_chatbot(mensaje_usuario)
        print(f"Respuesta de Gemini: {respuesta}")

        # Convert response to audio
        tts = gTTS(text=respuesta, lang='es')
        audio_path = "respuesta_chatbot.mp3"
        tts.save(audio_path)

        # Verify if file exists
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"El archivo no fue generado en la ruta: {audio_path}")
        print(f"Archivo de audio generado exitosamente: {audio_path}")

        # Upload file to repository
        copiarARepo(audio_path)

        # Public URL of the file on GitHub Pages
        public_url = "https://pecec1to.github.io/audio/respuesta_chatbot.mp3"

        # Play audio file on the robot
        block = PlayAudio(
            url=public_url,
            storage_type=AudioStorageType.NET_PUBLIC,
            volume=1.0
        )
        result_type, response = await block.execute()

        if result_type == MiniApiResultType.Success and response.isSuccess:
            print("Audio reproducido exitosamente")
        else:
            print(f"Error al reproducir audio: {response.resultCode}")

    except Exception as e:
        print(f"Error durante la generación o reproducción de TTS: {e}")


async def _run():
    try:
        print("Buscando el robot...")
        device = await MiniSdk.get_device_by_name("20256", 10)
        if device:
            print("Robot encontrado, conectando...")
            is_connected = await MiniSdk.connect(device)
            if not is_connected:
                print("No se pudo conectar al robot")
                return

            print("Entrando en modo programa...")
            success = await MiniSdk.enter_program()
            if not success:
                print("No se pudo entrar en modo programa")
                return

            print("Iniciando interacción con Gemini...")
            while True:
                mensaje = input("Escribe un mensaje para Gemini (o 'salir' para terminar): ")
                if mensaje.lower() == 'salir':
                    break

                await generar_reproducir_tts_chatbot(mensaje)

            print("Saliendo del modo programa...")
            await MiniSdk.quit_program()

            print("Liberando recursos...")
            await MiniSdk.release()
        else:
            print("No se encontró el robot")
    except Exception as e:
        print(f"Error en la ejecución: {e}")


MiniSdk.set_robot_type(MiniSdk.RobotType.MINI)


def main():
    asyncio.run(_run())


if __name__ == '__main__':
    main()