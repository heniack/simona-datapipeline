from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import os
import logging
from .models import UserProfile, Connector, GoogleDriveToken, SyncTask, SyncExecution
from .forms import ConnectorForm, SyncTaskForm
from .services import SyncOrchestrator

logger = logging.getLogger(__name__)

# Permitir HTTP en desarrollo (solo para localhost)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

# Configuración de Google OAuth
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CLIENT_SECRETS_FILE = os.path.join(settings.BASE_DIR, 'client_secret.json')

def home(request):
    return render(request, 'core/home.html')

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = request.POST.get('email', '')
            user.save()
            UserProfile.objects.create(user=user, role='user')
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'core/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)

                return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def create_connector(request):
    if request.method == 'POST':
        form = ConnectorForm(request.POST)
        if form.is_valid():
            connector = form.save(commit=False)
            connector.user = request.user
            connector.save()
            return redirect('select_tables', connector_id=connector.id)
    else:
        form = ConnectorForm()
    return render(request, 'core/create_connector.html', {'form': form})

@login_required
def google_drive_connectors(request):
    """Lista solo conectores de Google Drive"""
    connectors = Connector.objects.filter(user=request.user, destination_type='google_drive')
    return render(request, 'core/connector_list.html', {
        'connectors': connectors,
        'filter_type': 'google_drive',
        'page_title': 'Conectores de Google Drive'
    })

@login_required
def amazon_s3_connectors(request):
    """Lista solo conectores de Amazon S3"""
    connectors = Connector.objects.filter(user=request.user, destination_type='s3')
    return render(request, 'core/connector_list.html', {
        'connectors': connectors,
        'filter_type': 's3',
        'page_title': 'Conectores de Amazon S3'
    })

@login_required
def edit_connector(request, connector_id):
    connector = get_object_or_404(Connector, id=connector_id, user=request.user)
    
    if request.method == 'POST':
        form = ConnectorForm(request.POST, instance=connector)
        if form.is_valid():
            connector = form.save(commit=False)
            
            # Si el campo de password está vacío, mantener la contraseña actual
            if not request.POST.get('pg_password'):
                connector.pg_password = Connector.objects.get(id=connector_id).pg_password
            if not request.POST.get('s3_secret_key'):
                connector.s3_secret_key = Connector.objects.get(id=connector_id).s3_secret_key
            
            connector.save()
            
            # Si cambió la frecuencia, re-programar el conector
            from .scheduler import schedule_connector
            try:
                schedule_connector(connector)
            except Exception as e:
                logger.warning(f"Error al actualizar scheduler: {str(e)}")
            
            # Redirigir a seleccionar tablas
            return redirect('select_tables', connector_id=connector.id)
    else:
        form = ConnectorForm(instance=connector)
    
    return render(request, 'core/edit_connector.html', {'form': form, 'connector': connector})

@login_required
def delete_connector(request, connector_id):
    """Elimina un conector y todas sus tareas asociadas"""
    connector = get_object_or_404(Connector, id=connector_id, user=request.user)
    
    if request.method == 'POST':
        # Eliminar job del scheduler si existe
        from .scheduler import scheduler
        job_id = f"sync_connector_{connector.id}"
        try:
            if scheduler and scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
                logger.info(f"Job {job_id} eliminado del scheduler")
        except Exception as e:
            logger.warning(f"Error al eliminar job del scheduler: {str(e)}")
        
        # Django eliminará automáticamente SyncTasks y SyncExecutions por CASCADE
        destination_type = connector.destination_type
        connector.delete()
        
        # Redirigir a la vista filtrada correcta
        if destination_type == 'google_drive':
            return redirect('google_drive_connectors')
        else:
            return redirect('amazon_s3_connectors')
    
    # Si no es POST, redirigir a la vista filtrada
    if connector.destination_type == 'google_drive':
        return redirect('google_drive_connectors')
    else:
        return redirect('amazon_s3_connectors')

