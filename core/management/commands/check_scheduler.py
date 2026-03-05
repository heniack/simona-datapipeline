from django.core.management.base import BaseCommand
from core.scheduler import scheduler


class Command(BaseCommand):
    help = 'Muestra el estado del scheduler y los jobs programados'

    def handle(self, *args, **options):
        if scheduler is None:
            self.stdout.write(self.style.ERROR('❌ El scheduler NO está corriendo'))
            self.stdout.write(self.style.WARNING('Asegúrate de iniciar el servidor con: python manage.py runserver'))
            return
        
        self.stdout.write(self.style.SUCCESS('✓ El scheduler está corriendo'))
        self.stdout.write('')
        
        jobs = scheduler.get_jobs()
        
        if not jobs:
            self.stdout.write(self.style.WARNING('⚠ No hay jobs programados'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'📋 Jobs programados: {len(jobs)}'))
        self.stdout.write('')
        
        for job in jobs:
            self.stdout.write(f'  • Job ID: {job.id}')
            self.stdout.write(f'    Nombre: {job.name}')
            self.stdout.write(f'    Próxima ejecución: {job.next_run_time}')
            self.stdout.write('')
