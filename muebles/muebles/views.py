import re
from django.forms import DurationField
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
from django.db.models import Count, Avg, ExpressionWrapper, FloatField, DurationField

# ==================== VISTAS PÚBLICAS ====================

def index(request):
    muebles = Mueble.objects.all()
    return render(request, 'muebles/index.html', {'muebles': muebles})

def muebles_list(request):
    muebles = Mueble.objects.all()
    return render(request, 'muebles/mueble/muebles_list.html', {'muebles': muebles})

# ==================== RENTA DE MUEBLES ====================

def rentar_mueble(request, mueble_id):
    mueble = get_object_or_404(Mueble, id=mueble_id)
    
    # Verificar si el usuario está logueado usando la sesión
    logueo = request.session.get("logueo")
    usuario_logueado = logueo is not None
    
    if usuario_logueado:
        try:
            usuario = Usuario.objects.get(id=logueo["id"])
        except Usuario.DoesNotExist:
            usuario = None
    else:
        usuario = None

    if request.method == 'POST':
        form = RentaForm(request.POST)
        if form.is_valid():
            try:
                fecha_inicio = form.cleaned_data['fecha_inicio']
                fecha_fin = form.cleaned_data['fecha_fin']

                if usuario:
                    renta = Renta(
                        mueble=mueble,
                        usuario=usuario,
                        fecha_inicio=fecha_inicio,
                        fecha_fin=fecha_fin,
                        duracion_meses=form.cleaned_data.get('duracion_meses', 0),
                        duracion_dias=form.cleaned_data.get('duracion_dias', 0)
                    )
                    renta.save()

                carrito = Carrito.obtener_carrito(request)

                item_existente = carrito.items.filter(
                    mueble=mueble,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin
                ).first()

                if item_existente:
                    item_existente.cantidad += 1
                    item_existente.save()
                    messages.success(request, f"Se ha incrementado la cantidad de {mueble.nombre} en el carrito.")
                else:
                    ItemCarrito.objects.create(
                        carrito=carrito,
                        mueble=mueble,
                        cantidad=1,
                        fecha_inicio=fecha_inicio,
                        fecha_fin=fecha_fin
                    )
                    messages.success(request, f"{mueble.nombre} ha sido agregado al carrito.")

                # Actualizar conteo en sesión de manera consistente
                items_count = carrito.items.count()
                
                if usuario_logueado:
                    if "logueo" not in request.session:
                        request.session["logueo"] = {}
                    if "carrito" not in request.session["logueo"]:
                        request.session["logueo"]["carrito"] = {}
                    
                    request.session["logueo"]["carrito"]["items_count"] = items_count
                else:
                    request.session['carrito_items_count'] = items_count
                
                request.session.modified = True

                return redirect('ver_carrito')

            except Exception as e:
                messages.error(request, f"Error al procesar la renta: {str(e)}")
                return redirect('rentar_mueble', mueble_id=mueble_id)
    else:
        form = RentaForm(initial={'mueble': mueble})

    return render(request, 'muebles/mueble/rentar_mueble.html', {
        'form': form,
        'mueble': mueble,
        'usuario_no_logueado': not usuario_logueado
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
                # Crear o actualizar la sesión
                request.session["logueo"] = {
                    "id": user.id,
                    "nombre": user.nombre,
                    "email": user.email,
                    "rol": user.rol,
                    "nombre_rol": user.get_rol_display(),
                    "foto": user.foto.url if user.foto else None,
                    "carrito": {
                        "id": user.carrito.id if hasattr(user, 'carrito') else None,
                        "items_count": user.carrito.items.count() if hasattr(user, 'carrito') else 0
                    }
                }
                
                # Migrar carrito de sesión a usuario si existe
                if not request.user.is_authenticated and request.session.session_key:
                    carrito_invitado = Carrito.objects.filter(
                        session_key=request.session.session_key,
                        usuario__isnull=True
                    ).first()

                    if carrito_invitado and carrito_invitado.items.exists():
                        carrito_usuario, _ = Carrito.objects.get_or_create(usuario=user)
                        
                        for item in carrito_invitado.items.all():
                            item_existente = carrito_usuario.items.filter(
                                mueble=item.mueble,
                                fecha_inicio=item.fecha_inicio,
                                fecha_fin=item.fecha_fin
                            ).first()

                            if item_existente:
                                item_existente.cantidad += item.cantidad
                                item_existente.save()
                                item.delete()
                            else:
                                item.carrito = carrito_usuario
                                item.save()

                        # Migrar servicios adicionales
                        if carrito_invitado.domicilio and not carrito_usuario.domicilio:
                            carrito_usuario.domicilio = carrito_invitado.domicilio
                        if carrito_invitado.servicio_instalacion and not carrito_usuario.servicio_instalacion:
                            carrito_usuario.servicio_instalacion = carrito_invitado.servicio_instalacion

                        carrito_usuario.save()
                        carrito_invitado.delete()
                        
                        # Actualizar conteo en sesión del usuario
                        request.session["logueo"]["carrito"]["items_count"] = carrito_usuario.items.count()
                        
                        # Limpiar el contador de invitado
                        if 'carrito_items_count' in request.session:
                            del request.session['carrito_items_count']
                
                messages.success(request, f"Bienvenido {user.nombre}")
                return redirect('index')
            else:
                messages.warning(request, "Contraseña incorrecta.")
        except Usuario.DoesNotExist:
            messages.warning(request, "El correo electrónico no está registrado.")

    return render(request, 'muebles/perfil/login.html')


def registro(request):
    if request.method == 'POST':
        data = request.POST
        errors = {}

        # Obtener datos
        nombre = data.get('nombre', '').strip()
        email = data.get('email', '').strip()
        direccion = data.get('direccion', '').strip()
        password = data.get('password', '').strip()
        tipo_usuario = int(data.get('tipo_usuario', 3))
        tipo_documento = data.get('tipo_documento', 'CC')
        numero_documento = data.get('numero_documento', '').strip()
        nombre_empresa = data.get('nombre_empresa', '').strip()
        telefono = data.get('telefono', '').strip()
        tipo_persona = data.get('tipo_persona', 'natural')
        telefono_empresa = data.get('telefono_empresa', '').strip()

        # Validaciones campo por campo
        if not re.match(r"^[A-Za-z\s]+$", nombre):
            errors['nombre'] = "El nombre solo puede contener letras y espacios."

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errors['email'] = "Por favor, ingrese un correo electrónico válido."
        elif Usuario.objects.filter(email=email).exists():
            errors['email'] = "El correo electrónico ya está registrado."

        if not direccion:
            errors['direccion'] = "La dirección es obligatoria."

        if not telefono or not telefono.isdigit() or len(telefono) != 10:
            errors['telefono'] = "Debe ingresar un número de celular válido de 10 dígitos."

        if not password or len(password) < 8:
            errors['password'] = "La contraseña debe tener al menos 8 caracteres."

        if not numero_documento or not numero_documento.isdigit():
            errors['numero_documento'] = "El número de documento debe contener solo números."

        if tipo_usuario == 2:  # Proveedor
            if not nombre_empresa:
                errors['nombre_empresa'] = "El nombre de la empresa es obligatorio."
            if not telefono_empresa or not telefono_empresa.isdigit() or len(telefono_empresa) < 7:
                errors['telefono_empresa'] = "El teléfono de empresa debe contener al menos 7 dígitos."

        # Si hay errores, volver al formulario con valores y errores
        if errors:
            form = {
                'nombre': nombre,
                'email': email,
                'direccion': direccion,
                'telefono': telefono,
                'tipo_usuario': tipo_usuario,
                'tipo_documento': tipo_documento,
                'numero_documento': numero_documento,
                'tipo_persona': tipo_persona,
                'nombre_empresa': nombre_empresa,
                'telefono_empresa': telefono_empresa,
            }
            return render(request, 'muebles/perfil/registrarse.html', {
                'errors': errors, 
                'form': form,
                'field_errors': errors  # Pasamos los errores nuevamente para asegurar
            })

        try:
            with transaction.atomic():
                # Crear usuario
                usuario = Usuario.objects.create(
                    nombre=nombre,
                    email=email,
                    username=email,
                    direccion=direccion,
                    password=make_password(password),
                    rol=tipo_usuario,
                    tipo_documento=tipo_documento,
                    numero_documento=numero_documento,
                    tipo_persona=tipo_persona,
                    telefono=telefono
                )

                # Crear carrito
                Carrito.objects.create(usuario=usuario)

                # Si es proveedor, crear proveedor
                if tipo_usuario == 2:
                    Proveedor.objects.create(
                        usuario=usuario,
                        nombre_empresa=nombre_empresa,
                        telefono=telefono_empresa or telefono
                    )

                messages.success(request, "Usuario registrado exitosamente. Por favor, inicia sesión.")
                return redirect("login")

        except Exception as e:
            messages.error(request, f"Ocurrió un error al registrar el usuario: {str(e)}")
            return redirect("registro")

    return render(request, 'muebles/perfil/registrarse.html')

def logout(request):
    if "logueo" in request.session:
        del request.session["logueo"]
    if 'carrito_items_count' in request.session:
        del request.session['carrito_items_count']
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("index")

# ==================== PERFIL DE USUARIO ====================
from django.contrib.auth import update_session_auth_hash

@login_required
def perfil(request):
    logueo = request.session.get("logueo")
    user = Usuario.objects.get(id=logueo["id"])
    
    if request.method == 'POST':
        if 'editar_perfil' in request.POST:
            form_perfil = EditarPerfilForm(request.POST, request.FILES, instance=user)
            if form_perfil.is_valid():
                form_perfil.save()
                # Actualizar la sesión
                request.session['logueo']['nombre'] = user.nombre
                request.session['logueo']['email'] = user.email
                if user.foto:
                    request.session['logueo']['foto'] = user.foto.url
                request.session.modified = True
                messages.success(request, 'Perfil actualizado exitosamente!')
                return redirect('perfil')
            
        elif 'cambiar_contrasena' in request.POST:
            form_contrasena = CambiarContrasenaForm(request.POST)
            if form_contrasena.is_valid():
                nueva_password = form_contrasena.cleaned_data['nueva_contrasena']
                user.set_password(nueva_password)
                user.save()
                # Actualizar la sesión para evitar deslogueo
                update_session_auth_hash(request, user)
                messages.success(request, 'Contraseña cambiada exitosamente!')
                return redirect('perfil')
    else:
        form_perfil = EditarPerfilForm(instance=user)
        form_contrasena = CambiarContrasenaForm()

    # Obtener datos adicionales según el rol
    context = {
        'user': user,
        'form_perfil': form_perfil,
        'form_contrasena': form_contrasena,
    }
    
    # Añadir datos específicos según el rol
    if user.rol == 1:  # Admin
        total_usuarios = Usuario.objects.count()
        total_muebles = Mueble.objects.count()
        total_pedidos = Pedido.objects.count()
        context.update({
            'total_usuarios': total_usuarios,
            'total_muebles': total_muebles,
            'total_pedidos': total_pedidos,
        })
        return render(request, 'muebles/perfil/perfil_admin.html', context)
    
    elif user.rol == 2:  # Propietario/Proveedor
        proveedor = get_object_or_404(Proveedor, usuario=user)
        total_muebles = Mueble.objects.filter(proveedor=proveedor).count()
        muebles_activos = Mueble.objects.filter(proveedor=proveedor).count()
        
        ganancias_totales = DetallePedido.objects.filter(
            mueble__proveedor=proveedor
        ).aggregate(total=Sum('ganancia_propietario'))['total'] or 0
        
        pedidos_recientes = Pedido.objects.filter(
            detalles__mueble__proveedor=proveedor
        ).distinct().order_by('-fecha')[:5]
        
        context.update({
            'proveedor': proveedor,
            'total_muebles': total_muebles,
            'muebles_activos': muebles_activos,
            'ganancias_totales': ganancias_totales,
            'pedidos_recientes': pedidos_recientes,
        })
        return render(request, 'muebles/perfil/perfil_propietario.html', context)
    
    elif user.rol == 3:  # Cliente
        rentas = Renta.objects.filter(usuario=user).order_by('-fecha_inicio')
        context['rentas'] = rentas
        return render(request, 'muebles/perfil/perfil.html', context)
    
    elif user.rol == 4:  # Soporte
        problemas = ReporteProblema.objects.filter(usuario_asignado=user)
        total_problemas = ReporteProblema.objects.count()
        problemas_abiertos = ReporteProblema.objects.filter(estado='abierto').count()
        problemas_en_progreso = ReporteProblema.objects.filter(estado='en_progreso').count()
        problemas_resueltos = ReporteProblema.objects.filter(estado='resuelto').count()
        
        context.update({
            'problemas': problemas,
            'total_problemas': total_problemas,
            'problemas_abiertos': problemas_abiertos,
            'problemas_en_progreso': problemas_en_progreso,
            'problemas_resueltos': problemas_resueltos,
        })
        return render(request, 'muebles/perfil/perfil_soporte.html', context)
    
    # Por defecto, vista de cliente
    return render(request, 'muebles/perfil/perfil_cliente.html', context)


@login_requerido(roles_permitidos=[1])
def perfil_admin(request):
    logueo = request.session.get("logueo")
    user = Usuario.objects.get(id=logueo["id"])

    form_contrasena = CambiarContrasenaForm()
    form_perfil = EditarPerfilForm(instance=user)

    if request.method == 'POST':
        # 1. Editar perfil
        if 'editar_perfil' in request.POST:
            form_perfil = EditarPerfilForm(request.POST, request.FILES, instance=user)
            if form_perfil.is_valid():
                form_perfil.save()
                request.session['logueo'] = {
                    "id": user.id,
                    "nombre": user.nombre,
                    "email": user.email,
                    "rol": user.rol,
                    "nombre_rol": user.get_rol_display(),
                    "foto": user.foto.url if user.foto else None
                }
                messages.success(request, '¡Perfil actualizado exitosamente!')
                return redirect('perfil_admin')
            else:
                messages.warning(request, 'Por favor corrige los errores en el formulario de perfil: ' + str(form_perfil.errors))

        # 2. Cambiar contraseña
        elif 'cambiar_contrasena' in request.POST:
            form_contrasena = CambiarContrasenaForm(request.POST)
            if form_contrasena.is_valid():
                try:
                    nueva_password = form_contrasena.cleaned_data['nueva_contrasena']
                    user.set_password(nueva_password)
                    user.save()
                    update_session_auth_hash(request, user)  # mantener la sesión activa
                    messages.success(request, '¡Contraseña cambiada exitosamente!')
                    return redirect('perfil_admin')
                except Exception as e:
                    messages.error(request, f'Error al cambiar la contraseña: {str(e)}')
            else:
                messages.warning(request, 'Por favor corrige los errores en el formulario de contraseña: ' + str(form_contrasena.errors))

    # Obtener datos adicionales según el rol
    total_usuarios = Usuario.objects.count()
    total_muebles = Mueble.objects.count()
    total_pedidos = Pedido.objects.count()

    context = {
        'user': user,
        'form_contrasena': form_contrasena,
        'form_perfil': form_perfil,
        'total_usuarios': total_usuarios,
        'total_muebles': total_muebles,
        'total_pedidos': total_pedidos,
    }

    return render(request, 'muebles/perfil/perfil_admin.html', context)



@login_requerido(roles_permitidos=[2])
def perfil_proveedor(request):
    logueo = request.session.get("logueo")
    user = Usuario.objects.get(id=logueo["id"])

    form_contrasena = CambiarContrasenaForm()
    form_perfil = EditarPerfilForm(instance=user)

    if request.method == 'POST':
        # 1. Editar perfil
        if 'editar_perfil' in request.POST:
            form_perfil = EditarPerfilForm(request.POST, request.FILES, instance=user)
            if form_perfil.is_valid():
                form_perfil.save()
                # Actualizar el nombre de la empresa si se proporciona
                nombre_empresa = request.POST.get('nombre_empresa')
                if nombre_empresa:
                    proveedor = get_object_or_404(Proveedor, usuario=user)
                    proveedor.nombre_empresa = nombre_empresa
                    proveedor.save()

                request.session['logueo'] = {
                    "id": user.id,
                    "nombre": user.nombre,
                    "email": user.email,
                    "rol": user.rol,
                    "nombre_rol": user.get_rol_display(),
                    "foto": user.foto.url if user.foto else None
                }
                messages.success(request, '¡Perfil actualizado exitosamente!')
                return redirect('perfil_proveedor')
            else:
                messages.warning(request, 'Por favor corrige los errores en el formulario de perfil: ' + str(form_perfil.errors))

        # 2. Cambiar contraseña
        elif 'cambiar_contrasena' in request.POST:
            form_contrasena = CambiarContrasenaForm(request.POST)
            if form_contrasena.is_valid():
                try:
                    nueva_password = form_contrasena.cleaned_data['nueva_contrasena']
                    user.set_password(nueva_password)
                    user.save()
                    update_session_auth_hash(request, user)  # mantener la sesión activa
                    messages.success(request, '¡Contraseña cambiada exitosamente!')
                    return redirect('perfil_proveedor')
                except Exception as e:
                    messages.error(request, f'Error al cambiar la contraseña: {str(e)}')
            else:
                messages.warning(request, 'Por favor corrige los errores en el formulario de contraseña: ' + str(form_contrasena.errors))

    # Obtener datos adicionales según el rol
    proveedor = get_object_or_404(Proveedor, usuario=user)
    total_muebles = Mueble.objects.filter(proveedor=proveedor).count()
    muebles_activos = Mueble.objects.filter(proveedor=proveedor).count()

    ganancias_totales = DetallePedido.objects.filter(
        mueble__proveedor=proveedor
    ).aggregate(total=Sum('ganancia_propietario'))['total'] or 0

    # Agregar las ganancias por pedido
    pedidos_recientes = Pedido.objects.filter(
        detalles__mueble__proveedor=proveedor
    ).distinct().order_by('-fecha')[:5]

    for pedido in pedidos_recientes:
        # Filtramos solo los detalles de ese proveedor
        detalles = pedido.detalles.filter(mueble__proveedor=proveedor)
        pedido.ganancia_propietario = sum(d.ganancia_propietario for d in detalles)

    context = {
        'user': user,
        'form_contrasena': form_contrasena,
        'form_perfil': form_perfil,
        'proveedor': proveedor,
        'total_muebles': total_muebles,
        'muebles_activos': muebles_activos,
        'ganancias_totales': ganancias_totales,
        'pedidos_recientes': pedidos_recientes,
    }

    return render(request, 'muebles/perfil/perfil_proveedor.html', context)



@login_requerido(roles_permitidos=[3])
def perfil_cliente(request):
    logueo = request.session.get("logueo")
    user = Usuario.objects.get(id=logueo["id"])

    form_contrasena = CambiarContrasenaForm()
    form_perfil = EditarPerfilForm(instance=user)

    if request.method == 'POST':
        # 1. Editar perfil
        if 'editar_perfil' in request.POST:
            form_perfil = EditarPerfilForm(request.POST, request.FILES, instance=user)
            if form_perfil.is_valid():
                form_perfil.save()
                request.session['logueo'] = {
                    "id": user.id,
                    "nombre": user.nombre,
                    "email": user.email,
                    "rol": user.rol,
                    "nombre_rol": user.get_rol_display(),
                    "foto": user.foto.url if user.foto else None
                }
                messages.success(request, '¡Perfil actualizado exitosamente!')
                return redirect('perfil_cliente')
            else:
                messages.warning(request, 'Por favor corrige los errores en el formulario de perfil: ' + str(form_perfil.errors))

        # 2. Cambiar contraseña
        elif 'cambiar_contrasena' in request.POST:
            form_contrasena = CambiarContrasenaForm(request.POST)
            if form_contrasena.is_valid():
                try:
                    nueva_password = form_contrasena.cleaned_data['nueva_contrasena']
                    user.set_password(nueva_password)
                    user.save()
                    update_session_auth_hash(request, user)  # mantener la sesión activa
                    messages.success(request, '¡Contraseña cambiada exitosamente!')
                    return redirect('perfil_cliente')
                except Exception as e:
                    messages.error(request, f'Error al cambiar la contraseña: {str(e)}')
            else:
                messages.warning(request, 'Por favor corrige los errores en el formulario de contraseña: ' + str(form_contrasena.errors))

    context = {
        'user': user,
        'form_contrasena': form_contrasena,
        'form_perfil': form_perfil,
    }

    return render(request, 'muebles/perfil/perfil.html', context)


@login_requerido(roles_permitidos=[4])
def perfil_soporte(request):
    logueo = request.session.get("logueo")
    user = Usuario.objects.get(id=logueo["id"])

    form_contrasena = CambiarContrasenaForm()
    form_perfil = EditarPerfilForm(instance=user)

    if request.method == 'POST':
        # 1. Editar perfil
        if 'editar_perfil' in request.POST:
            form_perfil = EditarPerfilForm(request.POST, request.FILES, instance=user)
            if form_perfil.is_valid():
                form_perfil.save()
                request.session['logueo'] = {
                    "id": user.id,
                    "nombre": user.nombre,
                    "email": user.email,
                    "rol": user.rol,
                    "nombre_rol": user.get_rol_display(),
                    "foto": user.foto.url if user.foto else None
                }
                messages.success(request, '¡Perfil actualizado exitosamente!')
                return redirect('perfil_soporte')
            else:
                messages.warning(request, 'Por favor corrige los errores en el formulario de perfil: ' + str(form_perfil.errors))

        # 2. Cambiar contraseña
        elif 'cambiar_contrasena' in request.POST:
            form_contrasena = CambiarContrasenaForm(request.POST)
            if form_contrasena.is_valid():
                try:
                    nueva_password = form_contrasena.cleaned_data['nueva_contrasena']
                    user.set_password(nueva_password)
                    user.save()
                    update_session_auth_hash(request, user)  # mantener la sesión activa
                    messages.success(request, '¡Contraseña cambiada exitosamente!')
                    return redirect('perfil_soporte')
                except Exception as e:
                    messages.error(request, f'Error al cambiar la contraseña: {str(e)}')
            else:
                messages.warning(request, 'Por favor corrige los errores en el formulario de contraseña: ' + str(form_contrasena.errors))

    context = {
        'user': user,
        'form_contrasena': form_contrasena,
        'form_perfil': form_perfil,
        'problemas': ReporteProblema.objects.filter(usuario_asignado=user),
        'total_problemas': ReporteProblema.objects.count(),
        'problemas_abiertos': ReporteProblema.objects.filter(estado='abierto').count(),
        'problemas_en_progreso': ReporteProblema.objects.filter(estado='en_progreso').count(),
        'problemas_resueltos': ReporteProblema.objects.filter(estado='resuelto').count(),
    }

    return render(request, 'muebles/perfil/perfil_soporte.html', context)



# ==================== CARRITO DE COMPRAS ====================

def agregar_al_carrito(request, mueble_id):
    mueble = get_object_or_404(Mueble, id=mueble_id)
    
    if request.method == 'POST':
        form = RentaForm(request.POST)
        if form.is_valid():
            fecha_inicio = form.cleaned_data['fecha_inicio']
            fecha_fin = form.cleaned_data['fecha_fin']
            
            carrito = Carrito.obtener_carrito(request)
            
            # Verificar si ya existe un ítem igual en el carrito
            item_existente = carrito.items.filter(
                mueble=mueble,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            ).first()

            if item_existente:
                item_existente.cantidad += 1
                item_existente.save()
                messages.success(request, f"Se ha incrementado la cantidad de {mueble.nombre} en el carrito.")
            else:
                ItemCarrito.objects.create(
                    carrito=carrito,
                    mueble=mueble,
                    cantidad=1,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin
                )
                messages.success(request, f"{mueble.nombre} ha sido agregado al carrito.")

            # Actualizar la sesión con el conteo de items
            request.session['carrito_items_count'] = carrito.items.count()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'{mueble.nombre} agregado al carrito',
                    'carrito_count': carrito.items.count()
                })
            
            return redirect('ver_carrito')
    else:
        form = RentaForm()

    return render(request, 'muebles/mueble/rentar_mueble.html', {
        'form': form,
        'mueble': mueble,
    })



