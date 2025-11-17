from flask import Flask, request, jsonify, send_file, render_template, Response
from flask_cors import CORS
import yt_dlp
import os
import re
from pathlib import Path
import subprocess
import tempfile
import shutil
import time
import traceback
from urllib.parse import quote

app = Flask(__name__, 
            static_folder='src', 
            static_url_path='/static',
            template_folder='public')
CORS(app)

def sanitize_filename(filename):
    """Limpia el nombre del archivo para que sea seguro para el sistema de archivos"""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    if len(filename) > 200:
        filename = filename[:200]
    return filename


def download_video(url, format_id=None):
    """Descarga el video o audio según el formato especificado (simple y confiable)"""
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()

        # Verifica FFmpeg
        try:
            subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                check=True,
                timeout=5
            )
            ffmpeg_available = True
        except:
            ffmpeg_available = False

        # Determina si es audio o video
        if format_id and ('audio' in format_id.lower() and 'video' not in format_id.lower()):
            is_audio = True
            ydl_format = 'bestaudio/best'
        else:
            is_audio = False
            ydl_format = 'bv*+ba/b'

        ydl_opts = {
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': False,
            'noplaylist': True,
            'socket_timeout': 30,
            'retries': 3,
            'format': ydl_format,
        }

        if is_audio:
            if ffmpeg_available:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
        else:
            ydl_opts['merge_output_format'] = 'mp4'

        print(f"Descargando {('audio' if is_audio else 'video')} con formato: {ydl_format}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = sanitize_filename(info.get('title', 'video'))

        # Buscar archivo descargado
        files = [
            f for f in os.listdir(temp_dir)
            if os.path.isfile(os.path.join(temp_dir, f)) and not f.endswith('.part')
        ]

        if not files:
            raise Exception("No se encontró ningún archivo descargado.")

        downloaded_file = max(
            (os.path.join(temp_dir, f) for f in files),
            key=lambda p: os.path.getsize(p)
        )

        file_size = os.path.getsize(downloaded_file)
        if file_size < 10240:
            raise Exception(f"Archivo muy pequeño ({file_size} bytes). Descarga fallida o incompleta.")

        if is_audio:
            final_ext = '.mp3' if ffmpeg_available else os.path.splitext(downloaded_file)[1].lower()
        else:
            final_ext = '.mp4'

        final_filename = f"{title}{final_ext}"

        return {
            'file_path': downloaded_file,
            'filename': final_filename,
            'title': title,
            'temp_dir': temp_dir
        }

    except Exception as e:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise e


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/download', methods=['POST'])
def download():
    temp_dir = None
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type debe ser application/json'}), 415
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'El cuerpo de la petición debe ser JSON válido'}), 400
        
        url = data.get('url')
        format_type = data.get('format', 'video')
        
        if not url:
            return jsonify({'error': 'URL no proporcionada'}), 400
        
        format_id = 'bestaudio/best' if format_type == 'mp3' else None
        
        result = download_video(url, format_id)
        file_path = result['file_path']
        filename = result['filename']
        temp_dir = result['temp_dir']

        # 🔥 CORRECCIÓN: nombre normal sin encoding raro
        download_name = sanitize_filename(filename)
        content_disposition = f'attachment; filename="{download_name}"'

        def generate_file():
            try:
                with open(file_path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        yield chunk
            finally:
                try:
                    if temp_dir and os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    pass
        
        response = Response(
            generate_file(),
            mimetype='application/octet-stream',
            headers={
                'Content-Disposition': content_disposition,
                'Content-Type': 'application/octet-stream'
            }
        )
        
        return response
        
    except Exception as e:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        error_trace = traceback.format_exc()
        print(f"Error en /api/download: {str(e)}")
        print(error_trace)

        return jsonify({
            'error': str(e),
            'details': error_trace
        }), 500


if __name__ == '__main__':
    import os
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    app.run(debug=DEBUG, host=HOST, port=PORT)
