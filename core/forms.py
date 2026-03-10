from django import forms
from .models import Connector, SyncTask, CleanupTask

class ConnectorForm(forms.ModelForm):
    class Meta:
        model = Connector
        fields = [
            'name', 'destination_type', 'sync_frequency',
            'pg_host', 'pg_port', 'pg_database', 'pg_user', 'pg_password',
            'drive_folder_url',
            's3_bucket_name', 's3_region', 's3_access_key', 's3_secret_key'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Mi Conector de Ventas'}),
            'destination_type': forms.Select(attrs={'class': 'form-control'}),
            'sync_frequency': forms.Select(attrs={'class': 'form-control'}),
            'pg_host': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'localhost'}),
            'pg_port': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '5432'}),
            'pg_database': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'nombre_base_datos'}),
            'pg_user': forms.TextInput(attrs={'class': 'form-control', 'value': 'simona_user', 'readonly': True}),
            'pg_password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••', 'autocomplete': 'new-password'}, render_value=False),
            'drive_folder_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://drive.google.com/...'}),
            's3_bucket_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'mi-bucket'}),
            's3_region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'us-east-1'}),
            's3_access_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'AKIA...'}),
            's3_secret_key': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••', 'autocomplete': 'new-password'}, render_value=False),
        }


class SyncTaskForm(forms.ModelForm):
    class Meta:
        model = SyncTask
        fields = ['table_name', 'timestamp_column']
        widgets = {
            'table_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: users'}),
            'timestamp_column': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'updated_at'}),
        }


class CleanupTaskForm(forms.ModelForm):
    class Meta:
        model = CleanupTask
        fields = [
            'name', 'pg_host', 'pg_port', 'pg_database', 'pg_user', 'pg_password',
            'table_name', 'timestamp_column',
            'retention_months', 'retention_days', 'retention_hours',
            'cleanup_frequency'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Limpieza de logs antiguos'}),
            'pg_host': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'localhost'}),
            'pg_port': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '5432'}),
            'pg_database': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'nombre_base_datos'}),
            'pg_user': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'usuario'}),
            'pg_password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
            'table_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: logs'}),
            'timestamp_column': forms.Select(attrs={'class': 'form-control'}),
            'retention_months': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '12', 'placeholder': '0'}),
            'retention_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '365', 'placeholder': '7'}),
            'retention_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '24', 'placeholder': '0'}),
            'cleanup_frequency': forms.Select(attrs={'class': 'form-control'}),
        }