def eliminar_del_carrito(request, item_id):
    carrito = Carrito.obtener_carrito(request)
    item = get_object_or_404(ItemCarrito, id=item_id, carrito=carrito)
    nombre_mueble = item.mueble.nombre
    item.delete()

    # Si no quedan items, limpiar servicios
    if not carrito.items.exists():
        carrito.domicilio = None
        carrito.servicio_instalacion = False
        carrito.save()

    # Actualizar la sesión correctamente
    items_count = carrito.items.count()
    
    if request.session.get("logueo"):
        if "carrito" not in request.session["logueo"]:
            request.session["logueo"]["carrito"] = {}
        request.session["logueo"]["carrito"]["items_count"] = items_count
    else:
        request.session['carrito_items_count'] = items_count
    
    request.session.modified = True

    messages.success(request, f"{nombre_mueble} ha sido eliminado del carrito.")
    return redirect('ver_carrito')

def actualizar_cantidad(request, item_id):
    carrito = Carrito.obtener_carrito(request)
    item = get_object_or_404(ItemCarrito, id=item_id, carrito=carrito)

    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad', 1))

        if cantidad < 1:
            messages.warning(request, f"La cantidad mínima permitida es 1. Si deseas eliminar {item.mueble.nombre}, usa el botón 'Eliminar'.")
        elif cantidad > 10:
            messages.warning(request, f"La cantidad máxima permitida por artículo es 10. Para cantidades mayores, contáctanos.")
        else:
            item.cantidad = cantidad
            item.save()
            messages.success(request, f"La cantidad de {item.mueble.nombre} ha sido actualizada a {cantidad}.")

        # Actualizar la sesión
        request.session['carrito_items_count'] = carrito.items.count()

    return redirect('ver_carrito')


