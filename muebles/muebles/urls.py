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
    
    path('agregar_direccion/', views.agregar_direccion, name='agregar_direccion'),
    path('agregar_instalacion/', views.agregar_instalacion, name='agregar_instalacion'),

    path('actualizar_direccion/', views.actualizar_direccion, name='actualizar_direccion'),
    path('actualizar_instalacion/', views.actualizar_instalacion, name='actualizar_instalacion'),

    path('eliminar-domicilio/', views.eliminar_domicilio, name='eliminar_domicilio'),
    path('eliminar-instalacion/', views.eliminar_instalacion, name='eliminar_instalacion'),
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

#problemas
    path('reportar-problema/', views.reportar_problema_usuario, name='reportar_problema_usuario'),

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

#ZONA DE PROPIETARIOS
    path('propietarios/', views.propietario_inicio, name='propietario_inicio'),
    path('propietarios/muebles/', views.propietario_muebles, name='propietario_muebles'),
    path('propietarios/muebles/crear/', views.propietario_crear_mueble, name='propietario_crear_mueble'),
    path('propietarios/muebles/editar/<int:id>/', views.propietario_editar_mueble, name='propietario_editar_mueble'),
    path('propietarios/muebles/eliminar/<int:id>/', views.propietario_eliminar_mueble, name='propietario_eliminar_mueble'),

 # Zona de Soporte Técnico
    path('soporte-tecnico/', views.soporte_tecnico_inicio, name='soporte_tecnico_inicio'),
    path('soporte-tecnico/ver-codigo-fuente/', views.ver_codigo_fuente, name='ver_codigo_fuente'),
    path('soporte-tecnico/problemas/', views.lista_problemas, name='lista_problemas'),
    path('soporte-tecnico/problemas/<int:problema_id>/', views.detalle_problema, name='detalle_problema'),
    path('soporte-tecnico/problemas/reportar/', views.reportar_problema, name='reportar_problema'),
    path('soporte-tecnico/codigo-fuente/', views.ver_codigo_fuente, name='ver_codigo_fuente'),
    path('soporte-tecnico/estadisticas/', views.estadisticas_problemas, name='estadisticas_problemas'),


 # Perfiles específicos
    path('perfil/', views.perfil, name='perfil'),
    path('perfil/admin/', views.perfil_admin, name='perfil_admin'),
    path('perfil/propietario/', views.perfil_proveedor, name='perfil_proveedor'),
    path('perfil/cliente/', views.perfil_cliente, name='perfil_cliente'),
    path('perfil/soporte/', views.perfil_soporte, name='perfil_soporte'),

# Exel
    path('propietarios/exportar-excel/', views.exportar_excel, name='exportar_excel'),
    path('propietarios/eliminar-todo/', views.eliminar_todo, name='eliminar_todo'),
]
