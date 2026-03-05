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


def check_and_schedule_connectors():
    """
    Revisa todos los conectores activos y programa sus sincronizaciones
    según la frecuencia configurada.
    """
    from .models import Connector
    
    try:
        connectors = Connector.objects.filter(is_active=True)
        
        for connector in connectors:
            job_id = f"sync_connector_{connector.id}"
            
            # Verificar si ya existe un job para este conector
            existing_job = scheduler.get_job(job_id)
            
            if existing_job:
                # Si existe, verificar si la frecuencia cambió
                # Si cambió, eliminar el job antiguo y crear uno nuevo
                scheduler.remove_job(job_id)
                logger.info(f"Job existente removido para conector: {connector.name}")
            
            # Programar nuevo job con la frecuencia del conector
            scheduler.add_job(
                execute_sync_for_connector,
                'interval',
                minutes=connector.sync_frequency,
                id=job_id,
                args=[connector.id],
                replace_existing=True,
                max_instances=1,  # Solo una instancia a la vez
                coalesce=True,  # Si se acumulan ejecuciones, solo ejecutar una vez
                name=f"Sync: {connector.name}"
            )
            
            logger.info(f"✓ Programada sincronización para '{connector.name}' cada {connector.sync_frequency} minutos")
            
    except Exception as e:
        logger.error(f"Error al programar conectores: {str(e)}")


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
    
    # Agregar el job que revisa y programa los conectores cada 5 minutos
    scheduler.add_job(
        check_and_schedule_connectors,
        'interval',
        minutes=5,
        id='check_connectors',
        replace_existing=True,
        name='Revisar y programar conectores'
    )
    
    # Iniciar scheduler
    scheduler.start()
    
    print("✓ Scheduler iniciado correctamente")
    print("📋 Programando conectores existentes...")
    
    # Programar conectores inmediatamente al inicio
    try:
        from django.db import connection
        connection.ensure_connection()
        check_and_schedule_connectors()
        print("✓ Conectores programados")
    except Exception as e:
        print(f"⚠ Error al programar conectores iniciales: {e}")
        print("   (Se intentará nuevamente en 5 minutos)")
    
    print("⏰ Próxima revisión de conectores en 5 minutos")
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
