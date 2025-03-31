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
# En la sección de imports al inicio del archivo, agrega:
from django.db.models import F, Sum, ExpressionWrapper, FloatField
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
from .decorators import *

# Create your views here.

#inicio
def index(request):
    muebles = Mueble.objects.all()  # Obtén todos los muebles disponibles
    return render(request, 'muebles/index.html', {'muebles': muebles})


#muebles
def muebles_list(request):
    muebles = Mueble.objects.all()
    return render(request, 'muebles/mueble/muebles_list.html', {'muebles': muebles})

@login_requerido
def rentar_mueble(request, mueble_id):
    mueble = get_object_or_404(Mueble, id=mueble_id)

    if request.method == 'POST':
        form = RentaForm(request.POST)
        if form.is_valid():
            # Guardar la renta
            renta = form.save(commit=False)
            renta.mueble = mueble
            renta.usuario = request.user
            renta.save()

            # Agregar el mueble al carrito
            carrito, creado = Carrito.objects.get_or_create(usuario=request.user)
            item, item_creado = ItemCarrito.objects.get_or_create(carrito=carrito, mueble=mueble)
            if not item_creado:
                item.cantidad += 1
                item.save()

            messages.success(request, f"{mueble.nombre} ha sido agregado al carrito.")
            return redirect('ver_carrito')
    else:
        form = RentaForm(initial={'mueble': mueble})

    return render(request, 'muebles/mueble/rentar_mueble.html', {
        'form': form,
        'mueble': mueble,
    })

#contacto
def contacto(request):
    return render(request, 'muebles/contacto/contacto.html')


#usuario
@login_requerido
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

#carrito
def agregar_al_carrito(request, mueble_id):
    mueble = get_object_or_404(Mueble, id=mueble_id)
    carrito, creado = Carrito.objects.get_or_create(usuario=request.user)

    # Verificar si el mueble ya está en el carrito
    item, item_creado = ItemCarrito.objects.get_or_create(carrito=carrito, mueble=mueble)
    if not item_creado:
        item.cantidad += 1
        item.save()
        messages.success(request, f"Se ha incrementado la cantidad de {mueble.nombre} en el carrito.")
    else:
        messages.success(request, f"{mueble.nombre} ha sido agregado al carrito.")

    return redirect('ver_carrito')

def eliminar_del_carrito(request, item_id):
    carrito = get_object_or_404(Carrito, usuario=request.user)
    item = get_object_or_404(ItemCarrito, id=item_id)
    item.delete()
    
    # Verificar si quedan items en el carrito
    if carrito.items.count() == 0:
        carrito.domicilio = None  # Eliminar el domicilio si no hay items
        carrito.save()
        messages.success(request, "El carrito está vacío y se ha eliminado el domicilio.")
    else:
        messages.success(request, f"{item.mueble.nombre} ha sido eliminado del carrito.")
    
    return redirect('ver_carrito')

@login_requerido
def actualizar_cantidad(request, item_id):
    carrito = get_object_or_404(Carrito, usuario=request.user)
    item = get_object_or_404(ItemCarrito, id=item_id)
    cantidad = int(request.POST.get('cantidad', 1))

    if cantidad > 0:
        item.cantidad = cantidad
        item.save()
        messages.success(request, f"La cantidad de {item.mueble.nombre} ha sido actualizada a {cantidad}.")
    else:
        item.delete()
        # Verificar si quedan items en el carrito
        if carrito.items.count() == 0:
            carrito.domicilio = None  # Eliminar el domicilio si no hay items
            carrito.save()
            messages.success(request, "El carrito está vacío y se ha eliminado el domicilio.")
        else:
            messages.success(request, f"{item.mueble.nombre} ha sido eliminado del carrito.")

    return redirect('ver_carrito')

