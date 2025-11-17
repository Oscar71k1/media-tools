/**
 * Componente DownloadItem - Representa un item de descarga en la lista
 */

export class DownloadItem {
    /**
     * Formatea el tamaño en bytes a formato legible
     * @param {number} bytes - Tamaño en bytes
     * @returns {string} Tamaño formateado
     */
    formatSize(bytes) {
        if (!bytes) return '0 B';
        
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;
        
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        
        return `${size.toFixed(2)} ${units[unitIndex]}`;
    }

    /**
     * Crea el HTML del item de descarga
     * @param {Object} file - Información del archivo
     * @param {string} file.filename - Nombre del archivo
     * @param {number} file.size - Tamaño en bytes
     * @param {string} file.download_url - URL de descarga
     * @returns {string} HTML del item
     */
    createHTML(file) {
        const { filename, size, download_url } = file;
        
        return `
            <div class="download-item">
                <div class="download-item-header">
                    <div class="download-filename" title="${this.escapeHtml(filename)}">
                        ${this.escapeHtml(filename)}
                    </div>
                </div>
                <div class="download-size">${this.formatSize(size)}</div>
                <div class="download-actions">
                    <a 
                        href="${download_url}" 
                        class="btn-download-file"
                        download
                    >
                        ⬇️ Descargar
                    </a>
                </div>
            </div>
        `;
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
}

