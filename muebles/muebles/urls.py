from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views as especial

from . import views

urlpatterns = [
#inicio
    path('', views.index, name='index'),

#muebles
    path('muebles/', views.muebles_list, name='muebles'),
    path('rentar/<int:mueble_id>/', views.rentar_mueble, name='rentar_mueble'),

#contacto
    path('contacto/', views.contacto, name='contacto'),

#usuario
    path('login/', views.login, name='login'),
    path('registro/', views.registro, name='registro'),
    path('logout/', views.logout, name='logout'),
    path('perfil/', views.perfil, name='perfil'),

    ]