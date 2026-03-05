from django.core.management.base import BaseCommand
from core.models import Connector, SyncTask
import time


class Command(BaseCommand):
    help = 'Fuerza la revisión y programación de conectores inmediatamente'

    def handle(self, *args, **options):
        from core.scheduler import check_and_schedule_connectors, start_scheduler, scheduler
        
        self.stdout.write(self.style.SUCCESS('🔍 Revisando conectores activos...'))
        self.stdout.write('')
        
        connectors = Connector.objects.filter(is_active=True)
        
        if not connectors.exists():
            self.stdout.write(self.style.WARNING('⚠ No hay conectores activos'))
            return
        
        self.stdout.write(f'Encontrados {connectors.count()} conector(es) activo(s):')
        for conn in connectors:
            sync_tasks = SyncTask.objects.filter(connector=conn)
            self.stdout.write(f'  • {conn.name} - {conn.get_sync_frequency_display()} - {sync_tasks.count()} tabla(s)')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('⏰ Iniciando scheduler temporal...'))
        
        try:
            # Iniciar scheduler si no está corriendo
            if scheduler is None or not scheduler.running:
                start_scheduler()
                time.sleep(1)  # Dar tiempo para inicializar
            
            # Programar conectores
            self.stdout.write(self.style.SUCCESS('📋 Revisando y programando conectores...'))
            check_and_schedule_connectors()
            
            # Pequeña pausa para asegurar que los jobs se programaron
            time.sleep(0.5)
            
            # Mostrar jobs programados
            if scheduler and scheduler.running:
                jobs = scheduler.get_jobs()
                self.stdout.write('')
                self.stdout.write(f'✓ Scheduler activo con {len(jobs)} job(s) programado(s):')
                if jobs:
                    for job in jobs:
                        next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else 'No programado'
                        self.stdout.write(f'  • [{job.id}] {job.name}')
                        self.stdout.write(f'    └─ Próxima ejecución: {next_run}')
                else:
                    self.stdout.write('  ⚠ No hay jobs programados todavía')
            else:
                self.stdout.write(self.style.WARNING('⚠ Scheduler no está corriendo'))
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✓ Conectores programados exitosamente'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
