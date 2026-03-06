from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('user', 'Usuario Normal'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class Connector(models.Model):
    DESTINATION_CHOICES = [
        ('google_drive', 'Google Drive'),
        ('s3', 'Amazon S3'),
    ]
    
    SYNC_FREQUENCY_CHOICES = [
        (5, '5 minutos'),
        (15, '15 minutos'),
        (30, '30 minutos'),
        (60, '1 hora'),
        (360, '6 horas'),
        (1440, '24 horas'),
    ]
    
    # Campos comunes
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connectors')
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    sync_frequency = models.IntegerField(choices=SYNC_FREQUENCY_CHOICES, default=60, help_text='Frecuencia de sincronización en minutos')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Origen PostgreSQL
    pg_host = models.CharField(max_length=255)
    pg_port = models.IntegerField(default=5432)
    pg_database = models.CharField(max_length=100)
    pg_user = models.CharField(max_length=100, default='simona_user')
    pg_password = models.CharField(max_length=255)
    
    # Tipo de destino
    destination_type = models.CharField(max_length=20, choices=DESTINATION_CHOICES)
    
    # Google Drive
    drive_folder_url = models.URLField(blank=True, null=True)
    
    # Amazon S3
    s3_bucket_name = models.CharField(max_length=100, blank=True, null=True)
    s3_region = models.CharField(max_length=50, blank=True, null=True)
    s3_access_key = models.CharField(max_length=100, blank=True, null=True)
    s3_secret_key = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_destination_type_display()}) - {self.user.username}"


class SyncTask(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('running', 'Ejecutando'),
        ('success', 'Exitoso'),
        ('failed', 'Fallido'),
    ]
    
    connector = models.ForeignKey(Connector, on_delete=models.CASCADE, related_name='sync_tasks')
    table_name = models.CharField(max_length=100)
    timestamp_column = models.CharField(max_length=100, default='updated_at')
    last_sync_time = models.DateTimeField(null=True, blank=True)
    last_schema = models.TextField(null=True, blank=True, help_text='Lista de columnas de la última sincronización (JSON)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    records_synced = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['connector', 'table_name']
    
    def __str__(self):
        return f"{self.connector.name} - {self.table_name} ({self.get_status_display()})"


class GoogleDriveToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='google_drive_token')
    token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    token_uri = models.URLField(blank=True, null=True)
    client_id = models.CharField(max_length=500, blank=True, null=True)
    client_secret = models.CharField(max_length=500, blank=True, null=True)
    scopes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Google Drive Token - {self.user.username}"


class SyncExecution(models.Model):
    """Historial de ejecuciones de sincronización completas"""
    STATUS_CHOICES = [
        ('running', 'Ejecutando'),
        ('success', 'Exitoso'),
        ('partial', 'Parcial'),
        ('failed', 'Fallido'),
    ]
    
    TRIGGER_CHOICES = [
        ('manual', 'Manual'),
        ('automatic', 'Automático'),
    ]
    
    connector = models.ForeignKey(Connector, on_delete=models.CASCADE, related_name='sync_executions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    trigger = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default='manual')
    tables_synced = models.IntegerField(default=0)
    tables_failed = models.IntegerField(default=0)
    total_records = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.connector.name} - {self.get_status_display()} ({self.started_at.strftime('%d/%m/%Y %H:%M')})"
    
    @property
    def duration(self):
        """Duración de la ejecución"""
        if self.finished_at and self.started_at:
            delta = self.finished_at - self.started_at
            seconds = int(delta.total_seconds())
            if seconds < 60:
                return f"{seconds}s"
            else:
                minutes = seconds // 60
                seconds = seconds % 60
                return f"{minutes}m {seconds}s"
        return "En progreso"