@login_required
def authorize_google_drive(request):
    """Inicia el flujo OAuth de Google Drive"""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='http://localhost:8000/oauth2callback'
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    request.session['state'] = state
    return redirect(authorization_url)

@login_required
def oauth2callback(request):
    """Callback de Google OAuth - guarda los tokens"""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='http://localhost:8000/oauth2callback'
    )
    
    # No validar state en desarrollo
    flow.fetch_token(code=request.GET.get('code'))
    
    credentials = flow.credentials
    
    # Guardar o actualizar token
    token, created = GoogleDriveToken.objects.update_or_create(
        user=request.user,
        defaults={
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': ','.join(credentials.scopes) if credentials.scopes else ''
        }
    )
    
    messages.success(request, '¡Google Drive conectado exitosamente!')
    return redirect('google_drive_connectors')

@login_required
def sync_task_list(request, connector_id):
    """Lista el historial de sincronizaciones de un conector"""
    connector = get_object_or_404(Connector, id=connector_id, user=request.user)
    sync_tasks = SyncTask.objects.filter(connector=connector)
    sync_executions = SyncExecution.objects.filter(connector=connector)[:20]  # Últimas 20 ejecuciones
    
    return render(request, 'core/sync_task_list.html', {
        'connector': connector,
        'sync_tasks': sync_tasks,
        'sync_executions': sync_executions
    })

@login_required
def create_sync_task(request, connector_id):
    """Crea una nueva tarea de sincronización"""
    connector = get_object_or_404(Connector, id=connector_id, user=request.user)
    
    if request.method == 'POST':
        form = SyncTaskForm(request.POST)
        if form.is_valid():
            sync_task = form.save(commit=False)
            sync_task.connector = connector
            sync_task.save()
            messages.success(request, '¡Tarea de sincronización creada!')
            return redirect('sync_task_list', connector_id=connector.id)
    else:
        form = SyncTaskForm()
    
    return render(request, 'core/create_sync_task.html', {
        'form': form,
        'connector': connector
    })

@login_required
def execute_sync(request, sync_task_id):
    """Ejecuta una tarea de sincronización"""
    sync_task = get_object_or_404(SyncTask, id=sync_task_id, connector__user=request.user)
    
    orchestrator = SyncOrchestrator(sync_task)
    result = orchestrator.execute()
    
    return redirect('sync_task_list', connector_id=sync_task.connector.id)

@login_required
def sync_connector_now(request, connector_id):
    """Sincroniza todas las tareas de un conector manualmente"""
    from django.utils import timezone
    
    connector = get_object_or_404(Connector, id=connector_id, user=request.user)
    
    sync_tasks = SyncTask.objects.filter(connector=connector)
    
    if not sync_tasks.exists():
        # Redirigir a la vista filtrada correcta
        if connector.destination_type == 'google_drive':
            return redirect('google_drive_connectors')
        else:
            return redirect('amazon_s3_connectors')
    
    # Crear registro de ejecución
    execution = SyncExecution.objects.create(
        connector=connector,
        trigger='manual',
        status='running'
    )
    
    try:
        tables_success = 0
        tables_failed = 0
        total_records = 0
        errors = []
        
        for sync_task in sync_tasks:
            try:
                orchestrator = SyncOrchestrator(sync_task)
                result = orchestrator.execute()
                tables_success += 1
                total_records += sync_task.records_synced
            except Exception as e:
                tables_failed += 1
                errors.append(f"{sync_task.table_name}: {str(e)}")
        
        # Actualizar ejecución
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
        
    except Exception as e:
        execution.status = 'failed'
        execution.error_message = str(e)
        execution.finished_at = timezone.now()
        execution.save()
    
    # Redirigir a sync_task_list del conector
    return redirect('sync_task_list', connector_id=connector.id)

