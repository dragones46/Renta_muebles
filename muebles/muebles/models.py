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


class Usuario(AbstractUser):
    nombre = models.CharField(max_length=100, blank=False, null=False)
    email = models.EmailField(unique=True, blank=False, null=False)
    direccion = models.CharField(max_length=200, blank=False, null=False)
    password = models.CharField(max_length=100, blank=False, null=False)

    ROLES = (
        (1, "Administrador"),
        (2, "Vendedor"),
        (3, "Cliente"),
    )
    rol = models.IntegerField(choices=ROLES, default=3)

    ESTADO = (
        (1, "Activo"),
        (2, "Bloqueado"),
    )
    estado = models.IntegerField(choices=ESTADO, default=1)

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

class Propietario(models.Model):
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15)
    email = models.EmailField()

    def __str__(self):
        return self.nombre

class Mueble(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio_diario = models.IntegerField(default=0)
    imagen = models.ImageField(upload_to='muebles/')
    propietario = models.ForeignKey(Propietario, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre



class Renta(models.Model):
    mueble = models.ForeignKey(Mueble, on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()  # Campo obligatorio
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    duracion_meses = models.IntegerField(default=0)  # Duración en meses
    duracion_dias = models.IntegerField(default=0)  # Duración en días

    def __str__(self):
        return f"Renta de {self.mueble.nombre} por {self.usuario.nombre}"

    def save(self, *args, **kwargs):
        # Calcular la fecha_fin en función de la duración
        if self.fecha_inicio and (self.duracion_meses or self.duracion_dias):
            self.fecha_fin = self.fecha_inicio + timedelta(
                days=(self.duracion_meses * 30) + self.duracion_dias)
        super().save(*args, **kwargs)





class Carrito(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='carrito')
    domicilio = models.CharField(max_length=255, null=True, blank=True)
    COSTO_DOMICILIO = 20000  # Constante para el costo
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Carrito de {self.usuario.nombre}"

    def calcular_total(self):
        total = sum(item.subtotal() for item in self.items.all())
        if self.domicilio:
            total += self.COSTO_DOMICILIO
        return total



class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    mueble = models.ForeignKey(Mueble, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.cantidad} x {self.mueble.nombre}"

    def subtotal(self):
        return self.cantidad * self.mueble.precio_diario
    
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
    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.nombre}"

class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    mueble = models.ForeignKey(Mueble, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.IntegerField(default=0)
    subtotal = models.IntegerField(default=0)

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
    ESTADOS = (
        ('pendiente', 'Pendiente'),
        ('respondida', 'Respondida'),
        ('publicada', 'Publicada en FAQ'),
    )
    
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    pregunta = models.TextField(max_length=500)
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