def ver_carrito(request):
    carrito = Carrito.obtener_carrito(request)
    items = carrito.items.all().select_related('mueble')
    
    # Calcular ahorros y subtotales
    ahorro_total = 0
    subtotal = 0
    costo_domicilio = 0
    costo_instalacion = 0
    total = 0

    if items.exists():  # Solo si hay items
        for item in items:
            item.dias = (item.fecha_fin - item.fecha_inicio).days + 1
            if item.mueble.en_oferta:
                item.ahorro_por_dia = item.mueble.precio_diario - item.mueble.precio_con_descuento
                item.ahorro_total = (item.mueble.precio_diario * item.cantidad * item.dias) - item.subtotal()
                ahorro_total += item.ahorro_total
            else:
                item.ahorro_por_dia = 0
                item.ahorro_total = 0

        subtotal = sum(item.subtotal() for item in items)
        costo_domicilio = carrito.COSTO_DOMICILIO if carrito.domicilio else 0
        costo_instalacion = carrito.COSTO_INSTALACION_COMPLETO if carrito.servicio_instalacion else 0
        total = subtotal + costo_domicilio + costo_instalacion

    # Verificar si el usuario está logueado
    usuario_no_logueado = not request.session.get("logueo")
    
    context = {
        'items': items,
        'carrito': carrito,
        'subtotal': subtotal,
        'total': total,
        'costo_domicilio': costo_domicilio,
        'costo_instalacion': costo_instalacion,
        'ahorro_total': ahorro_total,
        'usuario_no_logueado': usuario_no_logueado,  # Usar esta variable para mostrar/ocultar mensaje
        'domicilio': carrito.domicilio if items.exists() else None,
        'servicio_instalacion': carrito.servicio_instalacion if items.exists() else None,
        'carrito_vacio': not items.exists(),
    }
    
    return render(request, 'muebles/carrito/ver_carrito.html', context)


