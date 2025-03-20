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

#carrito de compras
    path('agregar-al-carrito/<int:mueble_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('eliminar-del-carrito/<int:item_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('actualizar-cantidad/<int:item_id>/', views.actualizar_cantidad, name='actualizar_cantidad'),
    path('ver-carrito/', views.ver_carrito, name='ver_carrito'),

]