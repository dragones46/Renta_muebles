# soporte_tecnicodata.py
from muebles.models import TipoProblema

def crear_tipos_problema():
    tipos = [
        {'nombre': 'Error de Sistema', 'descripcion': 'Problemas críticos que afectan el funcionamiento del sistema', 'prioridad': 1},
        {'nombre': 'Error de Página', 'descripcion': 'Errores en páginas específicas del sitio web', 'prioridad': 2},
        {'nombre': 'Error de Base de Datos', 'descripcion': 'Problemas relacionados con el acceso o manipulación de datos', 'prioridad': 1},
        {'nombre': 'Error de UI/UX', 'descripcion': 'Problemas con la interfaz de usuario o experiencia del usuario', 'prioridad': 3},
        {'nombre': 'Error de Seguridad', 'descripcion': 'Problemas relacionados con la seguridad del sistema', 'prioridad': 1},
        {'nombre': 'Solicitud de Mejora', 'descripcion': 'Solicitudes para mejorar funcionalidades existentes', 'prioridad': 4},
        {'nombre': 'Nueva Funcionalidad', 'descripcion': 'Solicitudes para agregar nuevas funcionalidades', 'prioridad': 4},
    ]
    
    for tipo in tipos:
        TipoProblema.objects.get_or_create(**tipo)
    
    print("Tipos de problema creados exitosamente.")