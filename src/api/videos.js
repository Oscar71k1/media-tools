/**
 * Service Layer para todas las llamadas al backend
 */

// Usamos siempre el mismo origen desde donde se carga la app (ej: http://127.0.0.1:5000)
const API_BASE = window.location.origin;

/**
 * Descarga el video o audio en la mejor calidad disponible
 * @param {string} url - URL del video
 * @param {string} format - 'video' o 'mp3'
 * @returns {Promise<void>}
 */
export async function downloadVideo(url, format = 'video') {
    const endpoint = `${API_BASE}/api/download`;
    console.log('downloadVideo →', endpoint, { url, format });

    try {
        // Crear un AbortController con timeout muy largo (15 minutos)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15 * 60 * 1000); // 15 minutos

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url, format }),
            signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            // Si la respuesta no es OK, intentar leer el error como JSON
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `Error ${response.status}: ${response.statusText}`);
        }

        // La respuesta es un archivo binario, descargarlo directamente
        const blob = await response.blob();
        const contentDisposition = response.headers.get('content-disposition');
        let filename = 'video.mp4';
        
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (filenameMatch && filenameMatch[1]) {
                filename = filenameMatch[1].replace(/['"]/g, '');
            }
        }

        // Crear un enlace temporal y hacer clic para descargar
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);

        return { success: true, filename };
    } catch (error) {
        console.error('Error en downloadVideo:', error);
        
        // Manejar diferentes tipos de errores
        if (error.name === 'AbortError') {
            throw new Error('La descarga tardó demasiado tiempo. El video puede ser muy largo o tener restricciones. Intenta con un video más corto.');
        }
        
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            throw new Error('Error de conexión. Verifica que el servidor esté corriendo y que no haya problemas de red.');
        }
        
        throw new Error(error.message || 'Error al descargar el video');
    }
}

