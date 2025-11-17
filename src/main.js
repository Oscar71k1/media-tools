/**
 * Main Application Logic
 */

import { downloadVideo } from './api/videos.js';

// Estado de la aplicación
let currentFormat = 'video';

// Elementos del DOM
const videoForm = document.getElementById('videoForm');
const videoUrlInput = document.getElementById('videoUrl');
const downloadBtn = document.getElementById('downloadBtn');
const pasteBtn = document.getElementById('pasteBtn');

/**
 * Inicialización de la aplicación
 */
function init() {
    // Cargar última URL del localStorage
    const lastUrl = localStorage.getItem('lastVideoUrl');
    if (lastUrl) {
        videoUrlInput.value = lastUrl;
    }

    // Event listeners
    videoForm.addEventListener('submit', handleDownload);
    pasteBtn.addEventListener('click', handlePasteUrl);
}

/**
 * Maneja el evento de descargar
 */
async function handleDownload(e) {
    e.preventDefault();
    
    const url = videoUrlInput.value.trim();
    const format = document.querySelector('input[name="format"]:checked').value;

    // Validación
    if (!url) {
        showToast('Por favor ingresa una URL válida', 'error');
        return;
    }

    if (!isValidUrl(url)) {
        showToast('La URL no es válida', 'error');
        return;
    }

    // Guardar URL en localStorage
    localStorage.setItem('lastVideoUrl', url);
    currentFormat = format;
    
    // Actualizar estado del botón
    setButtonLoading(downloadBtn, true);
    showToast('Iniciando descarga en la mejor calidad... Esto puede tardar varios minutos, por favor espera.', 'success');

    try {
        console.log('Iniciando descarga de:', url, 'formato:', format);
        const startTime = Date.now();
        
        // Llamar al backend con el formato (video o mp3)
        const result = await downloadVideo(url, format);
        
        const elapsedTime = Math.round((Date.now() - startTime) / 1000);
        console.log(`Descarga completada en ${elapsedTime} segundos`);
        
        if (result.success) {
            showToast(`¡Descarga completada en ${elapsedTime}s!`, 'success');
        } else {
            throw new Error(result.error || 'Error al descargar');
        }
    } catch (error) {
        console.error('Error al descargar:', error);
        
        // Mensaje más descriptivo según el tipo de error
        let errorMessage = error.message || 'Error al descargar el video';
        
        // Detectar DRM real del backend
        if (error.message.includes('DRM') || error.message.includes('protegido')) {
            errorMessage = 'Este video está protegido por DRM y no se puede descargar.';
        } else if (error.message.includes('tardó demasiado')) {
            errorMessage = 'La descarga está tardando mucho. Esto puede ser normal para videos largos.';
        } else if (error.message.includes('conexión')) {
            errorMessage = 'Error de conexión con el servidor. Verifica que el servidor esté corriendo.';
        }
        
        showToast(errorMessage, 'error');
    } finally {
        setButtonLoading(downloadBtn, false);
    }
}

/**
 * Maneja el pegado de URL desde el portapapeles
 */
async function handlePasteUrl() {
    try {
        const text = await navigator.clipboard.readText();
        if (text) {
            videoUrlInput.value = text;
            showToast('URL pegada desde el portapapeles', 'success');
        }
    } catch (error) {
        videoUrlInput.focus();
        videoUrlInput.select();
        showToast('No se pudo leer el portapapeles. Pega manualmente (Ctrl+V)', 'warning');
    }
}

/**
 * Valida si una URL es válida
 */
function isValidUrl(string) {
    try {
        const url = new URL(string);
        return url.protocol === 'http:' || url.protocol === 'https:';
    } catch (_) {
        return false;
    }
}

/**
 * Muestra un toast notification
 */
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️'
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
        <span class="toast-message">${escapeHtml(message)}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 4000);
}

/**
 * Establece el estado de carga de un botón
 */
function setButtonLoading(button, isLoading) {
    if (!button) return;
    
    button.disabled = isLoading;
    const btnText = button.querySelector('.btn-text');
    const btnLoader = button.querySelector('.btn-loader');
    
    if (btnText && btnLoader) {
        btnText.style.display = isLoading ? 'none' : 'inline';
        btnLoader.style.display = isLoading ? 'inline-block' : 'none';
    }
}

/**
 * Escapa HTML para prevenir XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
