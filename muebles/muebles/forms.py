from django import forms
from django.core.validators import MaxLengthValidator
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import *

#preguntas y respuestas
class PreguntaForm(forms.ModelForm):
    class Meta:
        model = Pregunta
        fields = ['pregunta', 'categoria']  # Añadir categoría
        widgets = {
            'pregunta': forms.Textarea(attrs={
                'rows': 3,
                'maxlength': 500,
                'class': 'form-control',
                'placeholder': 'Escribe tu pregunta aquí (máximo 500 caracteres)'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
    
    def clean_pregunta(self):
        pregunta = self.cleaned_data.get('pregunta')
        if len(pregunta.split()) > 100:  # Máximo 100 palabras
            raise forms.ValidationError("La pregunta no puede exceder las 100 palabras.")
        return pregunta
    
class RespuestaForm(forms.ModelForm):
    class Meta:
        model = Respuesta
        fields = ['respuesta', 'es_faq']
        widgets = {
            'respuesta': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'es_faq': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

#soporte
class SoporteForm(forms.Form):
    nombre = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Tu nombre'
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'tu@email.com'
    }))
    mensaje = forms.CharField(widget=forms.Textarea(attrs={
        'class': 'form-control',
        'placeholder': 'Describe tu problema o consulta...',
        'rows': 5
    }))

# faq
class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = '__all__'
        widgets = {
            'pregunta': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese la pregunta frecuente'
            }),
            'respuesta': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Ingrese la respuesta detallada'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-control'
            }),
            'orden': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'votos': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

#domicilio
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

#usuario
class UsuarioForm(forms.ModelForm):
    TIPO_DOCUMENTO = (
        ('CC', 'Cédula de Ciudadanía'),
        ('NIT', 'NIT de Empresa'),
    )

    TIPO_PERSONA = (
        ('natural', 'Persona Natural'),
        ('juridica', 'Persona Jurídica'),
    )

    tipo_documento = forms.ChoiceField(choices=TIPO_DOCUMENTO, required=True)
    numero_documento = forms.CharField(max_length=20, required=True)
    tipo_persona = forms.ChoiceField(choices=TIPO_PERSONA, required=True)
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Dejar en blanco para mantener la contraseña actual'
        }),
        required=False,
        help_text="Dejar en blanco para mantener la contraseña actual"
    )

    nombre_empresa = forms.CharField(
        max_length=100,
        required=False,
        label="Nombre de Empresa"
    )
    telefono = forms.CharField(
        max_length=20,
        required=False,
        label="Teléfono"
    )

    class Meta:
        model = Usuario
        fields = ['nombre', 'email', 'direccion', 'password', 'rol', 'telefono', 'estado', 'foto', 'tipo_documento', 'numero_documento', 'tipo_persona']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            try:
                proveedor = self.instance.proveedor
                self.fields['nombre_empresa'].initial = proveedor.nombre_empresa
                self.fields['telefono'].initial = proveedor.telefono
            except Proveedor.DoesNotExist:
                pass

    def save(self, commit=True):
        usuario = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:  # Solo si se proporcionó una nueva contraseña
            usuario.set_password(password)

        if commit:
            usuario.save()

        # Si es proveedor, crear el registro en Proveedor
        if usuario.rol == 2:  # Proveedor
            Proveedor.objects.update_or_create(
                usuario=usuario,
                defaults={
                    'nombre_empresa': self.cleaned_data.get('nombre_empresa', ''),
                    'telefono': self.cleaned_data.get('telefono', '')
                }
            )
        elif hasattr(usuario, 'proveedor'):
            usuario.proveedor.delete()

        return usuario


#renta
class RentaForm(forms.ModelForm):
    class Meta:
        model = Renta
        fields = ['fecha_inicio', 'fecha_fin', 'duracion_meses', 'duracion_dias']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'required': True}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'required': True}),
            'duracion_meses': forms.NumberInput(attrs={'required': True, 'min': 0}),
            'duracion_dias': forms.NumberInput(attrs={'required': True, 'min': 0}),
        }

#mueble
class MuebleForm(forms.ModelForm):
    class Meta:
        model = Mueble
        fields = '__all__'
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'precio_diario': forms.NumberInput(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
        }  

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre_empresa', 'telefono']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['nombre_empresa'].initial = self.instance.nombre_empresa
            self.fields['telefono'].initial = self.instance.telefono

    def clean_nombre_empresa(self):
        nombre_empresa = self.cleaned_data.get('nombre_empresa')
        if not nombre_empresa:
            raise forms.ValidationError("Este campo es obligatorio.")
        return nombre_empresa

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if not telefono:
            raise forms.ValidationError("Este campo es obligatorio.")
        return telefono
    
#===================================soporte tecnico=================================================

# forms.py
class ReporteProblemaForm(forms.ModelForm):
    class Meta:
        model = ReporteProblema
        fields = ['titulo', 'descripcion', 'tipo_problema', 'url_relacionada', 'captura_pantalla']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4}),
            'url_relacionada': forms.URLInput(attrs={'placeholder': 'URL donde ocurre el problema'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_problema'].queryset = TipoProblema.objects.all().order_by('nombre')
        self.fields['captura_pantalla'].required = False

class ComentarioProblemaForm(forms.ModelForm):
    class Meta:
        model = ComentarioProblema
        fields = ['comentario']
        widgets = {
            'comentario': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Escribe tu comentario aquí...'}),
        }

class CambiarEstadoForm(forms.Form):
    nuevo_estado = forms.ChoiceField(choices=ReporteProblema.ESTADOS)
    comentario = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Explicación del cambio (opcional)'})
    )

class AsignarProblemaForm(forms.Form):
    usuario_asignado = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(Q(rol=1) | Q(rol=4)).order_by('nombre'),
        label="Asignar a"
    )


# forms.py

class EditarPerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre', 'email', 'direccion', 'telefono', 'foto']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'foto': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este correo electrónico ya está en uso.")
        return email

class CambiarContrasenaForm(forms.Form):
    nueva_contrasena = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True,
        min_length=8
    )
    confirmar_contrasena = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )

    def clean(self):
        cleaned_data = super().clean()
        nueva = cleaned_data.get('nueva_contrasena')
        confirmar = cleaned_data.get('confirmar_contrasena')

        if nueva and confirmar and nueva != confirmar:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data