def agregar_direccion(request):
    if request.method == 'POST':
        domicilio = request.POST.get('domicilio', '').strip()
        
        if domicilio:
            # Obtener el carrito (para usuario logueado o sesión)
            carrito = Carrito.obtener_carrito(request)
            carrito.domicilio = domicilio
            carrito.save()
            
            messages.success(request, 'Dirección de entrega agregada correctamente')
        else:
            messages.error(request, 'Debes ingresar una dirección válida')
    
    return redirect('ver_carrito')

def agregar_instalacion(request):
    if request.method == 'POST':
        # Obtener el carrito (para usuario logueado o sesión)
        carrito = Carrito.obtener_carrito(request)
        
        # Alternar el estado del servicio de instalación
        carrito.servicio_instalacion = not carrito.servicio_instalacion
        carrito.save()
        
        if carrito.servicio_instalacion:
            messages.success(request, 'Servicio de instalación agregado correctamente')
        else:
            messages.success(request, 'Servicio de instalación removido correctamente')
    
    return redirect('ver_carrito')

def actualizar_direccion(request): 
    carrito = Carrito.obtener_carrito(request)
    
    if request.method == 'POST':
        if not carrito.items.exists():
            messages.error(request, 'Debes tener items en el carrito para agregar una dirección')
            return redirect('ver_carrito')
            
        domicilio = request.POST.get('domicilio')

        if domicilio:
            if carrito.domicilio:
                mensaje = 'Dirección actualizada exitosamente'
            else:
                mensaje = 'Dirección agregada exitosamente'

            carrito.domicilio = domicilio
            carrito.save()
            messages.success(request, mensaje)
        else:
            messages.error(request, 'Dirección no válida')

    return redirect('ver_carrito')

def actualizar_instalacion(request):
    carrito = Carrito.obtener_carrito(request)
    
    if request.method == 'POST':
        # Solo permitir si hay items en el carrito
        if not carrito.items.exists():
            messages.error(request, 'Debes tener items en el carrito para agregar servicios')
            return redirect('ver_carrito')
            
        servicio_instalacion = request.POST.get('servicio_instalacion') == 'on'
        carrito.servicio_instalacion = servicio_instalacion
        carrito.save()
        
        if servicio_instalacion:
            messages.success(request, 'Servicio de instalación agregado al carrito')
        else:
            messages.success(request, 'Servicio de instalación removido del carrito')

    return redirect('ver_carrito')





    




def eliminar_domicilio(request):
    if request.user.is_authenticated:
        carrito = get_object_or_404(Carrito, usuario=request.user)
        carrito.domicilio = None
        carrito.save()
    else:
        if 'carrito_session' in request.session and 'domicilio' in request.session['carrito_session']:
            del request.session['carrito_session']['domicilio']
            request.session.modified = True
    
    messages.success(request, "Domicilio eliminado correctamente.")
    return redirect('ver_carrito')

def eliminar_instalacion(request):
    if request.user.is_authenticated:
        carrito = get_object_or_404(Carrito, usuario=request.user)
        carrito.servicio_instalacion = False
        carrito.save()
    else:
        if 'carrito_session' in request.session and 'servicio_instalacion' in request.session['carrito_session']:
            del request.session['carrito_session']['servicio_instalacion']
            request.session.modified = True
    
    messages.success(request, "Servicio de instalación eliminado correctamente.")
    return redirect('ver_carrito')

# ==================== PROCESO DE PAGO ====================
@login_requerido
def formulario_pago(request):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    carrito = Carrito.obtener_carrito(request)
    
    if not carrito.items.exists():
        messages.error(request, "Tu carrito está vacío")
        return redirect('ver_carrito')

    # Calcular totales
    subtotal = sum(item.subtotal() for item in carrito.items.all())
    costo_domicilio = carrito.COSTO_DOMICILIO if carrito.domicilio else 0
    costo_instalacion = carrito.COSTO_INSTALACION_COMPLETO if carrito.servicio_instalacion else 0
    total = subtotal + costo_domicilio + costo_instalacion

    if request.method == 'POST':
        form = MetodoPagoForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Crear el pedido
                    pedido = Pedido.objects.create(
                        usuario=usuario,
                        total=total,
                        direccion_entrega=carrito.domicilio or usuario.direccion,
                        estado='pendiente',
                        costo_domicilio=costo_domicilio,
                        servicio_instalacion=carrito.servicio_instalacion
                    )

                    comision_total = 0

                    # Crear los detalles del pedido
                    for item in carrito.items.all():
                        dias = (item.fecha_fin - item.fecha_inicio).days + 1
                        comision = (item.mueble.precio_diario * item.mueble.comision / 100) * item.cantidad * dias
                        ganancia_propietario = (item.mueble.precio_diario - (item.mueble.precio_diario * item.mueble.comision / 100)) * item.cantidad * dias

                        DetallePedido.objects.create(
                            pedido=pedido,
                            mueble=item.mueble,
                            cantidad=item.cantidad,
                            precio_unitario=item.mueble.precio_diario,
                            subtotal=item.subtotal(),
                            comision=comision,
                            ganancia_propietario=ganancia_propietario
                        )
                        comision_total += comision

                    # Actualizar comisión total
                    pedido.comision_total = comision_total
                    pedido.save()

                    # Limpiar el carrito
                    carrito.items.all().delete()
                    carrito.domicilio = None
                    carrito.servicio_instalacion = False
                    carrito.save()

                    # Actualizar la sesión
                    request.session["logueo"]["carrito"]["items_count"] = 0
                    request.session.modified = True

                    messages.success(request, "¡Pago exitoso! Tu pedido ha sido procesado.")
                    return redirect('detalle_pedido', id=pedido.id)

            except Exception as e:
                messages.error(request, f"Error al procesar el pago: {str(e)}")
                return redirect('formulario_pago')
    else:
        # Datos iniciales del formulario
        initial_data = {
            'nombre_tarjeta': usuario.nombre,
            'email': usuario.email,
            'direccion': carrito.domicilio or usuario.direccion,
        }
        form = MetodoPagoForm(initial=initial_data)

    context = {
        'form': form,
        'usuario': usuario,
        'carrito': carrito,
        'subtotal': subtotal,
        'total': total,
        'costo_domicilio': costo_domicilio,
        'costo_instalacion': costo_instalacion,
    }
    
    return render(request, 'muebles/carrito/formulario_pago.html', context)


@login_requerido
def detalle_pedido_usuario(request, id):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    
    try:
        # Solo permite ver el pedido si pertenece al usuario actual
        pedido = Pedido.objects.get(id=id, usuario=usuario)
        detalles = DetallePedido.objects.filter(pedido=pedido)
        
        # Calcular días de renta para cada item
        for detalle in detalles:
            detalle.dias = (detalle.pedido.fecha_fin - detalle.pedido.fecha_inicio).days + 1
        
        context = {
            'pedido': pedido,
            'detalles': detalles,
            'usuario': usuario,
        }
        
        return render(request, 'muebles/carrito/detalle_pedido_usuario.html', context)
        
    except Pedido.DoesNotExist:
        messages.error(request, "El pedido no existe o no tienes permiso para verlo")
        return redirect('perfil')

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
@login_requerido(roles_permitidos=[1, 2])
def admin_muebles(request):
    search = request.GET.get('search', '')
    oferta_filter = request.GET.get('oferta', '')
    proveedor_filter = request.GET.get('proveedor', '')

    muebles = Mueble.objects.all().order_by('-id')

    if search:
        try:
            mueble_id = int(search)
            muebles = muebles.filter(id=mueble_id)
        except ValueError:
            muebles = muebles.filter(
                Q(nombre__icontains=search) |
                Q(descripcion__icontains=search)
            )

    if oferta_filter:
        if oferta_filter == '1':
            muebles = [mueble for mueble in muebles if mueble.en_oferta]
        elif oferta_filter == '0':
            muebles = [mueble for mueble in muebles if not mueble.en_oferta]

    if proveedor_filter:
        muebles = muebles.filter(proveedor__id=proveedor_filter)

    # Paginación
    paginator = Paginator(muebles, 10)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    proveedores = Proveedor.objects.all().select_related('usuario')

    context = {
        'muebles': page_obj,
        'page_obj': page_obj,
        'proveedores': proveedores,
        'search': search,
        'oferta_filter': oferta_filter,
        'proveedor_filter': proveedor_filter,
        'is_paginated': page_obj.has_other_pages(),
    }

    return render(request, 'muebles/admin/muebles.html', context)

