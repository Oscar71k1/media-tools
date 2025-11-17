# Media tools



## ✨ Características

- 
- 🎵 Conversión a MP3
- 🖼️ Vista previa del video antes de descargar
- 📁 Lista de archivos descargados
- 🎨 Interfaz moderna y responsive

## 📋 Requisitos

- Python 3.8 o superior
- FFmpeg (necesario para la conversión a MP3)

### Instalar FFmpeg

**Windows:**
1. Descarga FFmpeg desde https://ffmpeg.org/download.html
2. Extrae el archivo y agrega la carpeta `bin` al PATH del sistema
3. O instala usando Chocolatey: `choco install ffmpeg`

**Linux:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

## 🚀 Instalación

1. Clona o descarga este repositorio

2. Instala las dependencias de Python:
```bash
pip install -r requirements.txt
```

## 💻 Uso

1. Inicia el servidor:
```bash
python app.py
```

2. Abre tu navegador y ve a:
```
http://localhost:5000
```

3. Pega la URL del video que quieres descargar (YouTube, Facebook o TikTok)

4. Haz clic en "Obtener Info" para ver la información del video

5. Selecciona si quieres descargar como video (MP4) o audio (MP3)

6. El archivo se descargará automáticamente

## 📝 Notas

- Los videos se guardan en la carpeta `downloads/`
- La aplicación soporta videos públicos de YouTube, Facebook y TikTok
- Para videos privados o con restricciones, puede que no funcionen
- La conversión a MP3 requiere FFmpeg instalado

## 🛠️ Tecnologías Utilizadas

- **Backend:** Flask (Python)
- **Descarga de videos:** yt-dlp
- **Frontend:** HTML, CSS, JavaScript
- **Conversión de audio:** FFmpeg

## ⚠️ Aviso Legal

Este software es solo para uso educativo y personal. Asegúrate de tener los derechos para descargar el contenido que descargues. Respeta los términos de servicio de las plataformas.

## 📄 Licencia

Este proyecto es de código abierto y está disponible para uso personal y educativo.




