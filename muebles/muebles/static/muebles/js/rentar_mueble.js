document.getElementById('fecha_inicio').addEventListener('change', function() {
    calcularDuracion();
});

document.getElementById('fecha_fin').addEventListener('change', function() {
    calcularDuracion();
});

function calcularDuracion() {
    const fechaInicio = document.getElementById('fecha_inicio').value;
    const fechaFin = document.getElementById('fecha_fin').value;

    if (fechaInicio && fechaFin) {
        const fechaInicioObj = new Date(fechaInicio);
        const fechaFinObj = new Date(fechaFin);

        // Calcular la diferencia en milisegundos
        const diferenciaMs = fechaFinObj - fechaInicioObj;

        // Convertir la diferencia a días
        const duracionDias = Math.floor(diferenciaMs / (1000 * 60 * 60 * 24));

        // Calcular la duración en meses
        let duracionMeses = (fechaFinObj.getFullYear() - fechaInicioObj.getFullYear()) * 12;
        duracionMeses -= fechaInicioObj.getMonth();
        duracionMeses += fechaFinObj.getMonth();

        // Mostrar los valores en los campos correspondientes
        console.log("Duración en días:", duracionDias); // Depuración
        console.log("Duración en meses:", duracionMeses); // Depuración

        document.getElementById('duracion_dias').value = duracionDias;
        document.getElementById('duracion_meses').value = duracionMeses;
    }
}