from django.test import TestCase
from django.contrib.auth.models import User
from core.models import Connector, CleanupTask


class CleanupTaskRetentionDisplayTest(TestCase):
    """Tests para verificar el formateo de políticas de retención"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
    
    def test_retention_display_only_months(self):
        """Test retención solo en meses"""
        task = CleanupTask.objects.create(
            user=self.user,
            name='Test Limpieza Meses',
            pg_host='localhost',
            pg_port=5432,
            pg_database='test_db',
            pg_user='simona_user',
            pg_password='test_password',
            table_name='test_table',
            timestamp_column='created_at',
            retention_months=3,
            retention_days=0,
            retention_hours=0,
            cleanup_frequency=1440
        )
        self.assertEqual(task.retention_display, '3 meses')
    
    def test_retention_display_only_days(self):
        """Test retención solo en días"""
        task = CleanupTask.objects.create(
            user=self.user,
            name='Test Limpieza Días',
            pg_host='localhost',
            pg_port=5432,
            pg_database='test_db',
            pg_user='simona_user',
            pg_password='test_password',
            table_name='test_table',
            timestamp_column='created_at',
            retention_months=0,
            retention_days=30,
            retention_hours=0,
            cleanup_frequency=1440
        )
        self.assertEqual(task.retention_display, '30 días')
    
    def test_retention_display_combined(self):
        """Test retención combinada (meses + días + horas)"""
        task = CleanupTask.objects.create(
            user=self.user,
            name='Test Limpieza Combinada',
            pg_host='localhost',
            pg_port=5432,
            pg_database='test_db',
            pg_user='simona_user',
            pg_password='test_password',
            table_name='test_table',
            timestamp_column='created_at',
            retention_months=2,
            retention_days=15,
            retention_hours=12,
            cleanup_frequency=1440
        )
        self.assertEqual(task.retention_display, '2 meses, 15 días, 12 horas')


class ConnectorPasswordEncryptionTest(TestCase):
    """Tests para verificar el cifrado automático de contraseñas"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
    
    def test_password_auto_encryption_on_save(self):
        """Test que las contraseñas se cifran automáticamente al guardar"""
        plaintext_password = 'mi_password_secreto_123'
        
        connector = Connector.objects.create(
            user=self.user,
            name='Test Connector',
            destination_type='google_drive',
            sync_frequency=60,
            pg_host='localhost',
            pg_port=5432,
            pg_database='test_db',
            pg_user='simona_user',
            pg_password=plaintext_password,
            drive_folder_url='https://drive.google.com/drive/folders/test123'
        )
        
        # Recargar desde DB
        connector.refresh_from_db()
        
        # Verificar que se cifró (empieza con gAAAAA)
        self.assertTrue(connector.pg_password.startswith('gAAAAA'))
        
        # Verificar que NO es texto plano
        self.assertNotEqual(connector.pg_password, plaintext_password)
        
        # Verificar que get_pg_password() devuelve el original
        self.assertEqual(connector.get_pg_password(), plaintext_password)
    
    def test_s3_secret_key_auto_encryption(self):
        """Test que las secret keys de S3 se cifran automáticamente"""
        plaintext_secret = 'aws_secret_key_xyz789'
        
        connector = Connector.objects.create(
            user=self.user,
            name='Test S3 Connector',
            destination_type='s3',
            sync_frequency=60,
            pg_host='localhost',
            pg_port=5432,
            pg_database='test_db',
            pg_user='simona_user',
            pg_password='test_pg_pass',
            s3_bucket_name='test-bucket',
            s3_region='us-east-1',
            s3_access_key='AKIA123456',
            s3_secret_key=plaintext_secret
        )
        
        # Recargar desde DB
        connector.refresh_from_db()
        
        # Verificar que se cifró
        self.assertTrue(connector.s3_secret_key.startswith('gAAAAA'))
        
        # Verificar que get_s3_secret_key() devuelve el original
        self.assertEqual(connector.get_s3_secret_key(), plaintext_secret)
    
    def test_already_encrypted_password_not_re_encrypted(self):
        """Test que contraseñas ya cifradas no se vuelven a cifrar"""
        plaintext_password = 'password_original'
        
        # Primera vez: se cifra
        connector = Connector.objects.create(
            user=self.user,
            name='Test Re-encryption',
            destination_type='google_drive',
            sync_frequency=60,
            pg_host='localhost',
            pg_port=5432,
            pg_database='test_db',
            pg_user='simona_user',
            pg_password=plaintext_password,
            drive_folder_url='https://drive.google.com/drive/folders/test456'
        )
        
        connector.refresh_from_db()
        encrypted_password = connector.pg_password
        
        # Segunda vez: actualizar otro campo (no debería re-cifrar)
        connector.name = 'Nombre Actualizado'
        connector.save()
        connector.refresh_from_db()
        
        # La contraseña cifrada debe ser la misma
        self.assertEqual(connector.pg_password, encrypted_password)
        
        # Y debe descifrar correctamente al original
        self.assertEqual(connector.get_pg_password(), plaintext_password)
