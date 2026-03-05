from django import forms
from .models import Connector, SyncTask

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
            'pg_password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
            'drive_folder_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://drive.google.com/...'}),
            's3_bucket_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'mi-bucket'}),
            's3_region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'us-east-1'}),
            's3_access_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'AKIA...'}),
            's3_secret_key': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
        }


class SyncTaskForm(forms.ModelForm):
    class Meta:
        model = SyncTask
        fields = ['table_name', 'timestamp_column']
        widgets = {
            'table_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: users'}),
            'timestamp_column': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'updated_at'}),
        }