# views.py
@login_requerido(roles_permitidos=[1, 2])
def crear_mueble(request):
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            descripcion = request.POST.get('descripcion')
            precio_diario = request.POST.get('precio_diario')
            proveedor_id = request.POST.get('proveedor')
            descuento = request.POST.get('descuento', 0)
            fecha_fin_descuento = request.POST.get('fecha_fin_descuento')
            imagen = request.FILES.get('imagen')

            if not all([nombre, precio_diario, proveedor_id]):
                messages.error(request, 'Todos los campos obligatorios deben ser completados.')
                return redirect('admin_muebles')

            proveedor = Proveedor.objects.get(id=proveedor_id)

            mueble = Mueble(
                nombre=nombre,
                descripcion=descripcion,
                precio_diario=precio_diario,
                proveedor=proveedor,
                descuento=descuento if descuento else 0,
                fecha_fin_descuento=fecha_fin_descuento if fecha_fin_descuento else None,
                imagen=imagen
            )
            mueble.save()

            messages.success(request, f'Mueble "{nombre}" creado exitosamente!')
            return redirect('admin_muebles')

        except Exception as e:
            messages.error(request, f'Error al crear el mueble: {str(e)}')
            return redirect('admin_muebles')

    return redirect('admin_muebles')

@login_requerido(roles_permitidos=[1, 2])
def editar_mueble(request, id):
    try:
        mueble = Mueble.objects.get(id=id)

        if request.method == 'POST':
            nombre = request.POST.get('nombre')
            descripcion = request.POST.get('descripcion')
            precio_diario = request.POST.get('precio_diario')
            proveedor_id = request.POST.get('proveedor')
            descuento = request.POST.get('descuento', 0)
            fecha_fin_descuento = request.POST.get('fecha_fin_descuento')
            imagen = request.FILES.get('imagen')

            if not all([nombre, precio_diario]):
                messages.error(request, 'Nombre y precio diario son campos obligatorios.')
                return redirect('admin_muebles')

            mueble.nombre = nombre
            mueble.descripcion = descripcion
            mueble.precio_diario = precio_diario
            mueble.descuento = descuento if descuento else 0
            mueble.fecha_fin_descuento = fecha_fin_descuento if fecha_fin_descuento else None

            if proveedor_id:
                mueble.proveedor = Proveedor.objects.get(id=proveedor_id)

            if imagen:
                mueble.imagen = imagen

            try:
                mueble.save()
                messages.success(request, f'Mueble "{mueble.nombre}" actualizado exitosamente!')
                return redirect('admin_muebles')
            except Exception as e:
                messages.error(request, f'Error al actualizar el mueble: {str(e)}')
                return redirect('admin_muebles')

    except Mueble.DoesNotExist:
        messages.error(request, 'El mueble que intentas editar no existe.')
        return redirect('admin_muebles')

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
    # Obtener parámetros de búsqueda/filtro
    search_query = request.GET.get('search', '')
    rol_filter = request.GET.get('rol', '')
    estado_filter = request.GET.get('estado', '')

    # Filtrar usuarios
    usuarios = Usuario.objects.all().order_by('-date_joined')

    if search_query:
        try:
            # Intentar buscar por ID
            usuario_id = int(search_query)
            usuarios = usuarios.filter(id=usuario_id)
        except ValueError:
            # Si no es un ID válido, buscar por nombre o email
            usuarios = usuarios.filter(
                Q(nombre__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(username__icontains=search_query)
            )
    if rol_filter:
        usuarios = usuarios.filter(rol=rol_filter)

    if estado_filter:
        usuarios = usuarios.filter(estado=estado_filter)

    # Preparar información adicional para cada usuario
    usuarios_info = []
    for usuario in usuarios:
        try:
            proveedor = usuario.proveedor
            tipo_proveedor = {
                'es_proveedor': True,
                'nombre_empresa': proveedor.nombre_empresa,
                'telefono': proveedor.telefono
            }
        except Proveedor.DoesNotExist:
            tipo_proveedor = {
                'es_proveedor': False,
                'nombre_empresa': None,
                'telefono': None
            }

        usuarios_info.append({
            'usuario': usuario,
            'tipo_proveedor': tipo_proveedor
        })

    # Paginación
    paginator = Paginator(usuarios_info, 10)  # 10 items por página
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'usuarios_info': page_obj,
        'roles': Usuario.ROLES,
        'estados': Usuario.ESTADO,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'search_query': search_query,
        'rol_filter': rol_filter,
        'estado_filter': estado_filter
    }

    return render(request, 'muebles/admin/usuarios.html', context)


@login_requerido(roles_permitidos=[1])
def crear_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Crear y guardar el usuario primero
                    usuario = Usuario(
                        nombre=form.cleaned_data['nombre'],
                        email=form.cleaned_data['email'],
                        username=form.cleaned_data['email'],
                        direccion=form.cleaned_data.get('direccion', ''),
                        rol=form.cleaned_data['rol'],
                        estado=form.cleaned_data['estado'],
                        foto=form.cleaned_data.get('foto')
                    )
                    usuario.set_password(form.cleaned_data['password'])
                    usuario.save()  # ¡IMPORTANTE! Guardar primero el usuario

                    # 2. Crear el carrito
                    Carrito.objects.create(usuario=usuario)

                    # 3. Crear propietario solo si se especificó segmento
                    segmento = form.cleaned_data.get('segmento')
                    if segmento:
                        # Asegurarse de que el usuario tiene ID (está guardado)
                        if not usuario.pk:
                            raise ValueError("El usuario no tiene ID asignado")
                            
                        Proveedor.objects.create(
                            usuario=usuario,
                            segmento=segmento,
                            nombre_empresa=form.cleaned_data.get('nombre_empresa', ''),
                            telefono=form.cleaned_data.get('telefono', '')
                        )

                    messages.success(request, 'Usuario creado exitosamente!')
                    return redirect('admin_usuarios')

            except IntegrityError:
                messages.error(request, 'El correo electrónico ya está registrado.')
            except Exception as e:
                messages.error(request, f'Error al crear el usuario: {str(e)}')
                # Para depuración
                import traceback
                print(traceback.format_exc())
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UsuarioForm()

    return render(request, 'muebles/admin/usuarios.html', {
        'form': form,
        'roles': Usuario.ROLES,
        'estados': Usuario.ESTADO,
        'modo': 'crear'
    })

