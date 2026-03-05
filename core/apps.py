from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """
        Se ejecuta cuando Django termina de cargar la aplicación.
        Aquí iniciamos el scheduler para las sincronizaciones automáticas.
        """
        import os
        import sys
        
        # Solo en runserver y en el proceso principal (no en el reloader)
        is_runserver = 'runserver' in sys.argv
        is_main_process = os.environ.get('RUN_MAIN') == 'true'
        
        if is_runserver and is_main_process:
            try:
                from .scheduler import start_scheduler
                start_scheduler()
            except Exception as e:
                print(f"❌ Error al iniciar scheduler: {str(e)}")
                import traceback
                traceback.print_exc()
