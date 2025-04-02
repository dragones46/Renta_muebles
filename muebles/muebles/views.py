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
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.db.models import F, Sum, ExpressionWrapper, FloatField
from django.shortcuts import render
import locale
from django.db.models import F
from collections import defaultdict
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
import threading
import traceback
from django.db import IntegrityError, transaction
from django.http import JsonResponse
import json
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from xhtml2pdf import pisa
from django.template.loader import render_to_string
import os
import tempfile
from django.core.files import File
from django.urls import reverse
from rest_framework import viewsets
from .serializers import *
from rest_framework import viewsets
from .crypt import *
from .models import *
from .forms import *
from datetime import datetime
import uuid
from io import BytesIO
from .decorators import *

# ==================== VISTAS PÚBLICAS ====================

def index(request):
    muebles = Mueble.objects.all()
    return render(request, 'muebles/index.html', {'muebles': muebles})

def muebles_list(request):
    muebles = Mueble.objects.all()
    return render(request, 'muebles/mueble/muebles_list.html', {'muebles': muebles})

# ==================== RENTA DE MUEBLES ====================

@login_requerido
def rentar_mueble(request, mueble_id):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    mueble = get_object_or_404(Mueble, id=mueble_id)

    if request.method == 'POST':
        form = RentaForm(request.POST)
        if form.is_valid():
            try:
                # Guardar la renta
                renta = form.save(commit=False)
                renta.mueble = mueble
                renta.usuario = usuario
                renta.save()

                # Agregar el mueble al carrito
                carrito, creado = Carrito.objects.get_or_create(usuario=usuario)
                item, item_creado = ItemCarrito.objects.get_or_create(
                    carrito=carrito, 
                    mueble=mueble
                )
                
                if not item_creado:
                    item.cantidad += 1
                    item.save()

                # Actualizar la sesión
                if "logueo" in request.session:
                    request.session["logueo"]["carrito"]["items_count"] = carrito.items.count()
                    request.session.modified = True

                messages.success(request, f"{mueble.nombre} ha sido agregado al carrito.")
                return redirect('ver_carrito')
                
            except Exception as e:
                messages.error(request, f"Error al procesar la renta: {str(e)}")
                return redirect('rentar_mueble', mueble_id=mueble_id)
    else:
        form = RentaForm(initial={'mueble': mueble})

    return render(request, 'muebles/mueble/rentar_mueble.html', {
        'form': form,
        'mueble': mueble,
    })

def contacto(request):
    return render(request, 'muebles/contacto/contacto.html')

# ==================== AUTENTICACIÓN ====================

def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user = Usuario.objects.get(email=email)
            
            if verify_password(password, user.password):
                # Obtener el carrito del usuario
                carrito, created = Carrito.objects.get_or_create(usuario=user)
                
                request.session["logueo"] = {
                    "id": user.id,
                    "nombre": user.nombre,
                    "email": user.email,
                    "rol": user.rol,
                    "nombre_rol": user.get_rol_display(),
                    "foto": user.foto.url if user.foto else None,
                    "carrito": {
                        "id": carrito.id,
                        "items_count": carrito.items.count()  # Asegurarse de contar los items actuales
                    }
                }
                request.session.modified = True  # Importante para guardar los cambios
                messages.success(request, "Bienvenido " + user.nombre)
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

        if not re.match("^[A-Za-z\\s]+$", nombre):
            messages.warning(request, "El nombre solo puede contener letras y espacios.")
            return redirect("registro")

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messages.warning(request, "Por favor, ingrese un correo electrónico válido.")
            return redirect("registro")

        if Usuario.objects.filter(email=email).exists():
            messages.warning(request, "El correo electrónico ya está registrado.")
            return redirect("registro")

        try:
            with transaction.atomic():
                user = Usuario.objects.create(
                    nombre=nombre,
                    email=email,
                    username=email,
                    direccion=direccion,
                    password=make_password(password),
                    rol=2  # Rol de cliente por defecto
                )
                
                # Crear carrito para el nuevo usuario
                Carrito.objects.create(usuario=user)
                
                messages.success(request, "Usuario creado exitosamente. Por favor, inicia sesión.")
                return redirect("login")
                
        except Exception as e:
            messages.error(request, f"Error al registrar usuario: {str(e)}")
            return redirect("registro")

    return render(request, 'muebles/perfil/registrarse.html')

