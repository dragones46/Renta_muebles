// Tiempos de visualización por tipo de alerta (en milisegundos)
const ALERT_TIMEOUTS = {
    'alert-success': 3000,  // 3 segundos
    'alert-danger': 5000,   // 5 segundos
    'alert-warning': 4000,  // 4 segundos
    'alert-info': 2500      // 2.5 segundos
};

// Función para cerrar automáticamente las alertas
function setupAutoDismissAlerts() {
    // Seleccionar todas las alertas de Bootstrap
    const alerts = document.querySelectorAll('.alert[data-bs-dismiss="alert"]');

    alerts.forEach(alert => {
        // Determinar el tipo de alerta
        let alertType = Object.keys(ALERT_TIMEOUTS).find(
            type => alert.classList.contains(type)
        ) || 'alert-info'; // Valor por defecto

        // Obtener el timeout configurado
        const timeout = ALERT_TIMEOUTS[alertType] || 3000;

        // Cerrar automáticamente después del tiempo especificado
        setTimeout(() => {
            // Usar el método de Bootstrap para cerrar la alerta
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, timeout);
    });
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function () {
    // Inicializar el cierre automático
    setupAutoDismissAlerts();

    // También manejar el cierre manual
    document.addEventListener('click', function (e) {
        if (e.target.classList.contains('btn-close')) {
            const alert = e.target.closest('.alert');
            const bsAlert = bootstrap.Alert.getInstance(alert) || new bootstrap.Alert(alert);
            bsAlert.close();
        }
    });
});


// Configuración
const ALERT_DISMISS_DELAY = 3000; // 3 segundos
const ALERT_FADE_DURATION = 500; // 0.5 segundos para el fade out

// Función para eliminar mensajes después de un tiempo
function autoDismissAlerts() {
    const alerts = document.querySelectorAll('.alert');

    alerts.forEach(alert => {
        // Si ya tiene el atributo data-autodismiss="false", no lo eliminamos
        if (alert.dataset.autodismiss === "false") return;

        setTimeout(() => {
            // Agregar animación de desvanecimiento
            alert.style.transition = `opacity ${ALERT_FADE_DURATION}ms ease-out`;
            alert.style.opacity = '0';

            // Eliminar el mensaje después de que termine la animación
            setTimeout(() => {
                alert.remove();
            }, ALERT_FADE_DURATION);
        }, ALERT_DISMISS_DELAY);
    });
}

// Ejecutar cuando el DOM esté cargado
document.addEventListener('DOMContentLoaded', autoDismissAlerts);


// Funciones para mostrar/ocultar el loading
function showGlobalLoading() {
    document.body.classList.add('loading');
    document.getElementById('globalLoading').classList.add('active');
}

function hideGlobalLoading() {
    document.body.classList.remove('loading');
    document.getElementById('globalLoading').classList.remove('active');
}

// Mostrar loading al hacer clic en enlaces
document.addEventListener('DOMContentLoaded', function() {
    // Mostrar loading en enlaces normales
    document.querySelectorAll('a:not([target="_blank"])').forEach(link => {
        link.addEventListener('click', function(e) {
            if (this.href && this.href !== '#') {
                showGlobalLoading();
            }
        });
    });
    
    // Mostrar loading al enviar formularios
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function() {
            showGlobalLoading();
        });
    });
    
    // Manejar el botón de retroceso del navegador
    window.addEventListener('pageshow', function() {
        hideGlobalLoading();
    });
    
    // Ocultar loading cuando la página termine de cargar
    window.addEventListener('load', function() {
        hideGlobalLoading();
    });
});

// Para peticiones AJAX (si las usas)
$(document).ajaxStart(function() {
    showGlobalLoading();
}).ajaxStop(function() {
    hideGlobalLoading();
});

// Interceptar todas las acciones CRUD
document.querySelectorAll('[data-action="delete"], [data-action="edit"], [data-action="add"]').forEach(btn => {
    btn.addEventListener('click', function() {
        showGlobalLoading();
    });
});