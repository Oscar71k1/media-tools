"""
Versión de producción de la aplicación Flask
Usa variables de entorno para configuración
"""
from flask import Flask, request, jsonify, send_file, render_template
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

# Configuración desde variables de entorno
FLASK_ENV = os.getenv('FLASK_ENV', 'production')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

# Directorio para guardar los archivos descargados
DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', 'downloads'))
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Límite de tamaño de archivo (por defecto 2GB)
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 2 * 1024 * 1024 * 1024))

def sanitize_filename(filename):
    """Limpia el nombre del archivo para que sea válido"""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    if len(filename) > 200:
        filename = filename[:200]
    return filename

def get_video_info(url):
    """Obtiene información del video sin descargarlo"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            has_drm = False
            formats = info.get('formats', [])
            for fmt in formats:
                if fmt.get('has_drm') or fmt.get('drm') or 'drm' in str(fmt).lower():
                    has_drm = True
                    break
            
            return {
                'title': info.get('title', 'Video'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Desconocido'),
                'has_drm': has_drm,
            }
    except Exception as e:
        error_msg = str(e).lower()
        if 'drm' in error_msg or 'protected' in error_msg or 'encrypted' in error_msg:
            raise Exception("Este video está protegido por DRM y no se puede descargar. Intenta con otro video.")
        raise Exception(f"Error al obtener información del video: {str(e)}")

def download_video(url, format_type='video'):
    """Descarga el video o audio según el formato especificado"""
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        
        if format_type == 'mp3':
            format_strategies = [
                'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
                'bestaudio/best',
                'worstaudio/worst',
                'audio',
            ]
        else:
            format_strategies = [
                'best[ext=mp4]/best',
                'worst[ext=mp4]/worst',
                'bestvideo+bestaudio/best',
                'bestvideo[height<=720]+bestaudio/best',
                'bestvideo[height<=480]+bestaudio/best',
                'best',
            ]
        
        base_opts = {
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'quiet': not DEBUG,
            'no_warnings': not DEBUG,
            'ignoreerrors': False,
            'extract_flat': False,
            'prefer_insecure': False,
            'noplaylist': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                }
            },
        }
        
        if format_type == 'mp3':
            try:
                subprocess.run(['ffmpeg', '-version'], 
                            capture_output=True, 
                            check=True, 
                            timeout=5)
                ffmpeg_available = True
            except:
                ffmpeg_available = False
            
            if ffmpeg_available:
                base_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
        
        last_error = None
        for format_strategy in format_strategies:
            try:
                ydl_opts = base_opts.copy()
                ydl_opts['format'] = format_strategy
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = sanitize_filename(info.get('title', 'video'))
                    
                    formats = info.get('formats', [])
                    has_video_audio = False
                    for fmt in formats:
                        vcodec = fmt.get('vcodec', 'none')
                        acodec = fmt.get('acodec', 'none')
                        if vcodec != 'none' or (acodec != 'none' and format_type == 'mp3'):
                            has_video_audio = True
                            break
                    
                    if not has_video_audio and formats:
                        raise Exception("Solo hay imágenes disponibles para este video.")
                    
                    downloaded_file = None
                    max_attempts = 30
                    attempt = 0
                    
                    while attempt < max_attempts:
                        time.sleep(1)
                        attempt += 1
                        
                        files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
                        
                        if not files:
                            if attempt < max_attempts:
                                continue
                            raise Exception("No se encontró ningún archivo descargado")
                        
                        max_size = 0
                        candidate_file = None
                        for f in files:
                            file_path = os.path.join(temp_dir, f)
                            if f.endswith('.part') or f.endswith('.mhtml'):
                                continue
                            if any(f.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                                continue
                            try:
                                file_size = os.path.getsize(file_path)
                                if file_size > max_size and file_size > 10240:
                                    max_size = file_size
                                    candidate_file = file_path
                            except OSError:
                                continue
                        
                        if candidate_file:
                            current_size = os.path.getsize(candidate_file)
                            time.sleep(0.5)
                            new_size = os.path.getsize(candidate_file)
                            
                            if current_size == new_size and current_size > 10240:
                                downloaded_file = candidate_file
                                break
                    
                    if not downloaded_file:
                        files = [f for f in os.listdir(temp_dir) 
                                if os.path.isfile(os.path.join(temp_dir, f)) and not f.endswith('.part')]
                        if files:
                            max_size = 0
                            for f in files:
                                file_path = os.path.join(temp_dir, f)
                                try:
                                    file_size = os.path.getsize(file_path)
                                    if file_size > max_size:
                                        max_size = file_size
                                        downloaded_file = file_path
                                except OSError:
                                    continue
                    
                    if not downloaded_file:
                        raise Exception("No se pudo encontrar el archivo descargado.")
                    
                    file_size = os.path.getsize(downloaded_file)
                    if file_size == 0:
                        raise Exception("El archivo descargado está vacío.")
                    if file_size < 10240:
                        raise Exception(f"El archivo descargado es muy pequeño ({file_size} bytes).")
                    if file_size > MAX_FILE_SIZE:
                        raise Exception(f"El archivo es demasiado grande ({file_size} bytes).")
                    
                    if format_type == 'mp3':
                        if not ffmpeg_available:
                            file_ext = os.path.splitext(downloaded_file)[1].lower()
                            if file_ext in ['.m4a', '.webm', '.opus', '.ogg', '.aac']:
                                final_ext = file_ext
                            else:
                                final_ext = '.m4a'
                        else:
                            final_ext = '.mp3'
                    else:
                        final_ext = '.mp4'
                    
                    final_filename = f"{title}{final_ext}"
                    final_path = DOWNLOAD_DIR / final_filename
                    
                    counter = 1
                    while final_path.exists():
                        final_filename = f"{title}_{counter}{final_ext}"
                        final_path = DOWNLOAD_DIR / final_filename
                        counter += 1
                    
                    shutil.copy2(downloaded_file, final_path)
                    
                    if os.path.getsize(final_path) == 0:
                        raise Exception("Error al copiar el archivo.")
                    
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    
                    return {
                        'filename': final_filename,
                        'path': str(final_path),
                        'title': title
                    }
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                if 'drm' in error_msg or 'protected' in error_msg or 'encrypted' in error_msg:
                    raise Exception("Este video está protegido por DRM y no se puede descargar.")
                if temp_dir and os.path.exists(temp_dir):
                    for f in os.listdir(temp_dir):
                        try:
                            os.remove(os.path.join(temp_dir, f))
                        except:
                            pass
                continue
        
        if last_error:
            error_msg = str(last_error).lower()
            if 'drm' in error_msg or 'protected' in error_msg or 'encrypted' in error_msg:
                raise Exception("Este video está protegido por DRM y no se puede descargar.")
            raise Exception(f"Error al descargar: {str(last_error)}")
        else:
            raise Exception("No se pudo descargar el archivo.")
            
    except Exception as e:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        error_msg = str(e).lower()
        if 'drm' in error_msg or 'protected' in error_msg or 'encrypted' in error_msg:
            raise Exception("Este video está protegido por DRM y no se puede descargar.")
        raise e

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/info', methods=['POST'])
def get_info():
    try:
        if not request.is_json:
            return jsonify({
                'error': 'Content-Type debe ser application/json'
            }), 415
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'El cuerpo de la petición debe ser JSON válido'}), 400
        
        url = data.get('url')
        if not url:
            return jsonify({'error': 'URL no proporcionada'}), 400
        
        info = get_video_info(url)
        return jsonify(info)
    except Exception as e:
        error_trace = traceback.format_exc() if DEBUG else None
        return jsonify({
            'error': str(e),
            'details': error_trace
        }), 500

@app.route('/api/download', methods=['POST'])
def download():
    try:
        if not request.is_json:
            return jsonify({
                'error': 'Content-Type debe ser application/json'
            }), 415
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'El cuerpo de la petición debe ser JSON válido'}), 400
        
        url = data.get('url')
        format_type = data.get('format', 'video')
        
        if not url:
            return jsonify({'error': 'URL no proporcionada'}), 400
        
        if format_type not in ['video', 'mp3']:
            return jsonify({'error': 'Formato inválido. Use "video" o "mp3"'}), 400
        
        result = download_video(url, format_type)
        return jsonify({
            'success': True,
            'filename': result['filename'],
            'title': result['title'],
            'download_url': f"/api/file/{result['filename']}"
        })
    except Exception as e:
        error_trace = traceback.format_exc() if DEBUG else None
        return jsonify({
            'error': str(e),
            'details': error_trace
        }), 500

@app.route('/api/file/<filename>')
def download_file(filename):
    file_path = DOWNLOAD_DIR / filename
    if file_path.exists():
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'Archivo no encontrado'}), 404

@app.route('/api/list', methods=['GET'])
def list_files():
    files = []
    for file_path in DOWNLOAD_DIR.iterdir():
        if file_path.is_file():
            files.append({
                'filename': file_path.name,
                'size': file_path.stat().st_size,
                'download_url': f"/api/file/{file_path.name}"
            })
    return jsonify(files)

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de health check para monitoreo"""
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(debug=DEBUG, host=HOST, port=PORT)



