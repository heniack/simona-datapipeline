from django.db import models
from django.contrib.auth.models import User
from .encryption import encrypt_password, decrypt_password

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
    pg_password = models.CharField(max_length=500)  # Aumentado para almacenar cifrado
    
    # Tipo de destino
    destination_type = models.CharField(max_length=20, choices=DESTINATION_CHOICES)
    
    # Google Drive
    drive_folder_url = models.URLField(blank=True, null=True)
    
    # Amazon S3
    s3_bucket_name = models.CharField(max_length=100, blank=True, null=True)
    s3_region = models.CharField(max_length=50, blank=True, null=True)
    s3_access_key = models.CharField(max_length=100, blank=True, null=True)
    s3_secret_key = models.CharField(max_length=500, blank=True, null=True)  # Aumentado para almacenar cifrado
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        """Cifrar contraseñas antes de guardar"""
        # Solo cifrar si la contraseña cambió (no está ya cifrada)
        if self.pg_password and not self.pg_password.startswith('gAAAAA'):
            self.pg_password = encrypt_password(self.pg_password)
        if self.s3_secret_key and not self.s3_secret_key.startswith('gAAAAA'):
            self.s3_secret_key = encrypt_password(self.s3_secret_key)
        super().save(*args, **kwargs)
    
    def get_pg_password(self):
        """Obtener contraseña descifrada"""
        return decrypt_password(self.pg_password)
    
    def get_s3_secret_key(self):
        """Obtener secret key descifrada"""
        return decrypt_password(self.s3_secret_key)
    
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


class CleanupTask(models.Model):
    """Tarea de limpieza automática de datos antiguos"""
    FREQUENCY_CHOICES = [
        (60, '1 hora'),
        (360, '6 horas'),
        (720, '12 horas'),
        (1440, '24 horas'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cleanup_tasks')
    name = models.CharField(max_length=100, help_text='Nombre descriptivo de la limpieza')
    
    # Conexión PostgreSQL
    pg_host = models.CharField(max_length=255)
    pg_port = models.IntegerField(default=5432)
    pg_database = models.CharField(max_length=100)
    pg_user = models.CharField(max_length=100)
    pg_password = models.CharField(max_length=500)  # Aumentado para almacenar cifrado
    
    # Configuración de limpieza
    table_name = models.CharField(max_length=100)
    timestamp_column = models.CharField(max_length=100, help_text='Campo timestamp para evaluar antigüedad')
    
    # Retención
    retention_months = models.IntegerField(default=0, help_text='Meses de retención (0-12)')
    retention_days = models.IntegerField(default=7, help_text='Días de retención (0-365)')
    retention_hours = models.IntegerField(default=0, help_text='Horas de retención (0-24)')
    
    # Frecuencia de ejecución
    cleanup_frequency = models.IntegerField(choices=FREQUENCY_CHOICES, default=1440, help_text='Frecuencia de limpieza en minutos')
    
    # Estado
    is_active = models.BooleanField(default=True)
    last_cleanup_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        """Cifrar contraseña antes de guardar"""
        if self.pg_password and not self.pg_password.startswith('gAAAAA'):
            self.pg_password = encrypt_password(self.pg_password)
        super().save(*args, **kwargs)
    
    def get_pg_password(self):
        """Obtener contraseña descifrada"""
        return decrypt_password(self.pg_password)
    
    def __str__(self):
        return f"{self.name} - {self.table_name}"
    
    @property
    def retention_display(self):
        """Muestra la retención en formato legible"""
        parts = []
        if self.retention_months > 0:
            parts.append(f"{self.retention_months} {'mes' if self.retention_months == 1 else 'meses'}")
        if self.retention_days > 0:
            parts.append(f"{self.retention_days} {'día' if self.retention_days == 1 else 'días'}")
        if self.retention_hours > 0:
            parts.append(f"{self.retention_hours} {'hora' if self.retention_hours == 1 else 'horas'}")
        return ', '.join(parts) if parts else '0 retención'


class CleanupExecution(models.Model):
    """Historial de ejecuciones de limpieza"""
    STATUS_CHOICES = [
        ('running', 'Ejecutando'),
        ('success', 'Exitoso'),
        ('failed', 'Fallido'),
    ]
    
    cleanup_task = models.ForeignKey(CleanupTask, on_delete=models.CASCADE, related_name='executions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    rows_deleted = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.cleanup_task.name} - {self.rows_deleted} filas eliminadas ({self.started_at.strftime('%d/%m/%Y %H:%M')})"
    
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
