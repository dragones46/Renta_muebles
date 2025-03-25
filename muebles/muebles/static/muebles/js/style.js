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
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar el cierre automático
    setupAutoDismissAlerts();
    
    // También manejar el cierre manual
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('btn-close')) {
            const alert = e.target.closest('.alert');
            const bsAlert = bootstrap.Alert.getInstance(alert) || new bootstrap.Alert(alert);
            bsAlert.close();
        }
    });
});