def logout(request):
    if "logueo" in request.session:
        del request.session["logueo"]
        messages.success(request, "Sesión cerrada correctamente.")
    return redirect("index")

# ==================== PERFIL DE USUARIO ====================

@login_requerido
def perfil(request):
    logueo = request.session.get("logueo")
    user = Usuario.objects.get(id=logueo["id"])

    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        direccion = request.POST.get('direccion')
        foto = request.FILES.get('foto')

        if Usuario.objects.filter(email=email).exclude(id=user.id).exists():
            messages.warning(request, "El correo ya está registrado.")
            return redirect('perfil')

        user.nombre = nombre
        user.email = email
        user.direccion = direccion

        if foto:
            user.foto = foto

        user.save()

        # Actualizar sesión
        request.session["logueo"] = {
            "id": user.id,
            "nombre": user.nombre,
            "email": user.email,
            "rol": user.rol,
            "nombre_rol": user.get_rol_display(),
            "foto": user.foto.url if user.foto else None
        }

        messages.success(request, "Perfil actualizado exitosamente.")
        return redirect('perfil')

    return render(request, 'muebles/perfil/perfil.html', {'user': user})

# ==================== CARRITO DE COMPRAS ====================

@login_requerido
def agregar_al_carrito(request, mueble_id):
    logueo = request.session.get("logueo")
    mueble = get_object_or_404(Mueble, id=mueble_id)
    
    usuario = Usuario.objects.get(id=logueo["id"])
    carrito, creado = Carrito.objects.get_or_create(usuario=usuario)

    item, item_creado = ItemCarrito.objects.get_or_create(
        carrito=carrito, 
        mueble=mueble
    )
    
    if not item_creado:
        item.cantidad += 1
        item.save()
        messages.success(request, f"Se ha incrementado la cantidad de {mueble.nombre} en el carrito.")
    else:
        messages.success(request, f"{mueble.nombre} ha sido agregado al carrito.")

    # Actualizar la sesión con el nuevo conteo
    if "logueo" in request.session:
        request.session["logueo"]["carrito"]["items_count"] = carrito.items.count()
        request.session.modified = True  # Esto es importante para guardar los cambios

    # Redirigir según la fuente de la solicitud
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': carrito.items.count(),
            'message': messages.get_messages(request)[0].message if messages.get_messages(request) else ''
        })
    else:
        return redirect('ver_carrito')
    
@login_requerido
def eliminar_del_carrito(request, item_id):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    carrito = get_object_or_404(Carrito, usuario=usuario)
    
    item = get_object_or_404(ItemCarrito, id=item_id, carrito=carrito)
    nombre_mueble = item.mueble.nombre
    item.delete()
    
    # Actualizar la sesión
    request.session["logueo"]["carrito"]["items_count"] = carrito.items.count()
    request.session.modified = True
    
    if carrito.items.count() == 0:
        carrito.domicilio = None
        carrito.save()
        messages.success(request, "El carrito está vacío y se ha eliminado el domicilio.")
    else:
        messages.success(request, f"{nombre_mueble} ha sido eliminado del carrito.")
    
    return redirect('ver_carrito')

@login_requerido
def actualizar_cantidad(request, item_id):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    carrito = get_object_or_404(Carrito, usuario=usuario)
    item = get_object_or_404(ItemCarrito, id=item_id, carrito=carrito)
    
    cantidad = int(request.POST.get('cantidad', 1))

    if cantidad > 0:
        item.cantidad = cantidad
        item.save()
        messages.success(request, f"La cantidad de {item.mueble.nombre} ha sido actualizada a {cantidad}.")
    else:
        item.delete()
        if carrito.items.count() == 0:
            carrito.domicilio = None
            carrito.save()
            messages.success(request, "El carrito está vacío y se ha eliminado el domicilio.")
        else:
            messages.success(request, f"{item.mueble.nombre} ha sido eliminado del carrito.")

    # Actualizar la sesión en cualquier caso
    request.session["logueo"]["carrito"]["items_count"] = carrito.items.count()
    request.session.modified = True

    return redirect('ver_carrito')

