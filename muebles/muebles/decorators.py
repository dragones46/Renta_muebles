from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from functools import wraps
from .models import Usuario
from django.contrib import messages


def rol_requerido(roles_permitidos):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            logueo = request.session.get("logueo", False)
            if not logueo:
                return redirect('login')

            user = Usuario.objects.get(pk=logueo["id"])

            if user.rol not in roles_permitidos:
                return HttpResponseForbidden("No tienes permiso para acceder a esta página")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def login_requerido(roles_permitidos=None, redirect_url='index', mensaje_no_autorizado="No tienes permiso para acceder a esta página"):
    """
    Decorador que verifica:
    1. Si el usuario está logueado
    2. Si el usuario existe en la base de datos
    3. Si tiene los roles requeridos (si se especifican)
    
    Args:
        roles_permitidos (list, optional): Lista de roles permitidos. Si es None, solo verifica login.
        redirect_url (str): URL a redirigir cuando no tiene permisos.
        mensaje_no_autorizado (str): Mensaje a mostrar cuando no tiene permisos.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Verificar sesión activa
            logueo = request.session.get("logueo", False)
            if not logueo:
                messages.warning(request, "Debes iniciar sesión para acceder a esta página")
                request.session['next_url'] = request.path
                return redirect('login')
            
            try:
                # Verificar que el usuario exista
                user = Usuario.objects.get(pk=logueo["id"])
            except Usuario.DoesNotExist:
                del request.session['logueo']
                messages.error(request, "Tu sesión ha expirado o el usuario ya no existe")
                return redirect('login')
            
            # Verificar roles si se especificaron
            if roles_permitidos is not None and user.rol not in roles_permitidos:
                messages.error(request, mensaje_no_autorizado)
                return redirect(redirect_url)
            
            # Si pasa todas las validaciones
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    
    # Permite usar el decorador con o sin parámetros
    if callable(roles_permitidos):
        # Si se usa como @login_requerido (sin paréntesis)
        temp_func = roles_permitidos
        roles_permitidos = None
        return decorator(temp_func)
    
    return decorator