@login_requerido
def ver_carrito(request):
    usuario = request.user if request.user.is_authenticated else None
    carrito, creado = Carrito.objects.get_or_create(usuario=usuario)
    
    if request.method == 'POST':
        form = DomicilioForm(request.POST)
        if form.is_valid():
            carrito.domicilio = form.cleaned_data['domicilio']
            carrito.save()
            return redirect('ver_carrito')
    else:
        form = DomicilioForm(initial={'domicilio': carrito.domicilio})

    items = carrito.items.all()
    total = carrito.calcular_total()
    costo_domicilio = carrito.COSTO_DOMICILIO if carrito.domicilio else 0

    return render(request, 'muebles/carrito/ver_carrito.html', {
        'items': items,
        'total': total,
        'form': form,
        'carrito': carrito,
        'costo_domicilio': costo_domicilio,
    })

#domicilio
@login_requerido
def eliminar_domicilio(request):
    carrito = get_object_or_404(Carrito, usuario=request.user)
    carrito.domicilio = None
    carrito.save()
    messages.success(request, "Domicilio eliminado correctamente.")
    return redirect('ver_carrito')

#pago
@login_requerido
def procesar_pago(request):
    carrito = request.user.carrito
    
    if not carrito.items.exists():
        messages.error(request, "Tu carrito está vacío")
        return redirect('carrito')
    
    # Crear el pedido
    pedido = Pedido.objects.create(
        usuario=request.user,
        total=carrito.calcular_total(),
        direccion_entrega=carrito.domicilio or request.user.direccion,
        estado='completado'
    )
    
    # Crear los detalles del pedido
    for item in carrito.items.all():
        DetallePedido.objects.create(
            pedido=pedido,
            mueble=item.mueble,
            cantidad=item.cantidad,
            precio_unitario=item.mueble.precio_diario,
            subtotal=item.subtotal()
        )
    
    # Limpiar el carrito
    carrito.items.all().delete()
    carrito.domicilio = None
    carrito.save()
    
    messages.success(request, "¡Pago exitoso! Tu pedido ha sido procesado.")
    return redirect('index')

#admin
@login_requerido(roles_permitidos=[1])
def admin_inicio(request):
    if not request.session.get('logueo') or request.session.get('logueo').get('rol') != 1:
        return redirect('login')
    
    # Estadísticas para el dashboard
    total_muebles = Mueble.objects.count()
    total_usuarios = Usuario.objects.count()
    total_pedidos = Pedido.objects.count()
    
    context = {
        'total_muebles': total_muebles,
        'total_usuarios': total_usuarios,
        'total_pedidos': total_pedidos,
    }
    return render(request, 'muebles/admin/inicio.html', context)


#crud muebles
# views.py

def admin_muebles(request):
    if not request.session.get('logueo') or request.session.get('logueo').get('rol') != 1:
        messages.error(request, 'Acceso denegado. Debes ser administrador.')
        return redirect('login')
    
    muebles = Mueble.objects.all()
    propietarios = Propietario.objects.all()
    return render(request, 'muebles/admin/muebles.html', {
        'muebles': muebles,
        'propietarios': propietarios
    })

def crear_mueble(request):
    if not request.session.get('logueo') or request.session.get('logueo').get('rol') != 1:
        messages.error(request, 'Acceso denegado. Debes ser administrador.')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            descripcion = request.POST.get('descripcion')
            precio_diario = request.POST.get('precio_diario')
            propietario_id = request.POST.get('propietario')
            imagen = request.FILES.get('imagen')
            
            if not all([nombre, precio_diario, propietario_id]):
                messages.error(request, 'Todos los campos obligatorios deben ser completados.')
                return redirect('admin_muebles')
            
            propietario = Propietario.objects.get(id=propietario_id)
            mueble = Mueble(
                nombre=nombre,
                descripcion=descripcion,
                precio_diario=precio_diario,
                propietario=propietario,
                imagen=imagen
            )
            mueble.save()
            messages.success(request, f'Mueble "{nombre}" creado exitosamente!')
            return redirect('admin_muebles')
            
        except Exception as e:
            messages.error(request, f'Error al crear el mueble: {str(e)}')
            return redirect('admin_muebles')
    
    return redirect('admin_muebles')

