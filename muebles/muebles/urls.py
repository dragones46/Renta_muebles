from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views as especial

from . import views

urlpatterns = [
#Zona de USUARIOS
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


#ayuda
    path('ayuda/', views.ayuda_principal, name='ayuda'),
    path('ayuda/faq/', views.faq_lista, name='faq'),
    path('ayuda/soporte/', views.soporte, name='soporte'),
    path('ayuda/actualizaciones/', views.actualizaciones, name='actualizaciones'),

#cookies
    path('politica-cookies/', views.politica_cookies, name='politica_cookies'),
    path('configurar-cookies/', views.configurar_cookies, name='configurar_cookies'),

#preguntas
    path('preguntas/', views.lista_preguntas, name='lista_preguntas'),
    path('preguntas/nueva/', views.crear_pregunta, name='crear_pregunta'),
    path('preguntas/<int:pregunta_id>/', views.detalle_pregunta, name='detalle_pregunta'),
    path('preguntas/eliminar-respondidas/', views.eliminar_preguntas_respondidas, name='eliminar_preguntas_respondidas'),
    path('eliminar-preguntas-antiguas/', views.eliminar_preguntas_antiguas, name='eliminar_preguntas_antiguas'),

# FAQ
    path('faq/', views.faq_lista, name='faq_lista'),
    path('faq/votar/<int:faq_id>/', views.votar_faq, name='votar_faq'),


#ZONA DE ADMINISTRADORES
#inicio de admin
    path('administradores/', views.admin_inicio, name='admin_inicio'),

#crud muebles
    path('administradores/muebles/', views.admin_muebles, name='admin_muebles'),
    path('administradores/muebles/crear/', views.crear_mueble, name='crear_mueble'),
    path('administradores/muebles/editar/<int:id>/', views.editar_mueble, name='editar_mueble'),
    path('administradores/muebles/eliminar/<int:id>/', views.eliminar_mueble, name='eliminar_mueble'),

#crud usuarios  
    path('administradores/usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('administradores/usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('administradores/usuarios/editar/<int:id>/', views.editar_usuario, name='editar_usuario'),
    path('administradores/usuarios/eliminar/<int:id>/', views.eliminar_usuario, name='eliminar_usuario'),

#pedidos    
    path('administradores/pedidos/', views.admin_pedidos, name='admin_pedidos'),
    path('administradores/pedidos/detalle/<int:id>/', views.detalle_pedido, name='detalle_pedido'),


# Admin preguntas
    path('administradores/preguntas/', views.admin_lista_preguntas, name='admin_lista_preguntas'),
    path('administradores/preguntas/<int:pregunta_id>/responder/', views.responder_pregunta, name='responder_pregunta'),

    
# Admin FAQ
    path('administradores/faqs/', views.admin_faq_lista, name='admin_faq_lista'),
    path('administradores/faqs/crear/', views.admin_crear_faq, name='admin_crear_faq'),
    path('administradores/faqs/editar/<int:pk>/', views.admin_editar_faq, name='admin_editar_faq'),
    path('administradores/faqs/eliminar/<int:faq_id>/', views.admin_eliminar_faq, name='admin_eliminar_faq'),

]