@login_requerido(roles_permitidos=[1])
def editar_usuario(request, id):
    try:
        usuario = Usuario.objects.get(id=id)

        if request.method == 'POST':
            form = UsuarioForm(request.POST, request.FILES, instance=usuario)

            if form.is_valid():
                # Mostrar los datos del formulario para debug
                print("Formulario válido")
                print("Datos del formulario:", form.cleaned_data)  # Imprime todos los datos limpiados del formulario

                try:
                    # Usamos form.save(commit=False) para no guardar inmediatamente
                    usuario = form.save(commit=False)

                    # Verificamos si se ha proporcionado una nueva contraseña
                    nueva_password = form.cleaned_data.get('password')
                    print(f"Nueva contraseña proporcionada: {nueva_password}")  # Imprime la nueva contraseña (si se proporciona)

                    if nueva_password:  # Solo si se proporciona una nueva contraseña
                        usuario.set_password(nueva_password)
                        print("La contraseña se ha actualizado.")
                    else:
                        # Si no hay nueva contraseña, no tocamos la contraseña
                        # Se mantiene la contraseña actual (sin modificación)
                        print("La contraseña no se proporcionó, se mantiene la misma.")

                    # Guardar el usuario sin cambiar la contraseña si no se proporciona una nueva
                    usuario.save()

                    # Si es el mismo usuario logueado, actualizar la sesión
                    if 'logueo' in request.session and request.session['logueo']['id'] == usuario.id:
                        request.session['logueo'] = {
                            "id": usuario.id,
                            "nombre": usuario.nombre,
                            "email": usuario.email,
                            "rol": usuario.rol,
                            "nombre_rol": usuario.get_rol_display(),
                            "foto": usuario.foto.url if usuario.foto else None
                        }
                        request.session.modified = True

                    messages.success(request, 'Usuario actualizado exitosamente!')
                    return redirect('admin_usuarios')
                except Exception as e:
                    print(f"Error al guardar el usuario: {str(e)}")  # Imprime el error
                    messages.error(request, f'Error al actualizar el usuario: {str(e)}')
                    return redirect('admin_usuarios')
        else:
            form = UsuarioForm(instance=usuario)

        return render(request, 'muebles/admin/usuarios.html', {
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
    # Obtener parámetros de búsqueda/filtro
    search = request.GET.get('search', '')
    estado = request.GET.get('estado', '')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')

    # Obtener todos los pedidos ordenados por fecha descendente
    pedidos = Pedido.objects.all().order_by('-fecha')

    # Aplicar filtros
    if search:
        try:
            # Intentar buscar por ID de pedido
            pedido_id = int(search)
            pedidos = pedidos.filter(id=pedido_id)
        except ValueError:
            # Si no es un ID válido, buscar por nombre de usuario
            pedidos = pedidos.filter(
                Q(usuario__nombre__icontains=search) |
                Q(usuario__email__icontains=search)
            )

    if estado:
        pedidos = pedidos.filter(estado=estado)

    if fecha_inicio:
        pedidos = pedidos.filter(fecha__gte=fecha_inicio)

    if fecha_fin:
        pedidos = pedidos.filter(fecha__lte=fecha_fin)

    # Paginación
    paginator = Paginator(pedidos, 10)  # 10 pedidos por página
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'muebles/admin/pedidos/pedidos.html', {
        'pedidos': page_obj,
        'estados_pedido': Pedido.ESTADOS,
        'search': search,
        'estado_selected': estado,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'is_paginated': paginator.num_pages > 1,
    })

@login_requerido(roles_permitidos=[1])
def detalle_pedido(request, id):
    pedido = get_object_or_404(Pedido, id=id)
    detalles = DetallePedido.objects.filter(pedido=pedido)

    return render(request, 'muebles/admin/pedidos/detalles_pedidos.html', {
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

# views.py
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
    # Obtener parámetros de filtrado
    busqueda = request.GET.get('q', '')
    estado_seleccionado = request.GET.get('estado', '')
    usuario_seleccionado = request.GET.get('usuario', '')

    # Obtener lista de usuarios que han hecho preguntas
    usuarios = Usuario.objects.filter(pregunta__isnull=False).distinct().order_by('id')

    # Aplicar filtros
    preguntas = Pregunta.objects.all().order_by('-fecha')

    if busqueda:
        try:
            # Intentar buscar por ID si la búsqueda es un número
            id_busqueda = int(busqueda)
            preguntas = preguntas.filter(id=id_busqueda)
        except ValueError:
            # Si no es número, buscar en texto de pregunta y respuestas
            preguntas = preguntas.filter(
                Q(pregunta__icontains=busqueda) |
                Q(respuestas__respuesta__icontains=busqueda)
            ).distinct()

    if estado_seleccionado:
        preguntas = preguntas.filter(estado=estado_seleccionado)

    if usuario_seleccionado:
        preguntas = preguntas.filter(usuario__id=usuario_seleccionado)

    # Paginación
    paginator = Paginator(preguntas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'preguntas': page_obj,
        'usuarios': usuarios,
        'busqueda': busqueda,
        'estado_seleccionado': estado_seleccionado,
        'usuario_seleccionado': usuario_seleccionado,
    }

    return render(request, 'muebles/admin/preguntas/lista_preguntas.html', context)

@login_requerido(roles_permitidos=[1])
def responder_pregunta(request, pregunta_id):
    # Obtener el usuario desde la sesión personalizada
    logueo = request.session.get("logueo")
    if not logueo:
        messages.error(request, 'Debes iniciar sesión para responder preguntas.')
        return redirect('login')

    try:
        usuario = Usuario.objects.get(id=logueo["id"])
    except Usuario.DoesNotExist:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('login')

    pregunta = get_object_or_404(Pregunta, id=pregunta_id)

    if request.method == 'POST':
        form = RespuestaForm(request.POST)
        if form.is_valid():
            respuesta = form.save(commit=False)
            respuesta.pregunta = pregunta
            respuesta.administrador = usuario  # Usar el usuario de tu sistema de sesiones
            respuesta.save()

            # Marcar la pregunta como respondida
            pregunta.estado = 'respondida'
            pregunta.save()

            messages.success(request, 'Respuesta enviada correctamente.')
            return redirect('admin_lista_preguntas')
    else:
        form = RespuestaForm()

    context = {
        'pregunta': pregunta,
        'form': form,
    }
    return render(request, 'muebles/admin/preguntas/responder_pregunta.html', context)

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
    # Manejar búsqueda y filtros
    search_query = request.GET.get('search', '')
    categoria_filter = request.GET.get('categoria', '')
    editar_id = request.GET.get('editar_id')

    # Ordenar por ID descendente (los más nuevos primero)
    faqs = FAQ.objects.all().order_by('-id')

    if search_query:
        try:
            id_busqueda = int(search_query)
            faqs = faqs.filter(id=id_busqueda)
        except ValueError:
            faqs = faqs.filter(
                Q(pregunta__icontains=search_query) |
                Q(respuesta__icontains=search_query)
            )

    if categoria_filter:
        faqs = faqs.filter(categoria=categoria_filter)

    # Manejar formularios
    if request.method == 'POST':
        if 'guardar' in request.POST:  # Crear nueva FAQ
            pregunta = request.POST.get('pregunta')
            respuesta = request.POST.get('respuesta')
            categoria = request.POST.get('categoria')
            activo = 'activo' in request.POST

            if not all([pregunta, respuesta, categoria]):
                messages.error(request, "Todos los campos obligatorios deben ser completados")
                return redirect('admin_faq_lista')

            try:
                FAQ.objects.create(
                    pregunta=pregunta,
                    respuesta=respuesta,
                    categoria=categoria,
                    activo=activo
                )
                messages.success(request, "FAQ creada exitosamente!")
                return redirect('admin_faq_lista')
            except Exception as e:
                messages.error(request, f"Error al crear FAQ: {str(e)}")
                return redirect('admin_faq_lista')

        elif 'faq_id' in request.POST:  # Editar FAQ existente
            try:
                faq = FAQ.objects.get(id=request.POST['faq_id'])
                faq.pregunta = request.POST.get('pregunta')
                faq.respuesta = request.POST.get('respuesta')
                faq.categoria = request.POST.get('categoria')
                faq.activo = 'activo' in request.POST
                faq.save()

                messages.success(request, "FAQ actualizada exitosamente!")
                return redirect('admin_faq_lista')
            except FAQ.DoesNotExist:
                messages.error(request, "La FAQ no existe")
            except Exception as e:
                messages.error(request, f"Error al actualizar FAQ: {str(e)}")
                return redirect('admin_faq_lista')

    # Manejar edición
    faq_editando = None
    if editar_id:
        try:
            faq_editando = FAQ.objects.get(id=editar_id)
        except FAQ.DoesNotExist:
            messages.error(request, "La FAQ no existe")

    # Paginación - importante mantener el orden
    paginator = Paginator(faqs, 10)  # 10 FAQs por página
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        # Si page no es un entero, mostrar primera página
        page_obj = paginator.page(1)
    except EmptyPage:
        # Si page está fuera de rango, mostrar última página
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'faqs': page_obj,
        'categorias': FAQ.CATEGORIAS,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'faq_editando': faq_editando,
    }

    return render(request, 'muebles/admin/faq/lista.html', context)

# ==================== ADMIN FAQ ====================

# views.py
@login_requerido(roles_permitidos=[1])
def admin_crear_faq(request):
    if request.method == 'POST':
        # Verificar que el usuario esté logueado y sea admin
        if 'logueo' not in request.session or request.session['logueo']['rol'] != 1:
            messages.error(request, 'No tienes permisos para realizar esta acción')
            return redirect('index')

        pregunta_id = request.POST.get('pregunta_id')
        try:
            pregunta = Pregunta.objects.get(id=pregunta_id, estado='respondida')
            respuesta = pregunta.respuestas.first()

            if not respuesta:
                messages.error(request, 'La pregunta no tiene respuesta')
                return redirect('admin_lista_preguntas')

            # Obtener el usuario admin desde la sesión
            admin_id = request.session['logueo']['id']
            try:
                admin = Usuario.objects.get(id=admin_id)
            except Usuario.DoesNotExist:
                messages.error(request, 'Usuario administrador no encontrado')
                return redirect('admin_lista_preguntas')

            # Crear el FAQ
            faq = FAQ.objects.create(
                pregunta=pregunta.pregunta,
                respuesta=respuesta.respuesta,
                categoria=pregunta.categoria,
                votos=0,
                activo=True
            )

            # Marcar la pregunta como publicada
            pregunta.estado = 'publicada'
            pregunta.save()

            # Registrar quién creó el FAQ (opcional)
            Respuesta.objects.create(
                pregunta=pregunta,
                administrador=admin,
                respuesta=f"Publicado como FAQ (ID: {faq.id})",
                es_faq=True
            )

            messages.success(request, f'Pregunta añadida a FAQ exitosamente en la categoría {faq.get_categoria_display()}')

        except Pregunta.DoesNotExist:
            messages.error(request, 'Pregunta no encontrada o no está respondida')
        except Exception as e:
            messages.error(request, f'Error al crear el FAQ: {str(e)}')

    return redirect('admin_faq_lista')

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

        return render(request, 'admin_faq_lista', {
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

# ==================== Rol de los Propietarios ====================

from django.core.paginator import Paginator


# views.py
@login_requerido(roles_permitidos=[2])
def propietario_inicio(request):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])

    try:
        proveedor = get_object_or_404(Proveedor, usuario=usuario)
    except Proveedor.DoesNotExist:
        messages.error(request, 'No tienes un perfil de proveedor asociado.')
        return redirect('index')  # Redirigir a una página adecuada

    total_muebles = Mueble.objects.filter(proveedor=proveedor).count()
    muebles_activos = Mueble.objects.filter(proveedor=proveedor).count()

    pedidos = Pedido.objects.filter(
        detalles__mueble__proveedor=proveedor
    ).distinct().order_by('-fecha')[:5]

    ganancias_totales = DetallePedido.objects.filter(
        mueble__proveedor=proveedor
    ).aggregate(
        total=Sum('ganancia_propietario'),
        comision=Sum('comision')
    )

    context = {
        'proveedor': proveedor,
        'total_muebles': total_muebles,
        'muebles_activos': muebles_activos,
        'pedidos_recientes': pedidos,
        'ganancias_totales': ganancias_totales['total'] or 0,
        'comision_total': ganancias_totales['comision'] or 0,
    }
    return render(request, 'muebles/proveedor/inicio.html', context)


@login_requerido(roles_permitidos=[2])
def propietario_muebles(request):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    proveedor = get_object_or_404(Proveedor, usuario=usuario)

    muebles = Mueble.objects.filter(proveedor=proveedor).annotate(
        ganancia_neta=ExpressionWrapper(
            F('precio_diario') * (100 - F('comision')) / 100,
            output_field=FloatField()
        )
    ).order_by('id')

    search = request.GET.get('search', '')
    oferta_filter = request.GET.get('oferta', '')
    hoy = timezone.now().date()

    if search:
        try:
            mueble_id = int(search)
            muebles = muebles.filter(id=mueble_id)
        except ValueError:
            muebles = muebles.filter(
                Q(nombre__icontains=search) |
                Q(descripcion__icontains=search)
            )

    if oferta_filter == '1':
        muebles = [mueble for mueble in muebles if mueble.en_oferta]
    elif oferta_filter == '0':
        muebles = [mueble for mueble in muebles if not mueble.en_oferta]

    muebles = sorted(muebles, key=lambda mueble: mueble.precio_con_descuento)

    paginator = Paginator(muebles, 10)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    query_params = []
    if search:
        query_params.append(f'search={search}')
    if oferta_filter:
        query_params.append(f'oferta={oferta_filter}')
    query_string = '&'.join(query_params)

    context = {
        'muebles': page_obj,
        'proveedor': proveedor,
        'search': search,
        'oferta_filter': oferta_filter,
        'query_string': query_string,
        'is_paginated': paginator.num_pages > 1,
    }

    return render(request, 'muebles/proveedor/muebles.html', context)

@login_requerido(roles_permitidos=[2])
def propietario_crear_mueble(request):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    proveedor = get_object_or_404(Proveedor, usuario=usuario)

    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            descripcion = request.POST.get('descripcion')
            precio_diario = request.POST.get('precio_diario')
            descuento = request.POST.get('descuento', 0)
            fecha_fin_descuento = request.POST.get('fecha_fin_descuento')
            imagen = request.FILES.get('imagen')

            if not all([nombre, precio_diario]):
                messages.error(request, 'Nombre y precio diario son campos obligatorios.')
                return redirect('propietario_muebles')

            mueble = Mueble(
                nombre=nombre,
                descripcion=descripcion,
                precio_diario=precio_diario,
                proveedor=proveedor,
                descuento=descuento if descuento else 0,
                fecha_fin_descuento=fecha_fin_descuento if fecha_fin_descuento else None,
                imagen=imagen
            )
            mueble.save()

            messages.success(request, f'Mueble "{nombre}" creado exitosamente!')
            return redirect('propietario_muebles')

        except Exception as e:
            messages.error(request, f'Error al crear el mueble: {str(e)}')
            return redirect('propietario_muebles')

    return render(request, 'muebles/proveedor/muebles.html', {
        'proveedor': proveedor,
        'hoy': timezone.now().date().isoformat(),
    })

@login_requerido(roles_permitidos=[2])
def propietario_editar_mueble(request, id):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    proveedor = get_object_or_404(Proveedor, usuario=usuario)

    mueble = get_object_or_404(Mueble, id=id, proveedor=proveedor)

    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            descripcion = request.POST.get('descripcion')
            precio_diario = request.POST.get('precio_diario')
            descuento = request.POST.get('descuento', 0)
            fecha_fin_descuento = request.POST.get('fecha_fin_descuento')
            imagen = request.FILES.get('imagen')

            if not all([nombre, precio_diario]):
                messages.error(request, 'Nombre y precio diario son campos obligatorios.')
                return redirect('propietario_editar_mueble', id=id)

            mueble.nombre = nombre
            mueble.descripcion = descripcion
            mueble.precio_diario = precio_diario
            mueble.descuento = descuento if descuento else 0
            mueble.fecha_fin_descuento = fecha_fin_descuento if fecha_fin_descuento else None

            if imagen:
                mueble.imagen = imagen

            mueble.save()
            messages.success(request, f'Mueble "{nombre}" actualizado exitosamente!')
            return redirect('propietario_muebles')

        except Exception as e:
            messages.error(request, f'Error al actualizar el mueble: {str(e)}')
            return redirect('propietario_editar_mueble', id=id)

    return render(request, 'muebles/proveedor/muebles.html', {
        'mueble': mueble,
        'proveedor': proveedor,
        'hoy': timezone.now().date().isoformat(),
    })

@login_requerido(roles_permitidos=[2])
def propietario_eliminar_mueble(request, id):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    proveedor = get_object_or_404(Proveedor, usuario=usuario)

    try:
        mueble = Mueble.objects.get(id=id, proveedor=proveedor)
        nombre = mueble.nombre
        mueble.delete()
        messages.success(request, f'Mueble "{nombre}" eliminado exitosamente!')
    except Mueble.DoesNotExist:
        messages.error(request, 'El mueble no existe o no tienes permisos para eliminarlo.')
    except Exception as e:
        messages.error(request, f'Error al eliminar el mueble: {str(e)}')

    return redirect('propietario_muebles')



# ============================================ Soporte Tencnico Rol=======================================


# views.py
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
import os
from datetime import datetime

# Decorador personalizado para verificar rol de soporte técnico

@login_requerido(roles_permitidos=[4])
def soporte_tecnico_inicio(request):
    # Estadísticas para el dashboard
    total_problemas = ReporteProblema.objects.count()
    problemas_abiertos = ReporteProblema.objects.filter(estado='abierto').count()
    problemas_en_progreso = ReporteProblema.objects.filter(estado='en_progreso').count()
    problemas_resueltos = ReporteProblema.objects.filter(estado='resuelto').count()
    
    # Problemas recientes
    problemas_recientes = ReporteProblema.objects.all().order_by('-fecha_reporte')[:5]
    
    context = {
        'total_problemas': total_problemas,
        'problemas_abiertos': problemas_abiertos,
        'problemas_en_progreso': problemas_en_progreso,
        'problemas_resueltos': problemas_resueltos,
        'problemas_recientes': problemas_recientes,
    }
    return render(request, 'muebles/soporte_tecnico/inicio.html', context)

@login_requerido(roles_permitidos=[4])
def lista_problemas(request):
    # Filtros
    estado = request.GET.get('estado', '')
    tipo_problema = request.GET.get('tipo_problema', '')
    search = request.GET.get('search', '')
    asignado_a_mi = 'asignado_a_mi' in request.GET
    
    problemas = ReporteProblema.objects.all().order_by('-fecha_reporte')
    
    if estado:
        problemas = problemas.filter(estado=estado)
    if tipo_problema:
        problemas = problemas.filter(tipo_problema_id=tipo_problema)
    if search:
        problemas = problemas.filter(
            Q(titulo__icontains=search) |
            Q(descripcion__icontains=search) |
            Q(url_relacionada__icontains=search)
        )
    if asignado_a_mi:
        problemas = problemas.filter(usuario_asignado_id=request.session['logueo']['id'])
    
    # Paginación
    paginator = Paginator(problemas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    tipos_problema = TipoProblema.objects.all()
    
    context = {
        'problemas': page_obj,
        'tipos_problema': tipos_problema,
        'estados': ReporteProblema.ESTADOS,
        'estado_seleccionado': estado,
        'tipo_seleccionado': tipo_problema,
        'search': search,
        'asignado_a_mi': asignado_a_mi,
    }
    return render(request, 'muebles/soporte_tecnico/lista_problemas.html', context)

@login_requerido(roles_permitidos=[4])
def detalle_problema(request, problema_id):
    problema = get_object_or_404(ReporteProblema, id=problema_id)
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        comentario = request.POST.get('comentario', '').strip()
        
        if accion == 'comentar':
            if comentario:
                ComentarioProblema.objects.create(
                    problema=problema,
                    usuario_id=request.session['logueo']['id'],
                    comentario=comentario
                )
                messages.success(request, 'Comentario agregado correctamente.')
            else:
                messages.error(request, 'El comentario no puede estar vacío.')
        
        elif accion == 'cambiar_estado':
            nuevo_estado = request.POST.get('nuevo_estado')
            if nuevo_estado and nuevo_estado != problema.estado:
                # Registrar el cambio
                RegistroCambio.objects.create(
                    problema=problema,
                    usuario_id=request.session['logueo']['id'],
                    campo='estado',
                    valor_anterior=problema.get_estado_display(),
                    valor_nuevo=dict(ReporteProblema.ESTADOS).get(nuevo_estado, nuevo_estado)
                )
                problema.estado = nuevo_estado
                problema.save()
                messages.success(request, f'Estado cambiado a {problema.get_estado_display()}.')
        
        elif accion == 'asignar':
            usuario_asignado_id = request.POST.get('usuario_asignado')
            if usuario_asignado_id:
                usuario_asignado = Usuario.objects.get(id=usuario_asignado_id)
                # Registrar el cambio
                RegistroCambio.objects.create(
                    problema=problema,
                    usuario_id=request.session['logueo']['id'],
                    campo='usuario_asignado',
                    valor_anterior=str(problema.usuario_asignado) if problema.usuario_asignado else 'Ninguno',
                    valor_nuevo=str(usuario_asignado)
                )
                problema.usuario_asignado = usuario_asignado
                problema.save()
                messages.success(request, f'Problema asignado a {usuario_asignado.nombre}.')
        
        elif accion == 'marcar_solucion':
            comentario_id = request.POST.get('comentario_id')
            if comentario_id:
                comentario = ComentarioProblema.objects.get(id=comentario_id)
                comentario.es_solucion = True
                comentario.save()
                
                # Registrar el cambio
                RegistroCambio.objects.create(
                    problema=problema,
                    usuario_id=request.session['logueo']['id'],
                    campo='solución',
                    valor_anterior='',
                    valor_nuevo=f'Solución marcada en comentario #{comentario.id}'
                )
                
                # Cambiar estado a resuelto
                if problema.estado != 'resuelto':
                    problema.estado = 'resuelto'
                    problema.save()
                    messages.success(request, 'Comentario marcado como solución y problema marcado como resuelto.')
                else:
                    messages.success(request, 'Comentario marcado como solución.')
        
        return redirect('detalle_problema', problema_id=problema.id)
    
    # Obtener usuarios disponibles para asignar (solo soporte técnico y administradores)
    usuarios_asignables = Usuario.objects.filter(Q(rol=1) | Q(rol=4)).order_by('nombre')
    
    context = {
        'problema': problema,
        'usuarios_asignables': usuarios_asignables,
    }
    return render(request, 'muebles/soporte_tecnico/detalle_problema.html', context)

@login_requerido
def reportar_problema_usuario(request):
    if request.method == 'POST':
        form = ReporteProblemaForm(request.POST, request.FILES)
        if form.is_valid():
            problema = form.save(commit=False)
            problema.usuario_reporte_id = request.session['logueo']['id']

            # Procesar captura de pantalla si existe
            if 'captura_pantalla' in request.FILES:
                captura = request.FILES['captura_pantalla']
                nombre_archivo = f"captura_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{captura.name}"
                problema.captura_pantalla.save(nombre_archivo, captura)

            problema.save()
            notificar_nuevo_problema(problema)
            messages.success(request, 'Problema reportado correctamente. El equipo de soporte lo revisará pronto.')
            return redirect('index')
    else:
        form = ReporteProblemaForm()

    return render(request, 'muebles/problemas/reportar_problema_usuario.html', {'form': form})

@login_requerido(roles_permitidos=[4])
def reportar_problema(request):
    if request.method == 'POST':
        form = ReporteProblemaForm(request.POST, request.FILES)
        if form.is_valid():
            problema = form.save(commit=False)
            problema.usuario_reporte_id = request.session['logueo']['id']

            # Procesar captura de pantalla si existe
            if 'captura_pantalla' in request.FILES:
                captura = request.FILES['captura_pantalla']
                nombre_archivo = f"captura_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{captura.name}"
                problema.captura_pantalla.save(nombre_archivo, captura)

            problema.save()
            notificar_nuevo_problema(problema)
            messages.success(request, 'Problema reportado correctamente. El equipo de soporte lo revisará pronto.')
            return redirect('lista_problemas')
    else:
        form = ReporteProblemaForm()

    return render(request, 'muebles/soporte_tecnico/reportar_problema.html', {'form': form})


def notificar_nuevo_problema(problema):
    # En una aplicación real, aquí podrías enviar un email o notificación
    # a los miembros del equipo de soporte técnico
    pass

@rol_requerido(roles_permitidos=[4])
def ver_codigo_fuente(request):
    # Obtener lista de archivos del proyecto
    base_dir = settings.BASE_DIR
    archivos = []
    
    # Directorios a explorar
    directorios = [
        os.path.join(base_dir, 'muebles'),
        os.path.join(base_dir, 'templates'),
    ]
    
    for directorio in directorios:
        for root, dirs, files in os.walk(directorio):
            for file in files:
                if file.endswith(('.py', '.html', '.css', '.js')):
                    ruta_relativa = os.path.relpath(os.path.join(root, file), base_dir)
                    archivos.append({
                        'nombre': file,
                        'ruta': os.path.join(root, file),
                        'ruta_relativa': ruta_relativa,
                        'tipo': 'python' if file.endswith('.py') else 
                               'html' if file.endswith('.html') else 
                               'css' if file.endswith('.css') else 'javascript'
                    })
    
    # Ordenar alfabéticamente
    archivos.sort(key=lambda x: x['nombre'])
    
    # Si se solicita ver un archivo específico
    archivo_path = request.GET.get('archivo')
    contenido = None
    
    if archivo_path and os.path.exists(archivo_path):
        try:
            with open(archivo_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
        except UnicodeDecodeError:
            with open(archivo_path, 'r', encoding='latin-1') as f:
                contenido = f.read()
        except Exception as e:
            messages.error(request, f'Error al leer el archivo: {str(e)}')
    
    context = {
        'archivos': archivos,
        'contenido': contenido,
        'archivo_actual': archivo_path,
    }
    return render(request, 'muebles/soporte_tecnico/ver_codigo_fuente.html', context)

@rol_requerido(roles_permitidos=[4])
def estadisticas_problemas(request):
    # Problemas por estado
    problemas_por_estado = ReporteProblema.objects.values('estado').annotate(
        total=Count('id'),
        porcentaje=ExpressionWrapper(
            Count('id') * 100.0 / ReporteProblema.objects.count(),
            output_field=FloatField()
        )
    ).order_by('-total')
    
    # Problemas por tipo
    problemas_por_tipo = ReporteProblema.objects.values('tipo_problema__nombre').annotate(
        total=Count('id'),
        porcentaje=ExpressionWrapper(
            Count('id') * 100.0 / ReporteProblema.objects.count(),
            output_field=FloatField()
        )
    ).order_by('-total')
    
    # Tiempo promedio de resolución
    problemas_resueltos = ReporteProblema.objects.filter(estado='resuelto')
    tiempo_promedio = problemas_resueltos.annotate(
        tiempo_resolucion=ExpressionWrapper(
            F('fecha_actualizacion') - F('fecha_reporte'),
            output_field=DurationField()
        )
    ).aggregate(
        promedio=Avg('tiempo_resolucion')
    )['promedio']
    
    # Convertir a días/horas/minutos
    if tiempo_promedio:
        dias = tiempo_promedio.days
        segundos = tiempo_promedio.seconds
        horas = segundos // 3600
        minutos = (segundos % 3600) // 60
        tiempo_promedio_str = f"{dias}d {horas}h {minutos}m"
    else:
        tiempo_promedio_str = "No hay datos suficientes"
    
    context = {
        'problemas_por_estado': problemas_por_estado,
        'problemas_por_tipo': problemas_por_tipo,
        'tiempo_promedio': tiempo_promedio_str,
    }
    return render(request, 'muebles/soporte_tecnico/estadisticas.html', context)

# ================================EXCEL===============================
import pandas as pd
from django.http import HttpResponse

@login_requerido(roles_permitidos=[2])
def exportar_excel(request):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    propietario = get_object_or_404(Proveedor, usuario=usuario)

    # Obtener todos los muebles del propietario
    muebles = Mueble.objects.filter(propietario=propietario)

    # Crear un DataFrame de pandas
    data = {
        'ID': [mueble.id for mueble in muebles],
        'Nombre': [mueble.nombre for mueble in muebles],
        'Precio Diario': [mueble.precio_diario for mueble in muebles],
        'Descuento': [mueble.descuento for mueble in muebles],
        'Comisión': [mueble.comision for mueble in muebles],  # Changed from comision_propietario to comision
        'Ganancia Propietario': [mueble.precio_final_propietario for mueble in muebles],
    }

    df = pd.DataFrame(data)

    # Crear una respuesta HTTP con el archivo Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=muebles.xlsx'

    df.to_excel(response, index=False)
    return response

@login_requerido(roles_permitidos=[2])
def eliminar_todo(request):
    logueo = request.session.get("logueo")
    usuario = Usuario.objects.get(id=logueo["id"])
    propietario = get_object_or_404(Proveedor, usuario=usuario)

    if request.method == 'POST':
        # Actualizar todos los muebles del propietario para restablecer ganancias y comisiones
        Mueble.objects.filter(propietario=propietario).update(
            precio_diario=0,  # Restablecer el precio diario a 0
            comision=0       # Restablecer la comisión a 0
        )

        messages.success(request, "Las ganancias y comisiones han sido restablecidas correctamente.")
        return redirect('propietario_inicio')

    return redirect('propietario_inicio')

