import re
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

from django.db.models import Q

#Para sacar totales de eventos.
from django.db.models import Sum
from django.shortcuts import render
import locale



from django.db.models import F
from collections import defaultdict

from django.utils import timezone
from datetime import timedelta

# Para tomar el from desde el settings
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
import threading

# Para que muestre más detalles de un error
import traceback

# Importamos todos los modelos de la base de datos
from django.db import IntegrityError, transaction
from django.http import JsonResponse
import json

from django.utils import timezone

#APIVIEW
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny


#PARA EL PDF
from xhtml2pdf import pisa
from django.template.loader import render_to_string
import os
import tempfile
from django.core.files import File

from django.urls import reverse


from rest_framework import viewsets

from .serializers import *
from rest_framework import viewsets


#Importar el crypt
from .crypt import *

#Importar todos los modelos de la base de datos.
from .models import *

#Validar la fecha de Nacimiento
from datetime import datetime
import uuid
from io import BytesIO

# Para restringir las vistas
from .decorators import rol_requerido

# Create your views here.

def index(request):
    muebles = Mueble.objects.all()  # Obtén todos los muebles disponibles
    return render(request, 'muebles/index.html', {'muebles': muebles})

def muebles_list(request):
    muebles = Mueble.objects.all()
    return render(request, 'muebles/mueble/muebles_list.html', {'muebles': muebles})

def contacto(request):
    return render(request, 'muebles/contacto/contacto.html')

@login_required
def perfil(request):
    return render(request, 'muebles/perfil/perfil.html')

def login(request):
    return render(request, 'muebles/perfil/login.html')

def registro(request):
    return render(request, 'muebles/perfil/registrarse.html')

