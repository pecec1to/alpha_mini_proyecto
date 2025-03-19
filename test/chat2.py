import asyncio
import os
import time
import uuid
import shutil
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

# Historial de chat para mantener contexto
chat_history = []


def obtener_respuesta_chatbot(mensaje: str) -> str:
    """
    Obtiene una respuesta del chatbot Gemini.
    """
    global chat_history

    try:
        # Configurar el modelo
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Crear el chat con historial
        chat = model.start_chat(history=chat_history)

        # Obtener respuesta
        response = chat.send_message(mensaje)

        # Actualizar historial
        chat_history.append({"role": "user", "parts": [mensaje]})
        chat_history.append({"role": "model", "parts": [response.text]})

        # Limitar el historial a las últimas 10 interacciones (5 pares)
        if len(chat_history) > 10:
            chat_history = chat_history[-10:]

        # Extraer texto de la respuesta
        return response.text

    except Exception as e:
        print(f"Error al comunicarse con Gemini: {e}")
        return "Ha ocurrido un error al procesar tu mensaje."


async def subir_y_reproducir_audio(audio_path: str, audio_filename: str):
    """
    Sube el audio a GitHub y lo reproduce en el robot.
    """
    try:
        # Clona repositorio si no está clonado
        if not os.path.exists("audio_repo"):
            print("Clonando el repositorio...")
            git.Repo.clone_from("https://github.com/pecec1to/audio.git", "audio_repo")

        # Actualizar el repositorio para evitar conflictos
        repo = git.Repo("audio_repo")
        origin = repo.remote(name='origin')
        origin.pull()

        # Ruta del archivo en el repositorio
        repo_audio_path = os.path.join("audio_repo", audio_filename)

        # Copia archivo al repositorio
        print(f"Copiando archivo {audio_path} al repositorio como {audio_filename}...")
        shutil.copy2(audio_path, repo_audio_path)

        # Añade archivo al repositorio
        print("Añadiendo archivo al repositorio...")
        repo.git.add(audio_filename)

        # Commit
        print("Haciendo commit...")
        repo.index.commit(f"Actualizar archivo de audio {audio_filename}")

        # Push
        print("Subiendo cambios a GitHub...")
        origin.push()

        print("Archivo subido a GitHub. Esperando a que esté disponible...")

        # Esperar a que el archivo esté disponible en GitHub Pages
        # Incrementamos el tiempo de espera a 5 segundos
        await asyncio.sleep(5)

        # URL pública del archivo en GitHub Pages con invalidación de caché
        timestamp = int(time.time())
        public_url = f"https://pecec1to.github.io/audio/{audio_filename}?cache={timestamp}"

        print(f"Intentando reproducir desde URL: {public_url}")

        # Reproducir el archivo de audio en el robot
        block = PlayAudio(
            url=public_url,
            storage_type=AudioStorageType.NET_PUBLIC,
            volume=1.0
        )
        result_type, response = await block.execute()

        if result_type == MiniApiResultType.Success and response.isSuccess:
            print("Audio reproducido exitosamente")
            return True
        else:
            print(f"Error al reproducir audio: {response.resultCode}")
            return False

    except Exception as e:
        print(f"Error durante la subida o reproducción: {e}")
        return False


async def generar_reproducir_tts(texto: str):
    """
    Genera un archivo de audio TTS, lo sube a GitHub y lo reproduce en el robot.
    """
    try:
        # Obtener directorio actual
        current_dir = os.getcwd()

        # Generar un nombre único para el archivo
        unique_id = str(uuid.uuid4())[:8]
        timestamp = int(time.time())
        audio_filename = f"respuesta_{unique_id}_{timestamp}.mp3"
        audio_path = os.path.join(current_dir, audio_filename)

        # Convertir texto a audio
        tts = gTTS(text=texto, lang='es')
        tts.save(audio_path)

        # Verificar si el archivo existe
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"El archivo no fue generado en la ruta: {audio_path}")
        print(f"Archivo de audio generado exitosamente: {audio_path}")

        # Intentar subir y reproducir el audio hasta 3 veces
        for intento in range(1, 4):
            print(f"Intento {intento} de subir y reproducir audio...")
            success = await subir_y_reproducir_audio(audio_path, audio_filename)
            if success:
                break
            else:
                print(f"Reintentando en 3 segundos...")
                await asyncio.sleep(3)

        # Eliminar el archivo local después de reproducirlo
        if os.path.exists(audio_path):
            os.remove(audio_path)

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