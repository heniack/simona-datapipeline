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
        
        # Iniciar en runserver (proceso principal) o en gunicorn
        is_runserver = 'runserver' in sys.argv
        is_main_process = os.environ.get('RUN_MAIN') == 'true'
        is_gunicorn = 'gunicorn' in sys.modules

        if (is_runserver and is_main_process) or is_gunicorn:
            try:
                from .scheduler import start_scheduler
                start_scheduler()
            except Exception as e:
                print(f"❌ Error al iniciar scheduler: {str(e)}")
                import traceback
                traceback.print_exc()

            # Crear superuser en producción si no existe
            try:
                from django.contrib.auth.models import User
                from .models import UserProfile
                if not User.objects.filter(username='administrator').exists():
                    user = User.objects.create_superuser(username='administrator', email='', password='12345678')
                    UserProfile.objects.get_or_create(user=user, defaults={'role': 'admin'})
                    print('✅ Superuser "administrator" creado')
                else:
                    print('ℹ Superuser "administrator" ya existe')
            except Exception as e:
                print(f"⚠ Error creando superuser: {e}")
