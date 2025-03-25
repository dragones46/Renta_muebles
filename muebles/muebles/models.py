from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django import forms

class CustomUserManager(BaseUserManager):
    def create_user(self, email, nombre, password=None, **extra_fields):
        if not email:
            raise ValueError('El campo Email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, nombre=nombre, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombre, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')

        return self.create_user(email, nombre, password, **extra_fields)

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

class MuebleForm(forms.ModelForm):
    class Meta:
        model = Mueble
        fields = '__all__'
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'precio_diario': forms.NumberInput(attrs={'class': 'form-control'}),
            'propietario': forms.Select(attrs={'class': 'form-control'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
        }

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

class RentaForm(forms.ModelForm):
    class Meta:
        model = Renta
        fields = ['fecha_inicio', 'duracion_meses', 'duracion_dias']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'required': True}),
            'duracion_meses': forms.NumberInput(attrs={'required': True, 'min': 0}),
            'duracion_dias': forms.NumberInput(attrs={'required': True, 'min': 0}),
        }
        
class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Dejar en blanco si no quieres cambiar la contraseña"
    )
    
    class Meta:
        model = Usuario
        fields = ['nombre', 'email', 'direccion', 'rol', 'estado', 'foto', 'password']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'foto': forms.FileInput(attrs={'class': 'form-control'}),
        }


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

class DomicilioForm(forms.Form):
    domicilio = forms.CharField(
        label='Dirección de entrega',
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su dirección completa'
        }),
        required=True
    )

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