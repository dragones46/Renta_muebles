from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from functools import wraps
from .models import Usuario

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

def login_requerido(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        logueo = request.session.get("logueo", False)
        if not logueo:
            # Redirige al usuario a la página de login si no está logueado
            return redirect('login')
        
        # Si el usuario está logueado, permite el acceso a la vista
        return view_func(request, *args, **kwargs)
    return _wrapped_view