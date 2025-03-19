from django.contrib import admin
from django.utils.html import mark_safe
from .models import *


# Registrar el modelo Usuario con un formulario personalizado
@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    form = UsuarioForm
    list_display = ('id', 'nombre', 'email', 'direccion', 'rol', 'estado', 'ver_foto')
    search_fields = ('id', 'nombre', 'email')
    list_filter = ('rol', 'estado')  # Debe ser una lista o tupla
    list_editable = ('rol', 'estado', 'direccion')

    def ver_foto(self, obj):
        if obj.foto:
            return mark_safe(f'<img src="{obj.foto.url}" width="50" height="50" />')
        return "Sin foto"

    ver_foto.short_description = 'Foto'

# Registrar el modelo Propietario
@admin.register(Propietario)
class PropietarioAdmin(admin.ModelAdmin):
    list_display = ('id','nombre', 'telefono', 'email')
    search_fields = ('id','nombre', 'email')

# Registrar el modelo Mueble
@admin.register(Mueble)
class MuebleAdmin(admin.ModelAdmin):
    list_display = ('id','nombre', 'descripcion', 'precio_diario', 'propietario', 'ver_foto')
    search_fields = ('id','nombre', 'propietario__nombre')
    list_filter = ('propietario',)

    def ver_foto(self, obj):
        if obj.imagen:
            return mark_safe(f'<img src="{obj.imagen.url}" width="50" height="50" />')
        return "Sin foto"

    ver_foto.short_description = 'Foto'
# Registrar el modelo Renta con un formulario personalizado
@admin.register(Renta)
class RentaAdmin(admin.ModelAdmin):
    form = RentaForm
    list_display = ('id','mueble', 'fecha_inicio', 'fecha_fin', 'usuario', 'duracion_meses', 'duracion_anios')
    search_fields = ('id','mueble__nombre', 'usuario__nombre')
    list_filter = ('fecha_inicio', 'fecha_fin')