def editar_mueble(request, id):
    if not request.session.get('logueo') or request.session.get('logueo').get('rol') != 1:
        messages.error(request, 'Acceso denegado. Debes ser administrador.')
        return redirect('login')
    
    try:
        mueble = Mueble.objects.get(id=id)
        
        if request.method == 'POST':
            nombre = request.POST.get('nombre')
            descripcion = request.POST.get('descripcion')
            precio_diario = request.POST.get('precio_diario')
            propietario_id = request.POST.get('propietario')
            
            if not all([nombre, precio_diario, propietario_id]):
                messages.error(request, 'Todos los campos obligatorios deben ser completados.')
                return redirect('admin_muebles')
            
            mueble.nombre = nombre
            mueble.descripcion = descripcion
            mueble.precio_diario = precio_diario
            mueble.propietario = Propietario.objects.get(id=propietario_id)
            
            if 'imagen' in request.FILES:
                mueble.imagen = request.FILES['imagen']
            
            mueble.save()
            messages.success(request, f'Mueble "{nombre}" actualizado exitosamente!')
            return redirect('admin_muebles')
            
    except Mueble.DoesNotExist:
        messages.error(request, 'El mueble que intentas editar no existe.')
    except Exception as e:
        messages.error(request, f'Error al actualizar el mueble: {str(e)}')
    
    return redirect('admin_muebles')

def eliminar_mueble(request, id):
    if not request.session.get('logueo') or request.session.get('logueo').get('rol') != 1:
        messages.error(request, 'Acceso denegado. Debes ser administrador.')
        return redirect('login')
    
    try:
        mueble = Mueble.objects.get(id=id)
        nombre = mueble.nombre
        mueble.delete()
        messages.success(request, f'Mueble "{nombre}" eliminado exitosamente!')
    except Mueble.DoesNotExist:
        messages.error(request, 'El mueble que intentas eliminar no existe.')
    except Exception as e:
        messages.error(request, f'Error al eliminar el mueble: {str(e)}')
    
    return redirect('admin_muebles')

#crud usuarios
# Vista para listar usuarios
# views.py

def admin_usuarios(request):
    if not request.session.get('logueo') or request.session.get('logueo').get('rol') != 1:
        messages.error(request, 'Acceso denegado. Debes ser administrador.')
        return redirect('login')
    
    usuarios = Usuario.objects.all().order_by('-id')
    return render(request, 'muebles/admin/usuarios.html', {
        'usuarios': usuarios,
        'roles': Usuario.ROLES,
        'estados': Usuario.ESTADO
    })

