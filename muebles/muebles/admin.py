from django.contrib import admin
from django.utils.html import mark_safe
from .models import *
from .forms import *

# Registrar el modelo Usuario con un formulario personalizado
@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    form = UsuarioForm
    list_display = ('id', 'nombre', 'email', 'get_tipo_propietario', 'rol', 'estado', 'ver_foto')
    search_fields = ('id', 'nombre', 'email')
    list_filter = ('rol', 'estado')
    list_editable = ('rol', 'estado')

    def get_tipo_propietario(self, obj):
        try:
            propietario = obj.propietario
            if propietario.tipo == 'empleado':
                return "Empleado de Empresa"
            elif propietario.tipo == 'individual':
                return "Propietario Individual"
        except Propietario.DoesNotExist:
            return "-"
    get_tipo_propietario.short_description = 'Tipo Propietario'

    def ver_foto(self, obj):
        if obj.foto:
            return mark_safe(f'<img src="{obj.foto.url}" width="50" height="50" />')
        return "Sin foto"

    ver_foto.short_description = 'Foto'

# Registrar el modelo Propietario
class PropietarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo', 'nombre_empresa', 'telefono', 'fecha_registro')
    search_fields = ('usuario__nombre', 'usuario__email', 'nombre_empresa', 'telefono')
    list_filter = ('tipo',)

admin.site.register(Propietario, PropietarioAdmin)

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
    list_display = ('id','mueble', 'fecha_inicio', 'fecha_fin', 'usuario', 'duracion_meses', 'duracion_dias')
    search_fields = ('id','mueble__nombre', 'usuario__nombre')
    list_filter = ('fecha_inicio', 'fecha_fin')


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'fecha', 'estado', 'total', 'direccion_entrega')
    list_filter = ('estado', 'fecha')
    search_fields = ('usuario__nombre', 'id')
    readonly_fields = ('fecha', 'total')
    list_editable = ('estado',)

@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'pedido', 'mueble', 'cantidad', 'precio_unitario', 'subtotal')
    search_fields = ('pedido__id', 'mueble__nombre')


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('pregunta', 'categoria', 'votos', 'activo')
    search_fields = ('pregunta', 'respuesta')
    list_filter = ('categoria', 'activo')
    list_editable = ('activo',)
    
    fieldsets = (
        (None, {
            'fields': ('pregunta', 'respuesta', 'categoria', 'activo')
        }),
    )

@admin.register(Actualizacion)
class ActualizacionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'fecha', 'importante')
    search_fields = ('titulo', 'contenido')
    list_filter = ('fecha', 'importante')
    list_editable = ('importante',)
    readonly_fields = ('fecha',)


# Preguntas y Respuestas
class RespuestaInline(admin.TabularInline):
    model = Respuesta
    extra = 1
    fields = ('administrador', 'respuesta', 'es_faq', 'fecha')
    readonly_fields = ('fecha',)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "administrador":
            kwargs["queryset"] = db_field.related_model.objects.filter(rol=1)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('pregunta_resumida', 'usuario', 'estado', 'fecha', 'cantidad_respuestas')
    list_filter = ('estado', 'fecha')
    search_fields = ('pregunta', 'usuario__nombre')
    inlines = [RespuestaInline]
    actions = ['marcar_como_respondidas', 'marcar_como_faq']
    
    def pregunta_resumida(self, obj):
        return obj.pregunta[:50] + '...' if len(obj.pregunta) > 50 else obj.pregunta
    pregunta_resumida.short_description = 'Pregunta'
    
    def cantidad_respuestas(self, obj):
        return obj.respuestas.count()
    cantidad_respuestas.short_description = 'Respuestas'
    
    def marcar_como_respondidas(self, request, queryset):
        updated = queryset.update(estado='respondida')
        self.message_user(request, f"{updated} preguntas marcadas como respondidas")
    marcar_como_respondidas.short_description = "Marcar como respondidas"
    
    def marcar_como_faq(self, request, queryset):
        updated = queryset.update(estado='publicada')
        self.message_user(request, f"{updated} preguntas marcadas como FAQ")
    marcar_como_faq.short_description = "Marcar como FAQ"

@admin.register(Respuesta)
class RespuestaAdmin(admin.ModelAdmin):
    list_display = ('id', 'pregunta_resumida', 'administrador', 'fecha', 'es_faq')
    list_filter = ('es_faq', 'fecha')
    search_fields = ('respuesta', 'pregunta__pregunta')
    readonly_fields = ('fecha',)
    
    def pregunta_resumida(self, obj):
        return obj.pregunta.pregunta[:50] + '...' if len(obj.pregunta.pregunta) > 50 else obj.pregunta.pregunta
    pregunta_resumida.short_description = 'Pregunta'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "administrador":
            kwargs["queryset"] = db_field.related_model.objects.filter(rol=1)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
