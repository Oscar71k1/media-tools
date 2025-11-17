/**
 * Componente VideoCard - Muestra la información del video
 */

export class VideoCard {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
    }

    /**
     * Formatea la duración en segundos a formato legible
     * @param {number} seconds - Duración en segundos
     * @returns {string} Duración formateada
     */
    formatDuration(seconds) {
        if (!seconds) return 'Desconocida';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }

    /**
     * Renderiza la tarjeta con la información del video
     * @param {Object} videoInfo - Información del video
     * @param {Function} onDownload - Callback cuando se presiona descargar
     */
    render(videoInfo, onDownload) {
        const { title, duration, thumbnail, uploader } = videoInfo;

        const cardHTML = `
            <div class="video-card">
                <div class="video-card-header">
                    ${thumbnail ? `<img src="${thumbnail}" alt="${title}" class="video-thumbnail" onerror="this.style.display='none'">` : ''}
                    <div class="video-details">
                        <h3 class="video-title">${this.escapeHtml(title)}</h3>
                        <div class="video-meta">
                            <div class="video-meta-item">
                                <span>👤</span>
                                <span>${this.escapeHtml(uploader || 'Desconocido')}</span>
                            </div>
                            <div class="video-meta-item">
                                <span>⏱️</span>
                                <span>${this.formatDuration(duration)}</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="video-actions">
                    <button 
                        id="downloadBtn" 
                        class="btn-download"
                    >
                        ⬇️ Descargar
                    </button>
                </div>
            </div>
        `;

        this.container.innerHTML = cardHTML;
        this.container.style.display = 'block';

        // Agregar event listener al botón de descarga (siempre habilitado)
        const downloadBtn = document.getElementById('downloadBtn');
        if (downloadBtn && onDownload) {
            downloadBtn.addEventListener('click', onDownload);
        }
    }

    /**
     * Renderiza una tarjeta básica cuando no se pudo obtener información
     * @param {string} url - URL del video
     * @param {Function} onDownload - Callback cuando se presiona descargar
     */
    renderBasic(url, onDownload) {
        const cardHTML = `
            <div class="video-card">
                <div class="video-card-header">
                    <div class="video-details" style="width: 100%;">
                        <h3 class="video-title">No se pudo obtener información del video</h3>
                        <div class="video-meta" style="margin-top: 15px;">
                            <div class="video-meta-item">
                                <span>🔗</span>
                                <span style="word-break: break-all; font-size: 0.9rem; color: var(--text-muted);">${this.escapeHtml(url)}</span>
                            </div>
                        </div>
                        <p style="color: var(--text-secondary); margin-top: 15px; font-size: 0.95rem;">
                            No se pudo obtener información previa, pero puedes intentar descargar directamente.
                        </p>
                    </div>
                </div>
                
                <div class="video-actions">
                    <button 
                        id="downloadBtn" 
                        class="btn-download"
                    >
                        ⬇️ Descargar sin información previa
                    </button>
                </div>
            </div>
        `;

        this.container.innerHTML = cardHTML;
        this.container.style.display = 'block';

        // Agregar event listener al botón de descarga
        const downloadBtn = document.getElementById('downloadBtn');
        if (downloadBtn && onDownload) {
            downloadBtn.addEventListener('click', onDownload);
        }
    }

    /**
     * Muestra un estado de carga
     */
    showLoading() {
        this.container.innerHTML = `
            <div class="video-card">
                <div style="text-align: center; padding: 40px;">
                    <div class="btn-loader" style="font-size: 2rem; margin-bottom: 20px;">⏳</div>
                    <p style="color: var(--text-secondary);">Obteniendo información del video...</p>
                </div>
            </div>
        `;
        this.container.style.display = 'block';
    }

    /**
     * Oculta la tarjeta
     */
    hide() {
        this.container.style.display = 'none';
    }

    /**
     * Escapa HTML para prevenir XSS
     * @param {string} text - Texto a escapar
     * @returns {string} Texto escapado
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Actualiza el estado del botón de descarga
     * @param {boolean} isLoading - Si está cargando
     */
    setDownloadLoading(isLoading) {
        const downloadBtn = document.getElementById('downloadBtn');
        if (downloadBtn) {
            downloadBtn.disabled = isLoading;
            downloadBtn.innerHTML = isLoading 
                ? '<span class="btn-loader">⏳</span> Descargando...' 
                : '⬇️ Descargar';
        }
    }
}