@login_required
def select_tables(request, connector_id):
    """Página para seleccionar tablas a sincronizar después de crear/editar conector"""
    connector = get_object_or_404(Connector, id=connector_id, user=request.user)
    
    if request.method == 'POST':
        selected_tables = request.POST.getlist('selected_tables')
        
        if selected_tables:
            new_tables_count = 0
            for table_name in selected_tables:
                # Verificar si ya existe
                if not SyncTask.objects.filter(connector=connector, table_name=table_name).exists():
                    SyncTask.objects.create(
                        connector=connector,
                        table_name=table_name,
                        timestamp_column='updated_at',
                        status='pending'
                    )
                    new_tables_count += 1
            
            if new_tables_count > 0:
                messages.success(request, f'¡{new_tables_count} tabla(s) agregada(s) exitosamente!')
                
                # Sincronizar automáticamente y crear registro de ejecución
                from django.utils import timezone
                
                execution = SyncExecution.objects.create(
                    connector=connector,
                    trigger='manual',
                    status='running'
                )
                
                try:
                    tables_success = 0
                    tables_failed = 0
                    total_records = 0
                    
                    for sync_task in SyncTask.objects.filter(connector=connector):
                        try:
                            orchestrator = SyncOrchestrator(sync_task)
                            orchestrator.execute()
                            tables_success += 1
                            total_records += sync_task.records_synced
                        except Exception as e:
                            tables_failed += 1
                    
                    execution.tables_synced = tables_success
                    execution.tables_failed = tables_failed
                    execution.total_records = total_records
                    execution.finished_at = timezone.now()
                    execution.status = 'success' if tables_failed == 0 else 'partial'
                    execution.save()
                except Exception as e:
                    execution.status = 'failed'
                    execution.error_message = str(e)
                    execution.finished_at = timezone.now()
                    execution.save()
        
        # Redirigir a la vista filtrada correcta
        if connector.destination_type == 'google_drive':
            return redirect('google_drive_connectors')
        else:
            return redirect('amazon_s3_connectors')
    
    # Obtener tablas de la base de datos
    from .services import PostgreSQLSync
    result = PostgreSQLSync.get_tables_from_database(
        connector.pg_host,
        connector.pg_port,
        connector.pg_database,
        connector.pg_user,
        connector.pg_password
    )
    
    # Obtener tablas ya sincronizadas
    existing_tables = set(SyncTask.objects.filter(connector=connector).values_list('table_name', flat=True))
    
    return render(request, 'core/select_tables.html', {
        'connector': connector,
        'tables_result': result,
        'existing_tables': existing_tables
    })

@login_required
def get_database_tables(request):
    """Vista AJAX para obtener las tablas de una base de datos PostgreSQL"""
    from django.http import JsonResponse
    from .services import PostgreSQLSync
    
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        
        host = data.get('host')
        port = data.get('port', 5432)
        database = data.get('database')
        user = data.get('user')
        password = data.get('password')
        
        if not all([host, database, user, password]):
            return JsonResponse({'success': False, 'error': 'Faltan datos de conexión'})
        
        result = PostgreSQLSync.get_tables_from_database(host, port, database, user, password)
        return JsonResponse(result)
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


# ============================================
# CLEANUP VIEWS (Limpiezas Automáticas)
# ============================================

@login_required
def cleanup_task_list(request):
    """Lista todas las tareas de limpieza del usuario"""
    from .models import CleanupTask
    
    cleanup_tasks = CleanupTask.objects.filter(user=request.user)
    return render(request, 'core/cleanup_task_list.html', {
        'cleanup_tasks': cleanup_tasks
    })


