function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Apply formatting when the document is ready
document.addEventListener("DOMContentLoaded", function () {
    const precioElementos = document.querySelectorAll('.precio-normal, .precio-original, .precio-descuento');

    precioElementos.forEach(element => {
        let precio = parseFloat(element.textContent.replace(/[^0-9.-]+/g, ""));
        if (!isNaN(precio)) {
            element.textContent = `$${formatNumber(precio)}/día`;
        }
    });
});