@login_requerido
def ver_carrito(request):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    carrito, creado = Carrito.objects.get_or_create(usuario=usuario)
    
    if request.method == 'POST':
        form = DomicilioForm(request.POST)
        if form.is_valid():
            carrito.domicilio = form.cleaned_data['domicilio']
            carrito.save()
            messages.success(request, "Dirección de envío actualizada correctamente.")
            return redirect('ver_carrito')
    else:
        form = DomicilioForm(initial={'domicilio': carrito.domicilio})

    items = carrito.items.all()
    total = sum(item.subtotal() for item in items)
    costo_domicilio = carrito.COSTO_DOMICILIO if carrito.domicilio else 0

    return render(request, 'muebles/carrito/ver_carrito.html', {
        'items': items,
        'total': total,
        'form': form,
        'carrito': carrito,
        'costo_domicilio': costo_domicilio,
    })

@login_requerido
def eliminar_domicilio(request):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    carrito = get_object_or_404(Carrito, usuario=usuario)
    
    carrito.domicilio = None
    carrito.save()
    messages.success(request, "Domicilio eliminado correctamente.")
    return redirect('ver_carrito')

# ==================== PROCESO DE PAGO ====================

@login_requerido
def procesar_pago(request):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    carrito = get_object_or_404(Carrito, usuario=usuario)

    if not carrito.items.exists():
        messages.error(request, "Tu carrito está vacío")
        return redirect('ver_carrito')

    try:
        with transaction.atomic():
            # Crear el pedido
            pedido = Pedido.objects.create(
                usuario=usuario,
                total=carrito.calcular_total(),
                direccion_entrega=carrito.domicilio or usuario.direccion,
                estado='pendiente',
                costo_domicilio=carrito.COSTO_DOMICILIO if carrito.domicilio else 0
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

            # Actualizar la sesión
            request.session["logueo"]["carrito"]["items_count"] = 0
            request.session.modified = True

            messages.success(request, "¡Pago exitoso! Tu pedido ha sido procesado.")
            return redirect('mis_pedidos')
            
    except Exception as e:
        messages.error(request, f"Error al procesar el pago: {str(e)}")
        return redirect('ver_carrito')

@login_requerido
def mis_pedidos(request):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    pedidos = Pedido.objects.filter(usuario=usuario).order_by('-fecha')
    return render(request, 'muebles/pedidos/mis_pedidos.html', {'pedidos': pedidos})

# ==================== VISTAS DE ADMINISTRACIÓN ====================

@login_requerido(roles_permitidos=[1])
def admin_inicio(request):
    total_muebles = Mueble.objects.count()
    total_usuarios = Usuario.objects.count()
    total_pedidos = Pedido.objects.count()
    
    context = {
        'total_muebles': total_muebles,
        'total_usuarios': total_usuarios,
        'total_pedidos': total_pedidos,
    }
    return render(request, 'muebles/admin/inicio.html', context)

# CRUD Muebles
@login_requerido(roles_permitidos=[1])
def admin_muebles(request):
    muebles = Mueble.objects.all()
    propietarios = Propietario.objects.all()
    return render(request, 'muebles/admin/muebles/muebles.html', {
        'muebles': muebles,
        'propietarios': propietarios
    })

@login_requerido(roles_permitidos=[1])
def crear_mueble(request):
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

@login_requerido(roles_permitidos=[1])
def editar_mueble(request, id):
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

@login_requerido(roles_permitidos=[1])
def eliminar_mueble(request, id):
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

# CRUD Usuarios
@login_requerido(roles_permitidos=[1])
def admin_usuarios(request):
    usuarios = Usuario.objects.all().order_by('-id')
    return render(request, 'muebles/admin/usuarios/usuarios.html', {
        'usuarios': usuarios,
        'roles': Usuario.ROLES,
        'estados': Usuario.ESTADO
    })

@login_requerido(roles_permitidos=[1])
def crear_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                usuario = form.save(commit=False)
                usuario.set_password(form.cleaned_data['password'])
                usuario.save()
                
                # Crear carrito para el nuevo usuario
                Carrito.objects.create(usuario=usuario)
                
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
    
    return render(request, 'muebles/admin/usuarios/crear_usuario.html', {
        'form': form,
        'roles': Usuario.ROLES,
        'estados': Usuario.ESTADO
    })

@login_requerido(roles_permitidos=[1])
def editar_usuario(request, id):
    try:
        usuario = Usuario.objects.get(id=id)
        
        if request.method == 'POST':
            form = UsuarioForm(request.POST, request.FILES, instance=usuario)
            if form.is_valid():
                try:
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
        
        return render(request, 'muebles/admin/usuarios/editar_usuario.html', {
            'form': form,
            'usuario': usuario,
            'roles': Usuario.ROLES,
            'estados': Usuario.ESTADO
        })
        
    except Usuario.DoesNotExist:
        messages.error(request, 'El usuario que intentas editar no existe.')
        return redirect('admin_usuarios')

@login_requerido(roles_permitidos=[1])
def eliminar_usuario(request, id):
    logueo = request.session.get("logueo")
    
    try:
        usuario = Usuario.objects.get(id=id)
        
        # No permitir que un admin se elimine a sí mismo
        if usuario.id == logueo["id"]:
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

# Pedidos
@login_requerido(roles_permitidos=[1])
def admin_pedidos(request):
    pedidos = Pedido.objects.all().order_by('-fecha')
    return render(request, 'muebles/admin/pedidos/pedidos.html', {'pedidos': pedidos})

@login_requerido(roles_permitidos=[1])
def detalle_pedido(request, id):
    pedido = get_object_or_404(Pedido, id=id)
    detalles = DetallePedido.objects.filter(pedido=pedido)
    
    return render(request, 'muebles/admin/pedidos/detalle_pedido.html', {
        'pedido': pedido,
        'detalles': detalles
    })

# ==================== AYUDA Y SOPORTE ====================

def ayuda_principal(request):
    return render(request, 'muebles/ayuda/ayuda_principal.html')

def soporte(request):
    if request.method == 'POST':
        form = SoporteForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            email = form.cleaned_data['email']
            mensaje = form.cleaned_data['mensaje']
            
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

# ==================== PREGUNTAS Y FAQ ====================

@login_requerido
def lista_preguntas(request):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    
    estado = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '')
    
    preguntas = Pregunta.objects.filter(usuario=usuario)
    
    if estado:
        preguntas = preguntas.filter(estado=estado)
    if busqueda:
        preguntas = preguntas.filter(pregunta__icontains=busqueda)
    
    paginator = Paginator(preguntas.order_by('-fecha'), 6)
    page = request.GET.get('page')
    
    try:
        preguntas_pagina = paginator.page(page)
    except PageNotAnInteger:
        preguntas_pagina = paginator.page(1)
    except EmptyPage:
        preguntas_pagina = paginator.page(paginator.num_pages)
    
    return render(request, 'muebles/preguntas/lista_preguntas.html', {
        'preguntas': preguntas_pagina,
        'estado_seleccionado': estado,
        'busqueda': busqueda
    })

