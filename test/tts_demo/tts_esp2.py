import asyncio
import os
import subprocess
from mini.mini_sdk import (
    set_log_level,
    set_robot_type,
    get_device_by_name,
    connect,
    enter_program,
    quit_program,
    release,
    RobotType,
    WiFiDevice
)
from mini.apis.api_sound import PlayAudio
from mini import AudioStorageType, MiniApiResultType
import pyttsx3  # Biblioteca de TTS

# Función para generar el archivo de audio usando pyttsx3
def generate_audio_with_pyttsx3(text: str, output_file: str):
    """
    Genera un archivo de audio usando pyttsx3.
    Args:
        text (str): Texto a convertir en audio.
        output_file (str): Ruta del archivo de salida.
    """
    engine = pyttsx3.init()

    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[0].id)  # Selecciona la primera voz disponible

    # Guardar el archivo de audio
    engine.save_to_file(text, output_file)
    engine.runAndWait()

# Función para subir el archivo al repositorio de GitHub Pages
def copy_file_to_github_pages(audio_path: str):
    """
    Copia el archivo de audio al repositorio de GitHub Pages.
    Args:
        audio_path (str): Ruta del archivo local.
    """
    try:
        # Clona el repositorio si no está clonado
        if not os.path.exists("play_tts/audio"):
            print("Clonando el repositorio 'audio'...")
            subprocess.run(["git", "clone", "https://github.com/pecec1to/audio.git"], check=True)

        # Copia el archivo al repositorio
        print(f"Copiando archivo {audio_path} al repositorio...")
        if os.name == 'nt':  # Si el sistema operativo es Windows
            subprocess.run(["copy", audio_path, "audio\\mensaje_2.mp3"], shell=True, check=True)
        else:  # Para sistemas Unix/Linux/Mac
            subprocess.run(["cp", audio_path, "audio/mensaje_2.mp3"], check=True)

        # Cambia al directorio del repositorio
        os.chdir("play_tts/audio")

        # Añade el archivo al repositorio
        print("Añadiendo archivo al repositorio...")
        subprocess.run(["git", "add", "mensaje_2.mp3"], check=True)

        # Haz commit de los cambios
        print("Haciendo commit...")
        subprocess.run(["git", "commit", "-m", "Audio 2"], check=True)

        # Sube los cambios a GitHub
        print("Subiendo cambios a GitHub...")
        subprocess.run(["git", "push", "origin", "main"], check=True)

        print("Archivo subido exitosamente a GitHub Pages.")
    except subprocess.CalledProcessError as e:
        print(f"Error al subir el archivo a GitHub Pages: {e}")

async def _generate_and_play_tts():
    # Texto en español para convertir a audio
    texto = "¡Hola! Soy AlphaMini, pero ahora estoy usando otra librería."

    try:
        # Generar el archivo de audio usando pyttsx3
        audio_path = "play_tts/mensaje_2.mp3"
        generate_audio_with_pyttsx3(texto, audio_path)

        # Verificar si el archivo existe
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"El archivo no fue generado en la ruta: {audio_path}")
        print(f"Archivo de audio generado exitosamente: {audio_path}")

        # Subir el archivo al repositorio de GitHub Pages
        copy_file_to_github_pages(audio_path)

        # URL pública del archivo en GitHub Pages
        public_url = "https://pecec1to.github.io/audio/mensaje_2.mp3"

        # Reproducir el archivo de audio en el robot
        block = PlayAudio(
            url=public_url,  # URL pública del archivo
            storage_type=AudioStorageType.NET_PUBLIC,  # Tipo de almacenamiento: red pública
            volume=1.0  # Volumen máximo
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
        # Configuración inicial
       # set_log_level(logging.INFO)
        set_robot_type(RobotType.MINI)

        # Buscar el robot
        print("Buscando el robot...")
        device = await get_device_by_name("20256", timeout=10)
        if not device:
            print("No se encontró el robot")
            return

        # Conectar al robot
        print("Robot encontrado, conectando...")
        is_connected = await connect(device)
        if not is_connected:
            print("No se pudo conectar al robot")
            return

        # Entrar en modo programa
        print("Entrando en modo programa...")
        success = await enter_program()
        if not success:
            print("No se pudo entrar en modo programa")
            return

        # Generar y reproducir TTS
        print("Generando y reproduciendo TTS...")
        await _generate_and_play_tts()

        # Salir del modo programa
        print("Saliendo del modo programa...")
        await quit_program()

        # Liberar recursos
        print("Liberando recursos...")
        await release()
    except Exception as e:
        print(f"Error en la ejecución: {e}")

# Punto de entrada principal
if __name__ == '__main__':
    asyncio.run(_run())