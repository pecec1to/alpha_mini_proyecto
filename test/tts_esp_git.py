import asyncio
import time
import os
from gtts import gTTS
import git
import mini.mini_sdk as MiniSdk
from mini.apis.api_sound import PlayAudio
from mini import AudioStorageType, MiniApiResultType






async def generarReproducirTTS():
    # texto para convertir a audio
    texto = "¡Hola! Soy AlphaMini."

    try:
        tts = gTTS(text=texto, lang='es')
        audio_path = "mensaje_es.mp3"
        tts.save(audio_path)

        # verificar si el archivo existe
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"El archivo no fue generado en la ruta: {audio_path}")
        print(f"Archivo de audio generado exitosamente: {audio_path}")

        # subir el archivo al repositorio
        copiarARepo(audio_path)

        # url pública del archivo en GitHub Pages
        timestamp = int(time.time())  # Genera un timestamp único
        public_url = f"https://pecec1to.github.io/audio/mensaje_es.mp3?cache_bust={timestamp}"

        # reproducir el archivo de audio en el robot
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

def copiarARepo(audio_path: str):
    try:
        # Clona repositorio si no está clonado
        if not os.path.exists("audio"):
            print("Clonando el repositorio...")
            git.Repo.clone_from("https://github.com/pecec1to/audio.git", "audio")

        # Elimina el archivo existente si existe
        repo_audio_path = "audio/mensaje_es.mp3"
        if os.path.exists(repo_audio_path):
            print(f"Eliminando archivo existente: {repo_audio_path}")
            os.remove(repo_audio_path)

        # Copia archivo al repositorio
        print(f"Copiando archivo {audio_path} al repositorio...")
        os.system(f"copy {audio_path} audio\\mensaje_es.mp3")  # Para Windows

        # Abre el repositorio
        repo = git.Repo("audio")

        # Añade archivo al repositorio (incluso si no hay cambios)
        print("Añadiendo archivo al repositorio...")
        repo.git.add("mensaje_es.mp3")

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

            print("Generando y reproduciendo TTS...")
            await generarReproducirTTS()

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