@login_requerido
def crear_pregunta(request):
    if request.method == 'POST':
        form = PreguntaForm(request.POST)
        if form.is_valid():
            logueo = request.session.get("logueo")
            usuario = Usuario.objects.get(id=logueo["id"])
            
            pregunta = form.save(commit=False)
            pregunta.usuario = usuario
            pregunta.save()
            messages.success(request, 'Pregunta enviada correctamente.')
            return redirect('lista_preguntas')
    else:
        form = PreguntaForm()
    
    return render(request, 'muebles/preguntas/crear_pregunta.html', {
        'form': form,
        'max_palabras': 100
    })

@login_requerido
def detalle_pregunta(request, pregunta_id):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    
    pregunta = get_object_or_404(Pregunta, id=pregunta_id, usuario=usuario)
    respuestas = pregunta.respuestas.all().order_by('fecha')
    
    return render(request, 'muebles/preguntas/detalle_pregunta.html', {
        'pregunta': pregunta,
        'respuestas': respuestas,
        'titulo_pagina': f'Detalle de Pregunta #{pregunta.id}'
    })

@login_requerido
def eliminar_preguntas_respondidas(request):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    
    if request.method == 'POST':
        try:
            preguntas = Pregunta.objects.filter(
                usuario=usuario,
                estado='respondida'
            )
            count = preguntas.count()
            preguntas.delete()
            
            messages.success(request, f'Se eliminaron {count} preguntas respondidas.')
            return redirect('lista_preguntas')
        except Exception as e:
            messages.error(request, f'Error al eliminar preguntas: {str(e)}')
            return redirect('lista_preguntas')
    
    return redirect('lista_preguntas')

