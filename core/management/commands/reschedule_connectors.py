from django.core.management.base import BaseCommand
from core.scheduler import scheduler, schedule_all_connectors


class Command(BaseCommand):
    help = 'Reprograma todos los conectores activos con sus frecuencias actualizadas'

    def handle(self, *args, **options):
        if scheduler is None:
            self.stdout.write(self.style.ERROR('❌ El scheduler NO está corriendo'))
            self.stdout.write(self.style.WARNING('Asegúrate de iniciar el servidor con: python manage.py runserver'))
            return
        
        self.stdout.write(self.style.SUCCESS('\n🔄 Reprogramando conectores...\n'))
        
        schedule_all_connectors()
        
        self.stdout.write(self.style.SUCCESS('\n✅ ¡Listo! Revisá con: python manage.py check_scheduler\n'))
