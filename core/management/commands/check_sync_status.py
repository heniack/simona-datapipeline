from django.core.management.base import BaseCommand
from core.models import SyncTask
from django.utils import timezone

class Command(BaseCommand):
    help = 'Muestra el estado de las tareas de sincronización'

    def handle(self, *args, **options):
        tasks = SyncTask.objects.all()
        
        self.stdout.write(self.style.SUCCESS('\n=== ESTADO DE SYNC TASKS ===\n'))
        
        if not tasks:
            self.stdout.write(self.style.WARNING('No hay sync tasks creadas'))
            return
        
        for task in tasks:
            self.stdout.write(f"\n📊 Conector: {task.connector.name}")
            self.stdout.write(f"   Tabla: {task.table_name}")
            self.stdout.write(f"   Estado: {task.get_status_display()}")
            self.stdout.write(f"   Registros sincronizados: {task.records_synced}")
            
            if task.last_sync_time:
                now = timezone.now()
                diff = now - task.last_sync_time
                self.stdout.write(f"   Último sync: {task.last_sync_time} (hace {diff})")
                self.stdout.write(self.style.WARNING(f"   ⚠️  Solo se traerán registros con updated_at > {task.last_sync_time}"))
            else:
                self.stdout.write(f"   Último sync: Nunca (primera sync traerá TODO)")
            
            if task.error_message:
                self.stdout.write(self.style.ERROR(f"   ❌ Error: {task.error_message}"))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Revisá que tu base de datos tenga registros con updated_at más reciente'))
        self.stdout.write(self.style.SUCCESS('   Para probar, hacé un UPDATE con updated_at = NOW() en algún registro\n'))
