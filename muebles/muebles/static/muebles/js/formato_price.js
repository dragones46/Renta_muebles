document.addEventListener('DOMContentLoaded', function() {
    // Función para formatear números con separadores de miles
    function formatNumber(value) {
        return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }

    // Selecciona todos los elementos con la clase 'price'
    var prices = document.querySelectorAll('.price');

    // Itera sobre cada elemento de precio
    prices.forEach(function(priceElement) {
        // Obtiene el texto del precio
        var priceText = priceElement.textContent;

        // Elimina el símbolo de dólar y cualquier espacio en blanco
        var priceValue = priceText.replace('$', '').trim();

        // Formatea el precio con separadores de miles
        var formattedPrice = formatNumber(priceValue);

        // Actualiza el contenido del elemento de precio
        priceElement.textContent = '$' + formattedPrice;
    });

    // Selecciona todos los elementos con la clase 'kg'
    var kgs = document.querySelectorAll('.kg');

    // Itera sobre cada elemento de kg
    kgs.forEach(function(kgElement) {
        // Obtiene el texto del kg
        var kgText = kgElement.textContent;

        // Elimina el símbolo de kg y cualquier espacio en blanco
        var kgValue = kgText.replace('kg', '').trim();

        // Formatea el kg con separadores de miles
        var formattedKg = formatNumber(kgValue);

        // Actualiza el contenido del elemento de kg
        kgElement.textContent = formattedKg + 'kg';
    });
});
