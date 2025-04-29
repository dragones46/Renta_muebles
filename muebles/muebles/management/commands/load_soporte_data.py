from django.core.management.base import BaseCommand
from muebles.soporte_tecnicodata import crear_tipos_problema

class Command(BaseCommand):
    help = 'Carga datos iniciales para el módulo de soporte técnico'
    
    def handle(self, *args, **options):
        crear_tipos_problema()
        self.stdout.write(self.style.SUCCESS('✅ Datos de soporte técnico cargados exitosamente!'))