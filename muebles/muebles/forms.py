from django import forms
from django.core.validators import MaxLengthValidator
from django.core.exceptions import ValidationError
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
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Dejar en blanco para mantener la contraseña actual'
        }),
        required=False,
        help_text="Dejar en blanco para mantener la contraseña actual"
    )
    
    segmento = forms.ChoiceField(
        choices=Propietario.SEGMENTOS, 
        required=False,
        label="Tipo de Propietario"
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
        fields = ['nombre', 'email', 'direccion', 'password', 'rol', 'estado', 'foto']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            try:
                propietario = self.instance.propietario
                self.fields['segmento'].initial = propietario.segmento
                self.fields['nombre_empresa'].initial = propietario.nombre_empresa
                self.fields['telefono'].initial = propietario.telefono
            except Propietario.DoesNotExist:
                pass

    def clean(self):
        cleaned_data = super().clean()
        segmento = cleaned_data.get('segmento')
        nombre_empresa = cleaned_data.get('nombre_empresa')

        if segmento == 'A' and not nombre_empresa:
            raise ValidationError("El nombre de la empresa es obligatorio para proveedores.")

        return cleaned_data

    def save(self, commit=True):
        usuario = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:  # Solo si se proporcionó una nueva contraseña
            usuario.set_password(password)
        
        if commit:
            usuario.save()

        segmento = self.cleaned_data.get('segmento')
        if segmento:
            nombre_empresa = self.cleaned_data.get('nombre_empresa') if segmento == 'A' else None
            telefono = self.cleaned_data.get('telefono', '')
            
            Propietario.objects.update_or_create(
                usuario=usuario,
                defaults={
                    'segmento': segmento,
                    'nombre_empresa': nombre_empresa,
                    'telefono': telefono
                }
            )
        elif hasattr(usuario, 'propietario'):
            usuario.propietario.delete()

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
            'propietario': forms.Select(attrs={'class': 'form-control'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
        }  

class PropietarioForm(forms.ModelForm):
    class Meta:
        model = Propietario
        fields = ['segmento', 'nombre_empresa', 'telefono']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['segmento'].initial = self.instance.segmento
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