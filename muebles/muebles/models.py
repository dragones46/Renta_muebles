from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django import forms
from django.utils import timezone
from .authentication import CustomUserManager
import os
from django.contrib.auth.models import AbstractUser, AbstractBaseUser, BaseUserManager
from django.db.models.signals import post_save
from django.dispatch import receiver
import qrcode
import uuid
from io import BytesIO
from django.core.files import File
import json
import qrcode
from django.core.files.base import ContentFile
from django.conf import settings
from datetime import date


class Usuario(AbstractUser):
    nombre = models.CharField(max_length=100, blank=False, null=False)
    email = models.EmailField(unique=True, blank=False, null=False)
    direccion = models.CharField(max_length=200, blank=False, null=False)
    password = models.CharField(max_length=100, blank=False, null=False)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    
    # Tipos de documento
    TIPO_DOCUMENTO = (
        ('CC', 'Cédula de Ciudadanía'),
        ('NIT', 'NIT de Empresa'),
    )
    tipo_documento = models.CharField(max_length=3, choices=TIPO_DOCUMENTO, default='CC')
    numero_documento = models.CharField(max_length=20, blank=True, null=True)

    ROLES = (
        (1, "Administrador"),
        (2, "Proveedor"),  # Changed from Propietario to Proveedor
        (3, "Cliente"),
        (4, "Soporte Técnico"),
    )
    rol = models.IntegerField(choices=ROLES, default=3)

    ESTADO = (
        (1, "Activo"),
        (2, "Bloqueado"),
    )
    estado = models.IntegerField(choices=ESTADO, default=1)

    TIPO_PERSONA = (
        ('natural', 'Persona Natural'),
        ('juridica', 'Persona Jurídica'),
    )
    tipo_persona = models.CharField(max_length=10, choices=TIPO_PERSONA, default='natural')
    foto = models.ImageField(upload_to='usuarios/', null=True, blank=True, default='usuarios/default.png')
    token_recuperar = models.CharField(max_length=254, default="", blank=True, null=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='usuario_groups',
        blank=True
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='usuario_permissions',
        blank=True
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre']

    def __str__(self):
        return self.nombre

class Proveedor(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='proveedor', null=True, blank=True)
    nombre_empresa = models.CharField(max_length=100, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    fecha_registro = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"{self.nombre_empresa or self.usuario.nombre} (Proveedor)"


    
class Mueble(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio_diario = models.IntegerField(default=0)
    imagen = models.ImageField(upload_to='muebles/')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE)
    descuento = models.IntegerField(default=0)  # Porcentaje de descuento (0-100)
    fecha_inicio_descuento = models.DateField(null=True, blank=True)
    fecha_fin_descuento = models.DateField(null=True, blank=True)
    comision = models.IntegerField(default=10,verbose_name="Comisión de proveedor  (%)")

    @property
    def en_oferta(self):
        hoy = timezone.now().date()
        return (
            self.descuento > 0 and
            (self.fecha_inicio_descuento is None or self.fecha_inicio_descuento <= hoy) and
            (self.fecha_fin_descuento is None or self.fecha_fin_descuento >= hoy)
        )
    
    @property
    def precio_con_descuento(self):
        if self.en_oferta:
            return int(self.precio_diario * (100 - self.descuento) / 100)
        return self.precio_diario

    @property
    def precio_final_propietario(self):
        return self.precio_con_descuento * (100 - self.comision) / 100
       
    def __str__(self):
        return self.nombre
    
    def get_propietario_display(self):
        """Devuelve el nombre del propietario o empresa según corresponda"""
        if self.propietario.tipo == 'individual':
            return self.propietario.usuario.nombre
        elif self.propietario.tipo == 'empleado' and self.propietario.nombre_empresa:
            return self.propietario.nombre_empresa
        return self.propietario.usuario.nombre  # Por defecto el nombre del usuario

    @property
    def comision_servicio(self):
        """Calcula el monto de la comisión basado en el precio diario"""
        return (self.precio_diario * self.comision / 100)
    
    @property
    def ganancia_propietario(self):
        """Calcula lo que realmente recibe el propietario"""
        return self.precio_diario - self.comision_servicio


class Renta(models.Model):
    ESTADOS = (
        ('activo', 'Activo'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    )

    mueble = models.ForeignKey('Mueble', on_delete=models.CASCADE)
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    duracion_meses = models.IntegerField(default=0)
    duracion_dias = models.IntegerField(default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='activo')
    total = models.FloatField(default=0)

    def save(self, *args, **kwargs):
        # Calcular fecha de fin si hay duración
        if self.fecha_inicio and (self.duracion_meses or self.duracion_dias):
            self.fecha_fin = self.fecha_inicio + timedelta(
                days=(self.duracion_meses * 30) + self.duracion_dias
            )

        # Calcular total con oferta o sin ella
        dias = (self.fecha_fin - self.fecha_inicio).days + 1 if self.fecha_inicio and self.fecha_fin else 0
        precio_diario = self.mueble.precio_con_descuento if self.mueble.en_oferta else self.mueble.precio_diario
        self.total = dias * precio_diario

        # Actualizar estado automáticamente
        if self.fecha_fin and self.fecha_fin < date.today():
            self.estado = 'completado'

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Renta de {self.mueble.nombre} por {self.usuario.nombre}"



class Carrito(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='carrito',
        null=True,
        blank=True
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)
    domicilio = models.CharField(max_length=255, null=True, blank=True)
    servicio_instalacion = models.BooleanField(default=False)
    COSTO_DOMICILIO = 20000
    COSTO_INSTALACION_COMPLETO = 50000
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.usuario:
            return f"Carrito de {self.usuario.username}"
        return f"Carrito de sesión {self.session_key}"

    def calcular_total(self):
        total = sum(item.subtotal() for item in self.items.all())
        if self.domicilio:
            total += self.COSTO_DOMICILIO
        if self.servicio_instalacion:
            total += self.COSTO_INSTALACION_COMPLETO
        return total

    @classmethod
    def obtener_carrito(cls, request):
        if request.session.get("logueo"):
            try:
                user_id = request.session["logueo"]["id"]
                user = Usuario.objects.get(id=user_id)
                carrito, creado = cls.objects.get_or_create(usuario=user)

                # Actualizar el conteo en la sesión si es necesario
                if creado or "carrito" not in request.session["logueo"]:
                    request.session["logueo"]["carrito"] = {
                        "id": carrito.id,
                        "items_count": carrito.items.count()
                    }
                    request.session.modified = True

            except (Usuario.DoesNotExist, KeyError):
                # Si hay algún error, crear carrito de sesión
                if not request.session.session_key:
                    request.session.create()
                session_key = request.session.session_key
                carrito, creado = cls.objects.get_or_create(session_key=session_key, usuario__isnull=True)
        else:
            # Usuario no logueado - usar carrito de sesión
            if not request.session.session_key:
                request.session.create()
            session_key = request.session.session_key
            carrito, creado = cls.objects.get_or_create(session_key=session_key, usuario__isnull=True)

        return carrito


    def migrar_a_usuario(self, usuario):
        """Migra el carrito de sesión a un usuario"""
        if self.usuario:
            return  # Ya tiene usuario
        
        # Obtener o crear carrito del usuario
        usuario_carrito, creado = Carrito.objects.get_or_create(usuario=usuario)
        
        # Migrar items
        for item in self.items.all():
            item_existente = usuario_carrito.items.filter(
                mueble=item.mueble,
                fecha_inicio=item.fecha_inicio,
                fecha_fin=item.fecha_fin
            ).first()
            
            if item_existente:
                item_existente.cantidad += item.cantidad
                item_existente.save()
                item.delete()
            else:
                item.carrito = usuario_carrito
                item.save()
        
        # Migrar servicios adicionales
        if not usuario_carrito.domicilio and self.domicilio:
            usuario_carrito.domicilio = self.domicilio
        if not usuario_carrito.servicio_instalacion and self.servicio_instalacion:
            usuario_carrito.servicio_instalacion = self.servicio_instalacion
        
        usuario_carrito.save()
        self.delete()  # Eliminar el carrito de sesión

class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    mueble = models.ForeignKey('Mueble', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    dias = models.PositiveIntegerField(default=1)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    duracion_meses = models.IntegerField(default=0)
    duracion_dias = models.IntegerField(default=0)
    def save(self, *args, **kwargs):
        # Calcular días automáticamente al guardar
        if self.fecha_inicio and self.fecha_fin:
            self.dias = (self.fecha_fin - self.fecha_inicio).days + 1
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.cantidad} x {self.mueble.nombre}"

    def subtotal(self):
        if self.mueble.en_oferta:
            return self.mueble.precio_con_descuento * self.cantidad * self.dias
        return self.mueble.precio_diario * self.cantidad * self.dias
    
class Pedido(models.Model):
    ESTADOS = (
        ('pendiente', 'Pendiente'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    )
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    total = models.IntegerField(default=0)
    direccion_entrega = models.CharField(max_length=255)
    costo_domicilio = models.IntegerField(default=0)
    comision_total = models.IntegerField(default=0)
    servicio_instalacion = models.BooleanField(default=False)
    renta = models.ForeignKey(Renta, on_delete=models.CASCADE, null=True, blank=True)  # Relación con Renta

    
    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.nombre}"

class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    mueble = models.ForeignKey(Mueble, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.IntegerField(default=0)
    subtotal = models.IntegerField(default=0)
    comision = models.IntegerField(default=0)
    ganancia_propietario = models.IntegerField(default=0)
    def __str__(self):
        return f"{self.cantidad} x {self.mueble.nombre} - ${self.subtotal}"
    

#ayuda
class FAQ(models.Model):
    CATEGORIAS = [
        ('CUENTA', 'Cuenta de usuario'),
        ('PAGOS', 'Pagos y facturación'),
        ('ENTREGAS', 'Entregas y logística'),
        ('MUEBLES', 'Productos y muebles'),
        ('SISTEMA', 'Sistema y mantenimiento'),
        ('OTROS', 'Otros'),
    ]
    
    pregunta = models.CharField(max_length=200)
    respuesta = models.TextField()
    categoria = models.CharField(max_length=50, choices=CATEGORIAS)
    votos = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['categoria', '-votos']  # Ordenamos por categoría y luego por votos descendentes
        verbose_name = 'Pregunta frecuente'
        verbose_name_plural = 'Preguntas frecuentes'
    
    def __str__(self):
        return self.pregunta
    


class Actualizacion(models.Model):
    titulo = models.CharField(max_length=100)
    contenido = models.TextField()
    fecha = models.DateTimeField(default=timezone.now)
    importante = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-fecha']
        verbose_name_plural = 'Actualizaciones'
    
    def __str__(self):
        return self.titulo



# models.py
class Pregunta(models.Model):
    CATEGORIAS = FAQ.CATEGORIAS  # Reutilizamos las mismas categorías que FAQ

    ESTADOS = (
        ('pendiente', 'Pendiente'),
        ('respondida', 'Respondida'),
        ('publicada', 'Publicada en FAQ'),
    )
    
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    pregunta = models.TextField(max_length=500)
    categoria = models.CharField(max_length=50, choices=CATEGORIAS, default='CUENTA')
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    votos = models.IntegerField(default=0)
    fecha_eliminacion = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Pregunta'
        verbose_name_plural = 'Preguntas'
    
    def __str__(self):
        return f"Pregunta de {self.usuario.nombre} - {self.get_estado_display()}"
    
    def save(self, *args, **kwargs):
        # Si la pregunta pasa a estado "respondida", establecer fecha de eliminación en 30 días
        if self.estado == 'respondida' and not self.fecha_eliminacion:
            self.fecha_eliminacion = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)
            
class Respuesta(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='respuestas')
    administrador = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    respuesta = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    es_faq = models.BooleanField(default=False)  # Si pertenece a FAQs
    
    class Meta:
        ordering = ['fecha']
    
    def __str__(self):
        return f"Respuesta a {self.pregunta.id}"

# soporte tecnico
class TipoProblema(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    prioridad = models.IntegerField(default=3)  # 1: Crítico, 2: Alto, 3: Medio, 4: Bajo
    
    def __str__(self):
        return self.nombre

class ReporteProblema(models.Model):
    ESTADOS = (
        ('abierto', 'Abierto'),
        ('en_progreso', 'En Progreso'),
        ('resuelto', 'Resuelto'),
        ('cerrado', 'Cerrado'),
        ('rechazado', 'Rechazado'),
    )
    
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    tipo_problema = models.ForeignKey(TipoProblema, on_delete=models.SET_NULL, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='abierto')
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    usuario_reporte = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='problemas_reportados')
    usuario_asignado = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='problemas_asignados')
    url_relacionada = models.CharField(max_length=255, blank=True)
    captura_pantalla = models.ImageField(upload_to='capturas_problemas/', null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha_reporte']
    
    def __str__(self):
        return f"{self.titulo} - {self.get_estado_display()}"

class ComentarioProblema(models.Model):
    problema = models.ForeignKey(ReporteProblema, on_delete=models.CASCADE, related_name='comentarios')
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    comentario = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    es_solucion = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['fecha']
    
    def __str__(self):
        return f"Comentario de {self.usuario.nombre if self.usuario else 'Anónimo'}"

class RegistroCambio(models.Model):
    problema = models.ForeignKey(ReporteProblema, on_delete=models.CASCADE, related_name='cambios')
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    campo = models.CharField(max_length=100)
    valor_anterior = models.TextField()
    valor_nuevo = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha']
    
    def __str__(self):
        return f"Cambio en {self.campo} por {self.usuario.nombre if self.usuario else 'Sistema'}"
