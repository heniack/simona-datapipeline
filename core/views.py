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
            user = form.save()
            UserProfile.objects.create(user=user, role='user')
            login(request, user)
            messages.success(request, '¡Cuenta creada exitosamente!')
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
                messages.success(request, f'¡Bienvenido {username}!')
                return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión.')
    return redirect('home')

@login_required
def create_connector(request):
    if request.method == 'POST':
        form = ConnectorForm(request.POST)
        if form.is_valid():
            connector = form.save(commit=False)
            connector.user = request.user
            connector.save()
            messages.success(request, '¡Conector creado exitosamente! Ahora selecciona las tablas a sincronizar.')
            return redirect('select_tables', connector_id=connector.id)
    else:
        form = ConnectorForm()
    return render(request, 'core/create_connector.html', {'form': form})

@login_required
def connector_list(request):
    connectors = Connector.objects.filter(user=request.user)
    return render(request, 'core/connector_list.html', {'connectors': connectors})

@login_required
def edit_connector(request, connector_id):
    connector = get_object_or_404(Connector, id=connector_id, user=request.user)
    
    if request.method == 'POST':
        form = ConnectorForm(request.POST, instance=connector)
        if form.is_valid():
            connector = form.save()
            messages.success(request, '¡Conector actualizado exitosamente!')
            
            # Si cambió la frecuencia, forzar actualización del scheduler
            from .scheduler import check_and_schedule_connectors
            try:
                check_and_schedule_connectors()
                messages.info(request, 'Frecuencia de sincronización actualizada.')
            except Exception as e:
                logger.warning(f"Error al actualizar scheduler: {str(e)}")
            
            # Redirigir a seleccionar tablas
            return redirect('select_tables', connector_id=connector.id)
    else:
        form = ConnectorForm(instance=connector)
    
    return render(request, 'core/edit_connector.html', {'form': form, 'connector': connector})

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
    return redirect('connector_list')

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
    
    if result['status'] == 'success':
        messages.success(request, f"¡Sincronización exitosa! {result['records']} registros sincronizados.")
    else:
        messages.error(request, f"Error en sincronización: {result.get('error', 'Error desconocido')}")
    
    return redirect('sync_task_list', connector_id=sync_task.connector.id)

@login_required
def sync_connector_now(request, connector_id):
    """Sincroniza todas las tareas de un conector manualmente"""
    from django.utils import timezone
    
    connector = get_object_or_404(Connector, id=connector_id, user=request.user)
    
    sync_tasks = SyncTask.objects.filter(connector=connector)
    
    if not sync_tasks.exists():
        messages.warning(request, 'No hay tareas de sincronización configuradas para este conector.')
        return redirect('connector_list')
    
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
            messages.success(request, f'¡Sincronización completada! {tables_success} tabla(s) sincronizada(s), {total_records} registro(s) en total.')
        elif tables_success > 0:
            execution.status = 'partial'
            execution.error_message = '; '.join(errors)
            messages.warning(request, f'Sincronización parcial: {tables_success} exitosa(s), {tables_failed} fallida(s).')
        else:
            execution.status = 'failed'
            execution.error_message = '; '.join(errors)
            messages.error(request, f'Error en sincronización: Todas las tablas fallaron.')
        
        execution.save()
        
    except Exception as e:
        execution.status = 'failed'
        execution.error_message = str(e)
        execution.finished_at = timezone.now()
        execution.save()
        messages.error(request, f'Error en sincronización: {str(e)}')
    
    return redirect('connector_list')

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
                    
                    messages.success(request, '¡Primera sincronización completada!')
                except Exception as e:
                    execution.status = 'failed'
                    execution.error_message = str(e)
                    execution.finished_at = timezone.now()
                    execution.save()
                    messages.warning(request, f'Tablas agregadas pero hubo un error en la sincronización: {str(e)}')
            else:
                messages.info(request, 'Las tablas seleccionadas ya estaban configuradas.')
        else:
            messages.warning(request, 'No seleccionaste ninguna tabla.')
        
        return redirect('connector_list')
    
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
