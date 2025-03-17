import re
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.core.files.uploadedfile import SimpleUploadedFile
import qrcode
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.urls import reverse
from urllib.parse import urlencode
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.contrib.auth.hashers import make_password
from django.views.decorators.http import require_POST

from django.db.models import Q

#Para sacar totales de eventos.
from django.db.models import Sum
from django.shortcuts import render
import locale



from django.db.models import F
from collections import defaultdict

from django.utils import timezone
from datetime import timedelta

# Para tomar el from desde el settings
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
import threading

# Para que muestre más detalles de un error
import traceback

# Importamos todos los modelos de la base de datos
from django.db import IntegrityError, transaction
from django.http import JsonResponse
import json

from django.utils import timezone

#APIVIEW
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny


#PARA EL PDF
from xhtml2pdf import pisa
from django.template.loader import render_to_string
import os
import tempfile
from django.core.files import File

from django.urls import reverse


from rest_framework import viewsets

from .serializers import *
from rest_framework import viewsets


#Importar el crypt
from .crypt import *

#Importar todos los modelos de la base de datos.
from .models import *

#Validar la fecha de Nacimiento
from datetime import datetime
import uuid
from io import BytesIO

# Para restringir las vistas
from .decorators import rol_requerido

# Create your views here.

#inicio
def index(request):
    muebles = Mueble.objects.all()  # Obtén todos los muebles disponibles
    return render(request, 'muebles/index.html', {'muebles': muebles})


#muebles
def muebles_list(request):
    muebles = Mueble.objects.all()
    return render(request, 'muebles/mueble/muebles_list.html', {'muebles': muebles})

@rol_requerido(['1', '2', '3'])
def rentar_mueble(request, mueble_id):
    mueble = get_object_or_404(Mueble, id=mueble_id)
    if request.method == 'POST':
        form = RentaForm(request.POST)
        print("Formulario recibido:", form.data)  # Depuración: Ver datos del formulario
        if form.is_valid():
            print("Formulario válido")  # Depuración: Verificar si el formulario es válido
            renta = form.save(commit=False)
            renta.mueble = mueble  # Asignar el mueble automáticamente
            renta.usuario = request.user  # Asignar el usuario automáticamente
            renta.save()
            print("Renta guardada correctamente")  # Depuración: Verificar si se guarda la renta
            messages.success(request, "La renta ha sido registrada exitosamente.")  # Mensaje de éxito
            return redirect('index')  # Redirige al índice
        else:
            print("Formulario no válido. Errores:", form.errors)  # Depuración: Ver errores del formulario
    else:
        form = RentaForm(initial={'mueble': mueble})

    return render(request, 'muebles/mueble/rentar_mueble.html', {'form': form, 'mueble': mueble})

#contacto
def contacto(request):
    return render(request, 'muebles/contacto/contacto.html')


#usuario
@login_required
def perfil(request):
    logueo = request.session.get("logueo", False)
    if not logueo:
        return redirect('login')

    user = Usuario.objects.get(id=logueo["id"])

    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        direccion = request.POST.get('direccion')
        foto = request.FILES.get('foto')

        # Validar si el correo ya está registrado (excluyendo el usuario actual)
        if Usuario.objects.filter(email=email).exclude(id=user.id).exists():
            messages.warning(request, "El correo ya está registrado.")
            return redirect('perfil')

        user.nombre = nombre
        user.email = email
        user.direccion = direccion

        if foto:
            user.foto = foto

        user.save()

        # Actualizar la sesión con los nuevos datos del usuario
        request.session["logueo"] = {
            "id": user.id,
            "nombre": user.nombre,
            "rol": user.rol,
            "nombre_rol": user.get_rol_display(),
            "foto": user.foto.url if user.foto else None
        }

        messages.success(request, "Perfil actualizado exitosamente.")
        return redirect('perfil')

    return render(request, 'muebles/perfil/perfil.html', {'user': user})

def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            # Buscar el usuario por su correo electrónico
            user = Usuario.objects.get(email=email)

            # Verificar la contraseña
            if verify_password(password, user.password):
                # Almacenar información del usuario en la sesión
                request.session["logueo"] = {
                    "id": user.id,
                    "nombre": user.nombre,
                    "rol": user.rol,
                    "nombre_rol": user.get_rol_display(),
                    "foto": user.foto.url if user.foto else None
                }
                messages.success(request, "Has iniciado sesión exitosamente.")
                return redirect("index")
            else:
                messages.warning(request, "Contraseña incorrecta.")
        except Usuario.DoesNotExist:
            messages.warning(request, "El correo electrónico no está registrado.")

    return render(request, 'muebles/perfil/login.html')

def registro(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        direccion = request.POST.get('direccion')
        password = request.POST.get('password')

        # Validación de nombre: solo letras y espacios
        if not re.match("^[A-Za-z\\s]+$", nombre):
            messages.warning(request, "El nombre solo puede contener letras y espacios.")
            return redirect("registro")

        # Validación de correo electrónico
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messages.warning(request, "Por favor, ingrese un correo electrónico válido.")
            return redirect("registro")

        # Validar si el correo ya existe
        if Usuario.objects.filter(email=email).exists():
            messages.warning(request, "El correo electrónico ya está registrado.")
            return redirect("registro")

        # Crear el usuario con contraseña encriptada
        Usuario.objects.create(
            nombre=nombre,
            email=email,
            username=email,  # Usar el email como nombre de usuario
            direccion=direccion,
            password=make_password(password)  # Encriptar la contraseña
        )

        messages.success(request, "Usuario creado exitosamente. Por favor, inicia sesión.")
        return redirect("login")

    return render(request, 'muebles/perfil/registrarse.html')

def logout(request):
    if "logueo" in request.session:
        del request.session["logueo"]
        messages.success(request, "Sesión cerrada correctamente.")
    else:
        messages.warning(request, "No hay sesión activa.")
    return redirect("index")

