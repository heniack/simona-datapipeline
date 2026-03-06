"""
Scheduler para ejecutar sincronizaciones automáticas según la frecuencia configurada
"""
from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Instancia global del scheduler
scheduler = None


def execute_sync_for_connector(connector_id):
    """
    Ejecuta la sincronización para un conector específico.
    Esta función se ejecuta en segundo plano por APScheduler.
    """
    from .models import Connector, SyncTask, SyncExecution
    from .services import SyncOrchestrator
    from django.utils import timezone
    
    try:
        connector = Connector.objects.get(id=connector_id, is_active=True)
        logger.info(f"Ejecutando sincronización automática para: {connector.name}")
        
        # Obtener todas las sync tasks de este conector
        sync_tasks = SyncTask.objects.filter(connector=connector)
        
        if not sync_tasks.exists():
            logger.warning(f"No hay tareas de sincronización para el conector: {connector.name}")
            return
        
        # Crear registro de ejecución
        execution = SyncExecution.objects.create(
            connector=connector,
            trigger='automatic',
            status='running'
        )
        
        # Ejecutar sincronización para cada tarea
        tables_success = 0
        tables_failed = 0
        total_records = 0
        errors = []
        
        for sync_task in sync_tasks:
            try:
                logger.info(f"Sincronizando tabla: {sync_task.table_name}")
                orchestrator = SyncOrchestrator(sync_task)
                orchestrator.execute()
                tables_success += 1
                total_records += sync_task.records_synced
                logger.info(f"✓ Tabla {sync_task.table_name} sincronizada exitosamente")
            except Exception as e:
                tables_failed += 1
                errors.append(f"{sync_task.table_name}: {str(e)}")
                logger.error(f"✗ Error sincronizando tabla {sync_task.table_name}: {str(e)}")
        
        # Actualizar registro de ejecución
        execution.tables_synced = tables_success
        execution.tables_failed = tables_failed
        execution.total_records = total_records
        execution.finished_at = timezone.now()
        
        if tables_failed == 0:
            execution.status = 'success'
        elif tables_success > 0:
            execution.status = 'partial'
            execution.error_message = '; '.join(errors)
        else:
            execution.status = 'failed'
            execution.error_message = '; '.join(errors)
        
        execution.save()
        
        logger.info(f"Sincronización automática completada para: {connector.name} ({tables_success} exitosas, {tables_failed} fallidas)")
        
    except Connector.DoesNotExist:
        logger.error(f"Conector con id {connector_id} no existe o no está activo")
    except Exception as e:
        logger.error(f"Error en sincronización automática del conector {connector_id}: {str(e)}")


def schedule_connector(connector):
    """
    Programa la sincronización de un conector específico según su frecuencia.
    """
    job_id = f"sync_connector_{connector.id}"
    
    try:
        # Remover job existente si hay
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info(f"Job existente removido para: {connector.name}")
        
        # Programar nuevo job
        scheduler.add_job(
            execute_sync_for_connector,
            'interval',
            minutes=connector.sync_frequency,
            id=job_id,
            args=[connector.id],
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            name=f"Sync: {connector.name}"
        )
        
        logger.info(f"✓ Programado '{connector.name}' cada {connector.sync_frequency} minutos")
        print(f"✓ Programado '{connector.name}' cada {connector.sync_frequency} minutos")
        
    except Exception as e:
        logger.error(f"Error programando {connector.name}: {str(e)}")
        print(f"✗ Error programando {connector.name}: {str(e)}")


def schedule_all_connectors():
    """
    Programa todos los conectores activos.
    """
    from .models import Connector
    
    try:
        connectors = Connector.objects.filter(is_active=True)
        
        if not connectors.exists():
            print("⚠ No hay conectores activos para programar")
            return
        
        print(f"📋 Programando {connectors.count()} conector(es)...")
        
        for connector in connectors:
            schedule_connector(connector)
            
        print(f"✅ {connectors.count()} conector(es) programados exitosamente")
            
    except Exception as e:
        logger.error(f"Error al programar conectores: {str(e)}")
        print(f"✗ Error: {str(e)}")


def start_scheduler():
    """
    Inicia el scheduler de APScheduler.
    Se llama una sola vez cuando Django arranca.
    """
    global scheduler
    
    if scheduler is not None:
        logger.warning("El scheduler ya está corriendo")
        return
    
    print("=" * 60)
    print("🚀 INICIANDO SCHEDULER DE SINCRONIZACIÓN AUTOMÁTICA")
    print("=" * 60)
    
    # Crear scheduler con BackgroundScheduler (no bloquea el proceso principal)
    scheduler = BackgroundScheduler(timezone='America/Argentina/Buenos_Aires')
    
    # Iniciar scheduler
    scheduler.start()
    
    print("✓ Scheduler iniciado correctamente")
    print("📋 Programando conectores existentes...")
    
    # Programar conectores inmediatamente al inicio
    try:
        from django.db import connection
        connection.ensure_connection()
        schedule_all_connectors()
    except Exception as e:
        print(f"⚠ Error al programar conectores iniciales: {e}")
    
    print("=" * 60)
    
    logger.info("✓ Scheduler iniciado correctamente")


def stop_scheduler():
    """
    Detiene el scheduler de forma segura.
    """
    global scheduler
    
    if scheduler is not None:
        logger.info("Deteniendo scheduler...")
        scheduler.shutdown()
        scheduler = None
        logger.info("✓ Scheduler detenido")
