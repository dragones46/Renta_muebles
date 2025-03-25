document.addEventListener('DOMContentLoaded', function() {
    function formatNumber(number) {
        return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    }

    // Función para formatear elementos que contienen precios
    function formatPriceElements(elements) {
        elements.forEach(element => {
            const text = element.textContent;
            // Busca números con formato $10000 o $ 10000
            const numberMatch = text.match(/\$\s*(\d+)/);
            if (numberMatch) {
                const number = parseInt(numberMatch[1]);
                element.textContent = text.replace(numberMatch[1], formatNumber(number));
            }
        });
    }

    // Formatear todos los números con clases específicas
    document.querySelectorAll('.price-number, .subtotal-number, .total-number, .delivery-number, .final-total').forEach(element => {
        const number = parseInt(element.textContent.replace(/[^\d]/g, ''));
        if (!isNaN(number)) {
            element.textContent = formatNumber(number);
        }
    });

    // Formatear precios en el carrito
    formatPriceElements(document.querySelectorAll('.carrito-item .info p:nth-child(3), .carrito-item .subtotal, .carrito-total h3'));

    // Formatear precios en la lista de muebles
    formatPriceElements(document.querySelectorAll('.card-text:nth-child(3)'));
});