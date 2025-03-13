document.addEventListener('DOMContentLoaded', function () {
    const form = document.querySelector('form');
    const nombreInput = document.getElementById('nombre');
    const nombreFeedback = nombreInput.nextElementSibling;

    form.addEventListener('submit', function (event) {
        let isValid = true;

        // Validación del nombre
        const nombreValue = nombreInput.value.trim();
        const nombreRegex = /^[A-Za-z\s]+$/;
        if (!nombreRegex.test(nombreValue)) {
            nombreInput.classList.add('is-invalid');
            nombreFeedback.textContent = 'El nombre solo puede contener letras y espacios. No se aceptan caracteres especiales.';
            nombreFeedback.style.display = 'block';
            isValid = false;
        } else {
            nombreInput.classList.remove('is-invalid');
            nombreFeedback.style.display = 'none';
        }

        if (!isValid) {
            event.preventDefault();
        }
    });
});