@login_required
def create_cleanup_task(request):
    """Crea una nueva tarea de limpieza"""
    from .forms import CleanupTaskForm
    from .services import CleanupOrchestrator
    from django.http import JsonResponse
    
    if request.method == 'POST':
        # Si es AJAX, obtener columnas timestamp
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            import json
            data = json.loads(request.body)
            
            columns = CleanupOrchestrator.get_timestamp_columns(
                data.get('host'),
                data.get('port', 5432),
                data.get('database'),
                data.get('user'),
                data.get('password'),
                data.get('table_name')
            )
            
            return JsonResponse({'success': True, 'columns': columns})
        
        # Si es POST normal, crear la tarea
        form = CleanupTaskForm(request.POST)
        if form.is_valid():
            cleanup_task = form.save(commit=False)
            cleanup_task.user = request.user
            cleanup_task.save()
            
            # Programar en el scheduler
            from .scheduler import schedule_cleanup_task
            schedule_cleanup_task(cleanup_task)
            
            return redirect('cleanup_task_detail', cleanup_task_id=cleanup_task.id)
    else:
        form = CleanupTaskForm()
    
    return render(request, 'core/create_cleanup_task.html', {'form': form})


# ============================================
# SETTINGS VIEWS (Configuración)
# ============================================

@login_required
def settings_view(request):
    """Página de configuración del usuario"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        user = request.user
        error = None
        
        # Validar cambio de contraseña
        if new_password:
            if not current_password:
                error = 'Debes ingresar tu contraseña actual para cambiarla'
            elif not user.check_password(current_password):
                error = 'La contraseña actual es incorrecta'
            elif new_password != confirm_password:
                error = 'Las contraseñas nuevas no coinciden'
            elif len(new_password) < 8:
                error = 'La contraseña debe tener al menos 8 caracteres'
            else:
                user.set_password(new_password)
        
        # Actualizar username y email
        if not error:
            if username and username != user.username:
                # Verificar que no exista otro usuario con ese nombre
                from django.contrib.auth.models import User
                if User.objects.filter(username=username).exclude(id=user.id).exists():
                    error = 'Ese nombre de usuario ya está en uso'
                else:
                    user.username = username
            
            if email and email != user.email:
                user.email = email
            
            if not error:
                user.save()
                return redirect('settings')
        
        if error:
            messages.error(request, error)
    
    return render(request, 'core/settings.html', {
        'user': request.user
    })


@login_required
def help_view(request):
    """Página de ayuda"""
    return render(request, 'core/help.html')


# ============================================
# CLEANUP TASK VIEWS (Limpiezas Automáticas)
# ============================================

@login_required
def cleanup_task_detail(request, cleanup_task_id):
    """Muestra el detalle de una tarea de limpieza con historial"""
    from .models import CleanupTask, CleanupExecution
    
    cleanup_task = get_object_or_404(CleanupTask, id=cleanup_task_id, user=request.user)
    executions = CleanupExecution.objects.filter(cleanup_task=cleanup_task)[:20]
    
    return render(request, 'core/cleanup_task_detail.html', {
        'cleanup_task': cleanup_task,
        'executions': executions
    })


@login_required
def execute_cleanup_now(request, cleanup_task_id):
    """Ejecuta una limpieza manualmente"""
    from .models import CleanupTask
    from .services import CleanupOrchestrator
    
    cleanup_task = get_object_or_404(CleanupTask, id=cleanup_task_id, user=request.user)
    
    orchestrator = CleanupOrchestrator(cleanup_task)
    orchestrator.execute()
    
    return redirect('cleanup_task_detail', cleanup_task_id=cleanup_task.id)


@login_required
def delete_cleanup_task(request, cleanup_task_id):
    """Elimina una tarea de limpieza"""
    from .models import CleanupTask
    
    cleanup_task = get_object_or_404(CleanupTask, id=cleanup_task_id, user=request.user)
    
    if request.method == 'POST':
        # Remover del scheduler
        from . import scheduler
        job_id = f"cleanup_{cleanup_task.id}"
        if scheduler.scheduler and scheduler.scheduler.get_job(job_id):
            scheduler.scheduler.remove_job(job_id)
            print(f"✓ Job {job_id} removido del scheduler")
        
        cleanup_task.delete()
        return redirect('cleanup_task_list')
    
    return redirect('cleanup_task_detail', cleanup_task_id=cleanup_task.id)
