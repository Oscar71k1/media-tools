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
            # Usar formatos más simples que no requieran PO tokens
            ydl_format = 'best[ext=mp4]/best[height<=720]/best[height<=480]/best'

        # User-Agent actualizado y realista
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # Extraer visitor_data de las cookies si existen
        visitor_data = None
        cookies_file_path = None
        
        # Primero intentar leer cookies desde variable de entorno
        cookies_from_env = os.getenv('YOUTUBE_COOKIES')
        if cookies_from_env:
            try:
                # Crear archivo temporal con las cookies de la variable de entorno
                cookies_file_path = os.path.join(temp_dir, 'cookies_temp.txt')
                with open(cookies_file_path, 'w', encoding='utf-8') as f:
                    f.write(cookies_from_env)
                print("Cookies cargadas desde variable de entorno YOUTUBE_COOKIES")
            except Exception as e:
                print(f"Error al crear archivo temporal de cookies: {e}")
                cookies_file_path = None
        
        # Si no hay cookies en variable de entorno, usar archivo local
        if not cookies_file_path and os.path.exists('cookies.txt'):
            cookies_file_path = 'cookies.txt'
            print("Cookies cargadas desde archivo cookies.txt")
        
        # Extraer visitor_data de las cookies
        if cookies_file_path:
            try:
                with open(cookies_file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if 'VISITOR_INFO1_LIVE' in line and not line.strip().startswith('#'):
                            parts = line.strip().split('\t')
                            if len(parts) >= 7:
                                visitor_data = parts[6]  # El valor de la cookie
                                print(f"Visitor data extraído: {visitor_data[:20]}...")
                                break
            except Exception as e:
                print(f"Error al extraer visitor_data: {e}")
                pass
        
        ydl_opts = {
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': False,
            'noplaylist': True,
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'format': ydl_format,
            
            # User-Agent realista
            'user_agent': user_agent,
            
            # Headers completos de navegador real
            'http_headers': {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            },
            
            # Configuración específica para YouTube - se probarán diferentes clientes
            'extractor_args': {
                'youtube': {
                    'player_client': ['mweb'],  # Empezar con mweb (móvil web) que suele funcionar mejor
                    'player_skip': ['webpage'],
                }
            },
            
            # Evitar detección adicional
            'no_check_certificate': False,
            'prefer_insecure': False,
        }
        
        # Agregar visitor_data si se encontró en las cookies
        if visitor_data:
            ydl_opts['extractor_args']['youtube']['visitor_data'] = visitor_data
            print(f"✅ Visitor data configurado: {visitor_data[:30]}...")
        else:
            print("⚠️ No se encontró visitor_data en las cookies")
        
        # Agregar cookies si existe el archivo (de variable de entorno o local)
        if cookies_file_path and os.path.exists(cookies_file_path):
            ydl_opts['cookiefile'] = cookies_file_path
            # Verificar que el archivo tenga contenido
            try:
                with open(cookies_file_path, 'r', encoding='utf-8') as f:
                    cookie_lines = [l for l in f if l.strip() and not l.strip().startswith('#')]
                    print(f"✅ Cookies configuradas: {len(cookie_lines)} cookies encontradas en {cookies_file_path}")
            except Exception as e:
                print(f"⚠️ Error al verificar cookies: {e}")
        else:
            print("⚠️ No se encontró archivo de cookies")

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
        
        # Estrategia: probar diferentes clientes y formatos
        client_strategies = ['mweb', 'tv_embedded', 'web', 'android', 'ios']
        format_strategies = [ydl_format]
        if not is_audio:
            format_strategies.extend([
                'best[ext=mp4]/best',
                'bestvideo+bestaudio/best',
                'worstvideo+worstaudio/worst',
                'best',
                'worst'
            ])
        else:
            format_strategies.extend(['bestaudio', 'worstaudio'])
        
        last_error = None
        success = False
        json_blocked_count = 0  # Contador de errores de JSON bloqueado
        
        # Probar diferentes clientes
        for client in client_strategies:
            if success:
                break
                
            ydl_opts['extractor_args']['youtube']['player_client'] = [client]
            if visitor_data:
                ydl_opts['extractor_args']['youtube']['visitor_data'] = visitor_data
            
            client_json_blocked = False
            
            # Probar diferentes formatos con este cliente
            for fmt_strategy in format_strategies:
                try:
                    ydl_opts['format'] = fmt_strategy
                    print(f"Intentando con cliente '{client}' y formato: {fmt_strategy}")
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        title = sanitize_filename(info.get('title', 'video'))
                        success = True
                        break  # Si funciona, salir del loop
                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()
                    error_str = str(e)
                    
                    # Detectar si YouTube está bloqueando JSON completamente
                    if 'failed to parse json' in error_msg or 'failed to extract any player response' in error_msg:
                        json_blocked_count += 1
                        client_json_blocked = True
                        print(f"⚠️ YouTube está bloqueando respuestas JSON con cliente '{client}'")
                        # Si varios clientes tienen este problema, es un bloqueo general
                        if json_blocked_count >= 2:
                            print("⚠️ YouTube parece estar bloqueando completamente las descargas desde esta IP")
                            time.sleep(2)  # Delay antes de probar otro cliente
                        break  # Cambiar de cliente inmediatamente
                    # Si es un error de formato no disponible, intentar el siguiente formato
                    elif 'format is not available' in error_msg or 'requested format' in error_msg:
                        print(f"Formato {fmt_strategy} no disponible, probando siguiente...")
                        continue
                    # Si hay problemas con firmas, probar otro cliente
                    elif 'signature' in error_msg or 'challenge' in error_msg or 'sabr' in error_msg:
                        print(f"Cliente '{client}' tiene problemas con firmas, probando otro cliente...")
                        break
                    # Si es un error de bot detection
                    elif 'bot' in error_msg or 'confirm that you are not a bot' in error_msg:
                        print(f"⚠️ YouTube detectó bot con cliente '{client}'")
                        json_blocked_count += 1
                        break
                    else:
                        # Si es otro tipo de error, continuar con siguiente formato
                        print(f"Error con formato {fmt_strategy}: {error_str[:100]}")
                        continue
            
            # Si este cliente fue bloqueado, agregar delay antes del siguiente
            if client_json_blocked:
                time.sleep(1)
        
        if not success:
            # Si todos los formatos y clientes fallaron
            if json_blocked_count >= 2:
                raise Exception("YouTube está bloqueando las descargas desde esta IP. Esto puede deberse a: 1) Detección de bot, 2) IP bloqueada, 3) Cookies expiradas. Intenta actualizar las cookies o usar un proxy diferente.")
            elif last_error:
                raise last_error
            else:
                raise Exception("No se pudo descargar con ningún formato o cliente disponible. YouTube puede estar bloqueando las descargas.")

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
    import socket
    
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # Función para obtener la IP local del dispositivo
    def get_local_ip():
        """Obtiene la IP local del dispositivo en la red"""
        try:
            # Conecta a un servidor externo para determinar la IP local
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # No necesita conectarse realmente, solo determina la interfaz
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            try:
                # Método alternativo
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                return ip
            except Exception:
                return 'localhost'
    
    # Obtener y mostrar la IP local
    local_ip = get_local_ip()
    
    print("\n" + "="*50)
    print("🚀 Servidor iniciado!")
    print("="*50)
    print(f"📱 Accede desde tu celular u otros dispositivos:")
    print(f"   http://{local_ip}:{PORT}")
    print(f"   http://{local_ip}:{PORT}/")
    print("="*50)
    print(f"💻 O desde este dispositivo:")
    print(f"   http://localhost:{PORT}")
    print(f"   http://127.0.0.1:{PORT}")
    print("="*50)
    print(f"🌐 Asegúrate de que tu celular esté en la misma red WiFi")
    print("="*50 + "\n")
    
    app.run(debug=DEBUG, host=HOST, port=PORT)
