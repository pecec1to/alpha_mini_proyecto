import asyncio
import os
import time
from gtts import gTTS
import git
import google.generativeai as genai
import mini.mini_sdk as MiniSdk
from mini.apis.api_sound import PlayAudio
from mini import AudioStorageType, MiniApiResultType
from dotenv import load_dotenv

# Cargar variables de entorno desde keys.env
load_dotenv("keys.env")

# Configurar claves desde variables de entorno
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Configurar Google API
genai.configure(api_key=GOOGLE_API_KEY)


def obtener_respuesta_chatbot(mensaje: str) -> str:
    """
    Obtiene una respuesta del chatbot Gemini.
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


def copiarARepo(audio_path: str):
    """
    Copia un archivo al repositorio Git y lo sube a GitHub.
    """
    try:
        # Clona repositorio si no está clonado
        if not os.path.exists("audio_repo"):
            print("Clonando el repositorio...")
            git.Repo.clone_from("https://github.com/pecec1to/audio.git", "audio_repo")

        # Elimina el archivo existente si existe
        repo_audio_path = "audio_repo/respuesta_chatbot.mp3"
        if os.path.exists(repo_audio_path):
            print(f"Eliminando archivo existente: {repo_audio_path}")
            os.remove(repo_audio_path)

        # Copia archivo al repositorio
        print(f"Copiando archivo {audio_path} al repositorio...")
        os.system(f"copy {audio_path} audio_repo\\respuesta_chatbot.mp3")  # Para Windows

        # Abre el repositorio
        repo = git.Repo("audio_repo")

        # Añade archivo al repositorio (incluso si no hay cambios)
        print("Añadiendo archivo al repositorio...")
        repo.git.add("respuesta_chatbot.mp3")

        # Commit (forzado)
        print("Haciendo commit...")
        repo.index.commit("Actualizar archivo de audio")

        # Push
        print("Subiendo cambios a GitHub...")
        origin = repo.remote(name='origin')
        origin.push()

        print("Archivo subido a GitHub.")

    except Exception as e:
        print(f"Error al subir el archivo a GitHub: {e}")


async def generar_reproducir_tts(texto: str):
    """
    Genera un archivo de audio TTS, lo sube a GitHub y lo reproduce en el robot.
    """
    try:
        # Convertir texto a audio
        tts = gTTS(text=texto, lang='es')
        audio_path = "respuesta_chatbot.mp3"
        tts.save(audio_path)

        # Verificar si el archivo existe
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"El archivo no fue generado en la ruta: {audio_path}")
        print(f"Archivo de audio generado exitosamente: {audio_path}")

        # Subir el archivo al repositorio
        copiarARepo(audio_path)

        # URL pública del archivo en GitHub Pages con invalidación de caché
        timestamp = int(time.time())  # Genera un timestamp único
        public_url = f"https://pecec1to.github.io/audio/respuesta_chatbot.mp3?cache_bust={timestamp}"

        # Reproducir el archivo de audio en el robot
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

                # Respuesta del chatbot
                respuesta = obtener_respuesta_chatbot(mensaje)
                print(f"Respuesta de Gemini: {respuesta}")

                # Generar y reproducir TTS
                await generar_reproducir_tts(respuesta)

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