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
    path('eliminar-domicilio/', views.eliminar_domicilio, name='eliminar_domicilio'),
    path('procesar-pago/', views.procesar_pago, name='procesar_pago'),

#admin
#inicio de admin
    path('administracion/', views.admin_inicio, name='admin_inicio'),

#crud muebles
    path('administracion/muebles/', views.admin_muebles, name='admin_muebles'),
    path('administracion/muebles/crear/', views.crear_mueble, name='crear_mueble'),
    path('administracion/muebles/editar/<int:id>/', views.editar_mueble, name='editar_mueble'),
    path('administracion/muebles/eliminar/<int:id>/', views.eliminar_mueble, name='eliminar_mueble'),

#crud usuarios  
    path('administracion/usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('administracion/usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('administracion/usuarios/editar/<int:id>/', views.editar_usuario, name='editar_usuario'),
    path('administracion/usuarios/eliminar/<int:id>/', views.eliminar_usuario, name='eliminar_usuario'),

#pedidos    
    path('administracion/pedidos/', views.admin_pedidos, name='admin_pedidos'),
    path('administracion/pedidos/detalle/<int:id>/', views.detalle_pedido, name='detalle_pedido'),
    
    ]