@login_requerido
def eliminar_preguntas_antiguas(request):
    if request.method == 'POST':
        try:
            fecha_limite_30 = timezone.now() - timedelta(days=30)
            fecha_limite_3 = timezone.now() - timedelta(days=3)

            # Eliminar preguntas respondidas hace más de 30 días
            preguntas_30 = Pregunta.objects.filter(
                estado='respondida', 
                fecha_eliminacion__lte=fecha_limite_30
            )
            count_30 = preguntas_30.count()
            preguntas_30.delete()

            # Eliminar preguntas respondidas hace más de 3 días
            preguntas_3 = Pregunta.objects.filter(
                estado='respondida', 
                fecha_eliminacion__lte=fecha_limite_3
            )
            count_3 = preguntas_3.count()
            preguntas_3.delete()

            return JsonResponse({
                'status': 'success',
                'message': f'Eliminadas {count_30 + count_3} preguntas antiguas',
                'count_30': count_30,
                'count_3': count_3
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Método no permitido'
    }, status=405)
# Admin Preguntas
@login_requerido(roles_permitidos=[1])
def admin_lista_preguntas(request):
    preguntas = Pregunta.objects.all().order_by('-fecha')
    return render(request, 'muebles/admin/preguntas/lista_preguntas.html', {'preguntas': preguntas})

@login_requerido(roles_permitidos=[1])
def responder_pregunta(request, pregunta_id):
    logueo = request.session.get("logueo")
    admin = Usuario.objects.get(id=logueo["id"])
    
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    
    if request.method == 'POST':
        form = RespuestaForm(request.POST)
        if form.is_valid():
            respuesta = form.save(commit=False)
            respuesta.pregunta = pregunta
            respuesta.administrador = admin
            respuesta.save()
            
            if form.cleaned_data['es_faq']:
                pregunta.estado = 'publicada'
            else:
                pregunta.estado = 'respondida'
            pregunta.save()
            
            messages.success(request, 'Respuesta enviada correctamente.')
            return redirect('admin_lista_preguntas')
    else:
        form = RespuestaForm()
    
    return render(request, 'muebles/admin/preguntas/responder_pregunta.html', {
        'pregunta': pregunta,
        'form': form
    })

# FAQ
def faq_lista(request):
    faqs = FAQ.objects.filter(activo=True)
    faqs_por_categoria = {}
    
    for faq in faqs:
        categoria_nombre = faq.get_categoria_display()
        
        if categoria_nombre not in faqs_por_categoria:
            faqs_por_categoria[categoria_nombre] = []
        
        faqs_por_categoria[categoria_nombre].append(faq)
    
    return render(request, 'muebles/ayuda/faq_lista.html', {
        'faqs_por_categoria': faqs_por_categoria
    })

def votar_faq(request, faq_id):
    faq = get_object_or_404(FAQ, id=faq_id, activo=True)
    
    if 'votos_faq' not in request.session:
        request.session['votos_faq'] = []
    
    if faq_id not in request.session['votos_faq']:
        faq.votos += 1
        faq.save()
        request.session['votos_faq'].append(faq_id)
        request.session.modified = True
        messages.success(request, '¡Gracias por tu voto!')
    else:
        messages.warning(request, 'Ya has votado por esta pregunta')
    
    return redirect('faq_lista')

# Admin FAQ
@login_requerido(roles_permitidos=[1])
def admin_faq_lista(request):
    faq_editando = None
    editar_id = request.GET.get('editar_id')
    
    if editar_id:
        try:
            faq_editando = FAQ.objects.get(id=editar_id)
        except FAQ.DoesNotExist:
            messages.error(request, 'La FAQ que intentas editar no existe.')
    
    if request.method == 'POST':
        try:
            faq_id = request.POST.get('faq_id')
            
            if faq_id:  # Edición
                faq = FAQ.objects.get(id=faq_id)
                accion = "editada"
            else:  # Creación
                faq = FAQ()
                accion = "creada"
                faq.votos = 0
                faq.fecha_creacion = timezone.now()
            
            faq.pregunta = request.POST.get('pregunta')
            faq.respuesta = request.POST.get('respuesta')
            faq.categoria = request.POST.get('categoria')
            faq.activo = request.POST.get('activo') == 'on'
            
            if not all([faq.pregunta, faq.respuesta, faq.categoria]):
                messages.error(request, 'Todos los campos obligatorios deben ser completados.')
                return redirect('admin_faq_lista')
            
            faq.save()
            messages.success(request, f'FAQ {accion} exitosamente!')
            return redirect('admin_faq_lista')
            
        except Exception as e:
            messages.error(request, f'Error al guardar la FAQ: {str(e)}')
            return redirect('admin_faq_lista')
    
    faqs = FAQ.objects.all()
    return render(request, 'muebles/admin/faq/lista.html', {
        'faqs': faqs,
        'categorias': FAQ.CATEGORIAS,
        'faq_editando': faq_editando
    })

