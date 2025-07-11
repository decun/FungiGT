/**
 * Gestor de temas para FungiGT
 * Maneja el cambio entre modo claro y oscuro con persistencia en el usuario
 */

class ThemeManager {
    constructor() {
        this.currentTheme = 'light';
        this.init();
    }

    /**
     * Inicializa el gestor de temas
     */
    async init() {
        // Cargar tema desde localStorage como fallback
        const savedTheme = localStorage.getItem('fungigt-theme');
        if (savedTheme) {
            this.currentTheme = savedTheme;
        }

        // Intentar cargar preferencias del usuario si está autenticado
        await this.loadUserPreferences();
        
        // Aplicar tema inicial
        this.applyTheme(this.currentTheme);
        
        // Configurar listeners
        this.setupEventListeners();
    }

    /**
     * Carga las preferencias del usuario desde el backend
     */
    async loadUserPreferences() {
        try {
            const token = this.getAuthToken();
            if (!token) return;

            const response = await fetch('/api/auth/preferences', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.preferences && data.preferences.theme) {
                    this.currentTheme = data.preferences.theme;
                }
            }
        } catch (error) {
            console.warn('No se pudieron cargar las preferencias del usuario:', error);
        }
    }

    /**
     * Guarda las preferencias del usuario en el backend
     */
    async saveUserPreferences(theme) {
        try {
            const token = this.getAuthToken();
            if (!token) return;

            const response = await fetch('/api/auth/preferences', {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ theme })
            });

            if (!response.ok) {
                console.warn('Error al guardar preferencias en el servidor');
            }
        } catch (error) {
            console.warn('Error al guardar preferencias:', error);
        }
    }

    /**
     * Obtiene el token de autenticación
     */
    getAuthToken() {
        const cookies = document.cookie.split(';').reduce((acc, cookie) => {
            const [name, value] = cookie.trim().split('=');
            acc[name] = value;
            return acc;
        }, {});
        return cookies.token;
    }

    /**
     * Aplica el tema especificado
     */
    applyTheme(theme) {
        this.currentTheme = theme;
        
        // Aplicar atributo data-theme al documento
        document.documentElement.setAttribute('data-theme', theme);
        
        // Guardar en localStorage como fallback
        localStorage.setItem('fungigt-theme', theme);
        
        // Actualizar estado de los toggles
        this.updateToggleStates();
        
        // Emitir evento personalizado
        window.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme: theme }
        }));
    }

    /**
     * Cambia entre los temas disponibles
     */
    async toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme);
        
        // Guardar en el backend
        await this.saveUserPreferences(newTheme);
        
        // Mostrar feedback al usuario
        this.showThemeChangeNotification(newTheme);
    }

    /**
     * Actualiza el estado visual de los toggles
     */
    updateToggleStates() {
        const toggles = document.querySelectorAll('.theme-toggle');
        toggles.forEach(toggle => {
            const isDark = this.currentTheme === 'dark';
            toggle.classList.toggle('active', isDark);
            toggle.setAttribute('aria-pressed', isDark);
        });
    }

    /**
     * Configura los event listeners
     */
    setupEventListeners() {
        // Listener para toggles de tema
        document.addEventListener('click', (e) => {
            if (e.target.matches('.theme-toggle') || e.target.closest('.theme-toggle')) {
                this.toggleTheme();
            }
        });

        // Listener para cambios en localStorage (múltiples pestañas)
        window.addEventListener('storage', (e) => {
            if (e.key === 'fungigt-theme') {
                this.applyTheme(e.newValue);
            }
        });

        // Listener para preferencias del sistema
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addListener(() => {
                // Solo aplicar preferencia del sistema si no hay preferencia guardada
                if (!localStorage.getItem('fungigt-theme')) {
                    this.applyTheme(mediaQuery.matches ? 'dark' : 'light');
                }
            });
        }
    }

    /**
     * Muestra una notificación del cambio de tema
     */
    showThemeChangeNotification(theme) {
        const message = theme === 'dark' ? 'Modo oscuro activado' : 'Modo claro activado';
        
        // Crear notificación temporal
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 theme-bg-secondary theme-text-primary px-4 py-2 rounded-lg shadow-lg z-50 transition-all duration-300';
        notification.innerHTML = `
            <div class="flex items-center space-x-2">
                <i class="fas fa-${theme === 'dark' ? 'moon' : 'sun'}"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Remover después de 3 segundos
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }

    /**
     * Crea un toggle de tema
     */
    createThemeToggle() {
        const toggle = document.createElement('div');
        toggle.className = 'theme-toggle flex items-center justify-center';
        toggle.setAttribute('role', 'button');
        toggle.setAttribute('aria-label', 'Cambiar tema');
        toggle.setAttribute('tabindex', '0');
        toggle.innerHTML = `
            <i class="fas fa-sun theme-icon sun"></i>
            <i class="fas fa-moon theme-icon moon"></i>
        `;
        
        // Agregar soporte para teclado
        toggle.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.toggleTheme();
            }
        });
        
        return toggle;
    }

    /**
     * Obtiene el tema actual
     */
    getCurrentTheme() {
        return this.currentTheme;
    }

    /**
     * Verifica si el modo oscuro está activo
     */
    isDarkMode() {
        return this.currentTheme === 'dark';
    }
}

// Instancia global del gestor de temas
window.themeManager = new ThemeManager();

// Función de utilidad para crear toggles de tema
window.createThemeToggle = () => {
    return window.themeManager.createThemeToggle();
};

// Evento DOMContentLoaded para inicialización
document.addEventListener('DOMContentLoaded', () => {
    // Inicializar el gestor de temas si no está ya inicializado
    if (!window.themeManager) {
        window.themeManager = new ThemeManager();
    }
}); 