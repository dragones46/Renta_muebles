
# 🏠 Renta Mueble

**Renta Mueble** es una aplicación web desarrollada con **Python Django** que permite la gestión y renta de muebles de forma fácil, rápida y eficiente. Está pensada para que propietarios individuales o empresas puedan publicar sus muebles ò inmuebles, y usuarios interesados puedan rentarlos por días con o sin descuentos según fechas establecidas.

## 🚀 Funcionalidades principales

- Registro y autenticación de usuarios.
- Publicación y visualización de muebles.
- Renta diaria de muebles.
- Aplicación de descuentos con fechas de inicio y fin.
- Visualización de imágenes.
- Soporte para multimedia (videos tutoriales del usuario).
- Gestión de propietarios individuales y empresas.

## 🛠️ Tecnologías utilizadas

- **Python 3.9+**
- **Django 4.x+**
- **MySQL Server** (base de datos relacional)
- **JavaScript** (para interactividad frontend)
- **HTML/CSS**
- **Node.js** (solo requerido para desarrolladores que modifiquen JS)
- **Archivos multimedia**: mp3 / mp4
- **Git** (opcional, para clonar o colaborar)

## 📁 Estructura principal del modelo Mueble

```python
class Mueble(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio_diario = models.IntegerField(default=0)
    imagen = models.ImageField(upload_to='muebles/')
    propietario = models.ForeignKey(Propietario, on_delete=models.CASCADE)
    descuento = models.IntegerField(default=0)
    fecha_inicio_descuento = models.DateField(null=True, blank=True)
    fecha_fin_descuento = models.DateField(null=True, blank=True)
```

## ⚙️ Requisitos

- Python 3.9 o superior  
- Django 4.x o superior  
- MySQL Server y cliente  
- Node.js (solo para entender/modificar el código JS)  
- Git (opcional)  
- Entorno virtual para Python  
- Servidor compatible con archivos multimedia (mp3/mp4)

## 📦 Instalación paso a paso

### 1. Clonar el repositorio

```bash
git clone https://github.com/dragones46/Renta_muebles.git

Cuando termine de clonar pueden abrir el archivo en la misma ventana y despues de eso usan el siguiente codigo

cd muebles
```

### 2. Crear entorno virtual

#### Windows

```bash
python -m venv env
env\Scripts\activate
```

#### macOS / Linux

```bash
python3 -m venv env
source env/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```



### 4. Aplicar migraciones (ESTO ES SI HAY ALGO PENDIENTE QUE MIGRAR)

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Crear superusuario

```bash
python manage.py createsuperuser
```

### 6. Ejecutar el servidor

```bash
python manage.py runserver
```

## 🎥 Manual del usuario

El sistema incluye videos tutoriales en formato mp3/mp4 que puedes ver desde el panel de ayuda o en la carpeta `static/muebles/videos`.

## 🚀 Despliegue en producción (opcional)

- Usar Gunicorn + Nginx como servidor de aplicaciones
- Configurar `DEBUG = False` y `ALLOWED_HOSTS` en `settings.py`
- Usar certificado SSL (Let's Encrypt)
- Alojamiento recomendado: Render, DigitalOcean, AWS o Heroku

## 📚 Enlaces útiles para instalación de herramientas

- [Python](https://www.python.org/downloads/)
- [Django](https://www.djangoproject.com/start/)
- [MySQL](https://dev.mysql.com/downloads/)
- [Node.js](https://nodejs.org/)
- [Git](https://git-scm.com/downloads)
- [Servidor multimedia (Nginx)](https://www.nginx.com/)

## 👨‍💻 Autoría

Desarrollado por el equipo de **Renta Mueble**. Si deseas colaborar o reportar errores, crea un github personal con este archivo y arregla lo errores que hayan.

---

¡Gracias por usar **Renta Mueble**!