def crear_usuario(request):
    if not request.session.get('logueo') or request.session.get('logueo').get('rol') != 1:
        messages.error(request, 'Acceso denegado. Debes ser administrador.')
        return redirect('login')
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                usuario = form.save(commit=False)
                usuario.set_password(form.cleaned_data['password'])
                usuario.save()
                messages.success(request, 'Usuario creado exitosamente!')
                return redirect('admin_usuarios')
            except Exception as e:
                messages.error(request, f'Error al crear el usuario: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    else:
        form = UsuarioForm()
    
    return render(request, 'muebles/admin/crear_usuario.html', {
        'form': form,
        'roles': Usuario.ROLES,
        'estados': Usuario.ESTADO
    })

def editar_usuario(request, id):
    if not request.session.get('logueo') or request.session.get('logueo').get('rol') != 1:
        messages.error(request, 'Acceso denegado. Debes ser administrador.')
        return redirect('login')
    
    try:
        usuario = Usuario.objects.get(id=id)
        
        if request.method == 'POST':
            form = UsuarioForm(request.POST, request.FILES, instance=usuario)
            if form.is_valid():
                try:
                    # Solo actualiza la contraseña si se proporcionó una nueva
                    if form.cleaned_data['password']:
                        usuario.set_password(form.cleaned_data['password'])
                    form.save()
                    messages.success(request, 'Usuario actualizado exitosamente!')
                    return redirect('admin_usuarios')
                except Exception as e:
                    messages.error(request, f'Error al actualizar el usuario: {str(e)}')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
        else:
            form = UsuarioForm(instance=usuario)
        
        return render(request, 'muebles/admin/editar_usuario.html', {
            'form': form,
            'usuario': usuario,
            'roles': Usuario.ROLES,
            'estados': Usuario.ESTADO
        })
        
    except Usuario.DoesNotExist:
        messages.error(request, 'El usuario que intentas editar no existe.')
        return redirect('admin_usuarios')

def eliminar_usuario(request, id):
    if not request.session.get('logueo') or request.session.get('logueo').get('rol') != 1:
        messages.error(request, 'Acceso denegado. Debes ser administrador.')
        return redirect('login')
    
    try:
        usuario = Usuario.objects.get(id=id)
        
        # No permitir eliminar el propio usuario admin
        if usuario.id == request.session.get('logueo').get('id'):
            messages.error(request, 'No puedes eliminar tu propio usuario.')
            return redirect('admin_usuarios')
        
        nombre = usuario.nombre
        usuario.delete()
        messages.success(request, f'Usuario "{nombre}" eliminado exitosamente!')
        
    except Usuario.DoesNotExist:
        messages.error(request, 'El usuario que intentas eliminar no existe.')
    except Exception as e:
        messages.error(request, f'Error al eliminar el usuario: {str(e)}')
    
    return redirect('admin_usuarios')


#pedidos
# Vista para listar pedidos
def admin_pedidos(request):
    if not request.session.get('logueo') or request.session.get('logueo').get('rol') != 1:
        return redirect('login')
    
    pedidos = Pedido.objects.all().order_by('-fecha')
    return render(request, 'muebles/admin/pedidos/pedidos.html', {'pedidos': pedidos})

# Vista para ver detalle de pedido
def detalle_pedido(request, id):
    if not request.session.get('logueo') or request.session.get('logueo').get('rol') != 1:
        return redirect('login')
    
    pedido = get_object_or_404(Pedido, id=id)
    detalles = DetallePedido.objects.filter(pedido=pedido)
    
    return render(request, 'muebles/admin/pedidos/detalles_pedidos.html', {
        'pedido': pedido,
        'detalles': detalles
    })

# vistas para ayuda
def ayuda_principal(request):
    return render(request, 'muebles/ayuda/ayuda_principal.html')

def faq(request):
    # Obtener el total de votos para calcular porcentajes
    total_votos = FAQ.objects.aggregate(total=Sum('votos'))['total'] or 1
    
    categorias = FAQ.objects.values_list('categoria', flat=True).distinct()
    faqs = {}
    
    for categoria in categorias:
        faqs_por_categoria = FAQ.objects.filter(categoria=categoria).annotate(
            porcentaje=ExpressionWrapper(
                F('votos') * 100 / total_votos,
                output_field=FloatField()
            )
        ).order_by('-votos')
        faqs[categoria] = faqs_por_categoria
    
    return render(request, 'muebles/ayuda/faq.html', {
        'faqs': faqs,
        'total_votos': total_votos
    })

def soporte(request):
    if request.method == 'POST':
        form = SoporteForm(request.POST)
        if form.is_valid():
            # Procesar el formulario
            nombre = form.cleaned_data['nombre']
            email = form.cleaned_data['email']
            mensaje = form.cleaned_data['mensaje']
            
            # Enviar correo
            send_mail(
                f'Solicitud de soporte de {nombre}',
                mensaje,
                email,
                [settings.EMAIL_SOPORTE],
                fail_silently=False,
            )
            messages.success(request, 'Tu solicitud de soporte ha sido enviada. Nos pondremos en contacto contigo pronto.')
            return redirect('soporte')
    else:
        form = SoporteForm()
    
    return render(request, 'muebles/ayuda/soporte.html', {'form': form})

def actualizaciones(request):
    actualizaciones = Actualizacion.objects.all().order_by('-fecha')
    return render(request, 'muebles/ayuda/actualizaciones.html', {'actualizaciones': actualizaciones})

def politica_cookies(request):
    return render(request, 'muebles/legal/Cookies.html')

def configurar_cookies(request):
    if request.method == 'POST':
        # Guardar las preferencias del usuario
        request.session['cookie_preferences'] = {
            'esenciales': 'esenciales' in request.POST,
            'analiticas': 'analiticas' in request.POST,
            'marketing': 'marketing' in request.POST
        }
        messages.success(request, "Tus preferencias de cookies han sido guardadas.")
        return redirect('index')
    
    # Obtener las preferencias actuales si existen
    preferencias = request.session.get('cookie_preferences', {
        'esenciales': True,
        'analiticas': False,
        'marketing': False
    })
    
    return render(request, 'muebles/legal/configurar_cookies.html', {'preferencias': preferencias})

# PREGUNTAS
@login_requerido
def hacer_pregunta(request):
    if request.method == 'POST':
        form = PreguntaForm(request.POST)
        if form.is_valid():
            pregunta = form.save(commit=False)
            pregunta.usuario = request.user
            pregunta.save()
            messages.success(request, 'Tu pregunta ha sido enviada. Te notificaremos cuando tengamos una respuesta.')
            return redirect('lista_preguntas')  # Cambiado de 'preguntas' a 'lista_preguntas'
    else:
        form = PreguntaForm()
    
    return render(request, 'muebles/preguntas/preguntas.html', {'form': form})



@login_requerido
def responder_pregunta(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    
    if not request.user.is_staff:
        messages.error(request, 'No tienes permiso para responder preguntas.')
        return redirect('preguntas')
    
    if request.method == 'POST':
        form = RespuestaForm(request.POST)
        if form.is_valid():
            respuesta = form.save(commit=False)
            respuesta.pregunta = pregunta
            respuesta.administrador = request.user
            respuesta.save()
            
            # Actualizar estado de la pregunta
            pregunta.estado = 'respondida'
            if form.cleaned_data['es_faq']:
                pregunta.estado = 'publicada'
                pregunta.votos += 5  # Peso extra por ser marcada como FAQ
            pregunta.save()
            
            messages.success(request, 'Respuesta enviada correctamente.')
            return redirect('lista_preguntas')
    else:
        form = RespuestaForm()
    
    return render(request, 'muebles/preguntas/responder_pregunta.html', {
        'pregunta': pregunta,
        'form': form
    })

@login_requerido
def lista_preguntas(request):
    preguntas = Pregunta.objects.filter(usuario=request.user).order_by('-fecha')
    return render(request, 'muebles/preguntas/lista_preguntas.html', {'preguntas': preguntas})

def preguntas_frecuentes(request):
    preguntas = Pregunta.objects.filter(estado='publicada').order_by('-votos')
    return render(request, 'muebles/preguntas/preguntas_frecuentes.html', {'preguntas': preguntas})

@login_requerido
def votar_pregunta(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    pregunta.votos += 1
    pregunta.save()
    
    # Si alcanza cierto umbral, marcarla como frecuente
    if pregunta.votos >= 10 and pregunta.estado != 'publicada':
        pregunta.estado = 'publicada'
        pregunta.save()
    
    messages.success(request, 'Gracias por tu voto. Esto nos ayuda a mejorar las FAQs.')
    return redirect('preguntas_frecuentes')

@login_requerido(roles_permitidos=[1])  # Solo administradores
def admin_preguntas(request):
    if not request.session.get('logueo') or request.session.get('logueo').get('rol') != 1:
        return redirect('login')
    
    preguntas_pendientes = Pregunta.objects.filter(estado='pendiente').order_by('-fecha')
    preguntas_respondidas = Pregunta.objects.filter(estado='respondida').order_by('-fecha')
    preguntas_publicadas = Pregunta.objects.filter(estado='publicada').order_by('-votos')
    
    return render(request, 'muebles/admin/preguntas/admin_preguntas.html', {
        'preguntas_pendientes': preguntas_pendientes,
        'preguntas_respondidas': preguntas_respondidas,
        'preguntas_publicadas': preguntas_publicadas
    })

@login_requerido(roles_permitidos=[1])
def marcar_como_faq(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    pregunta.estado = 'publicada'
    pregunta.votos += 5  # Dar un boost inicial
    pregunta.save()
    messages.success(request, 'La pregunta ha sido publicada en las FAQs')
    return redirect('admin_preguntas')

@require_POST
@login_requerido
def votar_faq(request, faq_id):
    faq = get_object_or_404(FAQ, id=faq_id)
    faq.votos += 1
    faq.save()
    return JsonResponse({'votos': faq.votos})