# ==================== ADMIN FAQ ====================

@login_requerido(roles_permitidos=[1])
def admin_crear_faq(request):
    logueo = request.session.get("logueo")
    
    if request.method == 'POST':
        try:
            pregunta = request.POST.get('pregunta')
            respuesta = request.POST.get('respuesta')
            categoria = request.POST.get('categoria')
            orden = request.POST.get('orden', 0)
            activo = request.POST.get('activo') == 'on'
            
            if not all([pregunta, respuesta, categoria]):
                messages.error(request, 'Los campos pregunta, respuesta y categoría son obligatorios.')
                return redirect('admin_faq_lista')
            
            FAQ.objects.create(
                pregunta=pregunta,
                respuesta=respuesta,
                categoria=categoria,
                orden=orden,
                activo=activo,
                votos=0,
                fecha_creacion=timezone.now()
            )
            
            messages.success(request, 'FAQ creada exitosamente!')
            return redirect('admin_faq_lista')
            
        except Exception as e:
            messages.error(request, f'Error al crear la FAQ: {str(e)}')
            return redirect('admin_faq_lista')
    
    return render(request, 'muebles/admin/faq/crear.html', {
        'categorias': FAQ.CATEGORIAS
    })

@login_requerido(roles_permitidos=[1])
def admin_editar_faq(request, pk):
    logueo = request.session.get("logueo")
    
    try:
        faq = FAQ.objects.get(id=pk)
        
        if request.method == 'POST':
            try:
                pregunta = request.POST.get('pregunta')
                respuesta = request.POST.get('respuesta')
                categoria = request.POST.get('categoria')
                orden = request.POST.get('orden', faq.orden)
                activo = request.POST.get('activo') == 'on'
                
                if not all([pregunta, respuesta, categoria]):
                    messages.error(request, 'Los campos pregunta, respuesta y categoría son obligatorios.')
                    return redirect('admin_editar_faq', pk=pk)
                
                faq.pregunta = pregunta
                faq.respuesta = respuesta
                faq.categoria = categoria
                faq.orden = orden
                faq.activo = activo
                faq.save()
                
                messages.success(request, 'FAQ actualizada exitosamente!')
                return redirect('admin_faq_lista')
                
            except Exception as e:
                messages.error(request, f'Error al actualizar la FAQ: {str(e)}')
                return redirect('admin_editar_faq', pk=pk)
        
        return render(request, 'muebles/admin/faq/editar.html', {
            'faq': faq,
            'categorias': FAQ.CATEGORIAS
        })
        
    except FAQ.DoesNotExist:
        messages.error(request, 'La FAQ que intentas editar no existe.')
        return redirect('admin_faq_lista')
    
@login_requerido(roles_permitidos=[1])
def admin_eliminar_faq(request, faq_id):
    try:
        faq = FAQ.objects.get(id=faq_id)
        faq.delete()
        messages.success(request, 'FAQ eliminada exitosamente!')
    except FAQ.DoesNotExist:
        messages.error(request, 'La FAQ que intentas eliminar no existe.')
    except Exception as e:
        messages.error(request, f'Error al eliminar la FAQ: {str(e)}')
    
    return redirect('admin_faq_lista')

# ==================== POLÍTICAS Y LEGAL ====================

def politica_cookies(request):
    return render(request, 'muebles/legal/Cookies.html')

def configurar_cookies(request):
    if request.method == 'POST':
        request.session['cookie_preferences'] = {
            'esenciales': 'esenciales' in request.POST,
            'analiticas': 'analiticas' in request.POST,
            'marketing': 'marketing' in request.POST
        }
        messages.success(request, "Tus preferencias de cookies han sido guardadas.")
        return redirect('index')
    
    preferencias = request.session.get('cookie_preferences', {
        'esenciales': True,
        'analiticas': False,
        'marketing': False
    })
    
    return render(request, 'muebles/legal/configurar_cookies.html', {'preferencias': preferencias})