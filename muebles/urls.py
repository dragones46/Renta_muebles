from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views as especial

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('muebles/', views.muebles_list, name='muebles'),
    path('contacto/', views.contacto, name='contacto'),
    path('perfil/', views.perfil, name='perfil'),
    path('login/', views.login, name='login'),
    path('registrarse/', views.registro, name='registro'),
    ]