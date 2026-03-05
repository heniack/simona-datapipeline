import psycopg2
import csv
import io
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from .models import SyncTask

class PostgreSQLSync:
    def __init__(self, connector):
        self.connector = connector
        
    def get_connection(self):
        """Conecta al PostgreSQL del cliente"""
        return psycopg2.connect(
            host=self.connector.pg_host,
            port=self.connector.pg_port,
            database=self.connector.pg_database,
            user=self.connector.pg_user,
            password=self.connector.pg_password
        )
    
    @staticmethod
    def get_tables_from_database(host, port, database, user, password):
        """Obtiene la lista de tablas de una base de datos PostgreSQL que tienen columna updated_at"""
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            cursor = conn.cursor()
            
            # Query para obtener tablas que tengan la columna 'updated_at'
            cursor.execute("""
                SELECT DISTINCT t.table_name 
                FROM information_schema.tables t
                INNER JOIN information_schema.columns c 
                    ON t.table_name = c.table_name 
                    AND t.table_schema = c.table_schema
                WHERE t.table_schema = 'public' 
                AND t.table_type = 'BASE TABLE'
                AND c.column_name = 'updated_at'
                ORDER BY t.table_name;
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return {'success': True, 'tables': tables}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def extract_data(self, sync_task):
        """Extrae datos incrementales de la tabla"""
        from django.utils import timezone as django_timezone
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Construir query incremental
            if sync_task.last_sync_time:
                # Convertir a naive datetime (sin timezone) para PostgreSQL
                last_sync_naive = sync_task.last_sync_time
                if django_timezone.is_aware(last_sync_naive):
                    last_sync_naive = django_timezone.make_naive(last_sync_naive, timezone=django_timezone.get_current_timezone())
                
                print(f"DEBUG: Sincronización incremental. Last sync (aware): {sync_task.last_sync_time}")
                print(f"DEBUG: Last sync (naive para query): {last_sync_naive}")
                
                query = f"""
                    SELECT * FROM {sync_task.table_name}
                    WHERE {sync_task.timestamp_column} > %s
                    ORDER BY {sync_task.timestamp_column}
                """
                cursor.execute(query, (last_sync_naive,))
            else:
                print(f"DEBUG: Primera sincronización - trayendo todos los datos")
                # Primera sincronización: traer todo
                query = f"SELECT * FROM {sync_task.table_name}"
                cursor.execute(query)
            
            # Obtener nombres de columnas
            columns = [desc[0] for desc in cursor.description]
            
            # Obtener datos
            rows = cursor.fetchall()
            print(f"DEBUG: Se extrajeron {len(rows)} registros")
            
            # Obtener el máximo updated_at de los datos extraídos
            max_timestamp = None
            if rows:
                timestamp_col_index = columns.index(sync_task.timestamp_column)
                max_timestamp = max(row[timestamp_col_index] for row in rows)
                
                # Hacer timezone-aware si es necesario
                if max_timestamp and not django_timezone.is_aware(max_timestamp):
                    max_timestamp = django_timezone.make_aware(max_timestamp)
                
                print(f"DEBUG: Max timestamp extraído: {max_timestamp}")
            
            return columns, rows, max_timestamp
            
        finally:
            cursor.close()
            conn.close()
    
    def data_to_csv(self, columns, rows):
        """Convierte datos a CSV en memoria"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Escribir encabezados
        writer.writerow(columns)
        
        # Escribir datos
        writer.writerows(rows)
        
        output.seek(0)
        return output.getvalue()


class GoogleDriveUploader:
    def __init__(self, connector, user):
        self.connector = connector
        self.user = user
    
    def get_folder_id_from_url(self, url):
        """Extrae el ID de carpeta del URL de Google Drive"""
        # URL típica: https://drive.google.com/drive/folders/1ABC123XYZ
        # También: https://drive.google.com/drive/u/0/folders/1ABC123XYZ
        if not url:
            raise ValueError("La URL de carpeta de Google Drive no está configurada. Por favor, editá el conector y agregá la URL de la carpeta.")
        
        if '/folders/' in url:
            folder_id = url.split('/folders/')[-1].split('?')[0].split('/')[0]
            print(f"DEBUG: Folder ID extraído: {folder_id}")
            return folder_id
        
        raise ValueError(f"URL de Google Drive inválida: {url}. Debe ser del formato: https://drive.google.com/drive/folders/ID_DE_CARPETA")
        
    
    def get_credentials(self):
        """Obtiene las credenciales OAuth del usuario"""
        from .models import GoogleDriveToken
        from google.oauth2.credentials import Credentials
        
        token_obj = GoogleDriveToken.objects.get(user=self.user)
        
        credentials = Credentials(
            token=token_obj.token,
            refresh_token=token_obj.refresh_token,
            token_uri=token_obj.token_uri,
            client_id=token_obj.client_id,
            client_secret=token_obj.client_secret,
            scopes=token_obj.scopes.split(',') if token_obj.scopes else []
        )
        
        return credentials
    
    def get_or_create_folder(self, service, folder_name, parent_id=None):
        """Busca o crea una carpeta en Google Drive"""
        # Buscar si existe
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        results = service.files().list(q=query, fields='files(id, name)').execute()
        folders = results.get('files', [])
        
        if folders:
            return folders[0]['id']
        
        # Crear carpeta
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    
    def upload_csv(self, csv_content, database_name, table_name):
        """Sube o actualiza archivo CSV en Google Drive (append-only)"""
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
        import io
        
        # Obtener credenciales
        credentials = self.get_credentials()
        service = build('drive', 'v3', credentials=credentials)
        
        # Obtener carpeta base del usuario
        base_folder_id = self.get_folder_id_from_url(self.connector.drive_folder_url)
        
        # Crear estructura: carpeta_base/nombre_bd/nombre_tabla/
        db_folder_id = self.get_or_create_folder(service, database_name, base_folder_id)
        table_folder_id = self.get_or_create_folder(service, table_name, db_folder_id)
        
        # Nombre del archivo (siempre el mismo)
        filename = f"{table_name}.csv"
        
        # Buscar si ya existe el archivo
        query = f"name='{filename}' and '{table_folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields='files(id, name)').execute()
        files = results.get('files', [])
        
        if files:
            # Archivo existe: descargar contenido existente
            file_id = files[0]['id']
            request = service.files().get_media(fileId=file_id)
            
            import io
            fh = io.BytesIO()
            from googleapiclient.http import MediaIoBaseDownload
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            # Obtener contenido existente
            fh.seek(0)
            existing_content = fh.read().decode('utf-8')
            
            # Separar el nuevo contenido (sin header)
            new_lines = csv_content.split('\n')
            if len(new_lines) > 1:
                # Quitar el header del nuevo contenido
                new_data_only = '\n'.join(new_lines[1:])
                
                # Combinar: existente + nuevos datos
                combined_content = existing_content.rstrip('\n') + '\n' + new_data_only
            else:
                combined_content = existing_content
            
            # Actualizar archivo existente
            media = MediaIoBaseUpload(
                io.BytesIO(combined_content.encode('utf-8')),
                mimetype='text/csv',
                resumable=True
            )
            
            file = service.files().update(
                fileId=file_id,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
            
        else:
            # Archivo no existe: crear nuevo
            file_metadata = {
                'name': filename,
                'parents': [table_folder_id]
            }
            
            media = MediaIoBaseUpload(
                io.BytesIO(csv_content.encode('utf-8')),
                mimetype='text/csv',
                resumable=True
            )
            
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
        
        return file


class SyncOrchestrator:
    """Orquesta el proceso completo de sincronización"""
    
    def __init__(self, sync_task):
        self.sync_task = sync_task
        self.connector = sync_task.connector
    
    def execute(self):
        """Ejecuta la sincronización completa"""
        from .models import SyncTask
        from django.utils import timezone as django_timezone
        
        try:
            # Actualizar estado a running
            self.sync_task.status = 'running'
            self.sync_task.save()
            
            # 1. Extraer datos de PostgreSQL
            pg_sync = PostgreSQLSync(self.connector)
            columns, rows, max_timestamp = pg_sync.extract_data(self.sync_task)
            
            if not rows:
                self.sync_task.status = 'success'
                self.sync_task.records_synced = 0
                self.sync_task.error_message = 'No hay datos nuevos para sincronizar'
                self.sync_task.save()
                return {'status': 'success', 'message': 'No hay datos nuevos', 'records': 0}
            
            # 2. Convertir a CSV
            csv_content = pg_sync.data_to_csv(columns, rows)
            
            # 3. Subir según tipo de destino
            if self.connector.destination_type == 'google_drive':
                uploader = GoogleDriveUploader(self.connector, self.connector.user)
                result = uploader.upload_csv(
                    csv_content,
                    self.connector.pg_database,
                    self.sync_task.table_name
                )
                file_url = result.get('webViewLink', '')
            elif self.connector.destination_type == 's3':
                # TODO: Implementar S3
                raise NotImplementedError('S3 upload aún no implementado')
            
            # 4. Asegurar que max_timestamp sea timezone-aware antes de guardar
            if max_timestamp and not django_timezone.is_aware(max_timestamp):
                max_timestamp = django_timezone.make_aware(max_timestamp)
            
            # Agregar 1 microsegundo para evitar traer los mismos datos
            if max_timestamp:
                from datetime import timedelta
                max_timestamp = max_timestamp + timedelta(microseconds=1)
            
            print(f"DEBUG: Guardando last_sync_time como: {max_timestamp}")
            
            # 5. Actualizar SyncTask
            self.sync_task.status = 'success'
            self.sync_task.records_synced = len(rows)
            self.sync_task.last_sync_time = max_timestamp
            self.sync_task.error_message = None
            self.sync_task.save()
            
            return {
                'status': 'success',
                'records': len(rows),
                'file_url': file_url,
                'last_sync_time': max_timestamp
            }
            
        except Exception as e:
            # Guardar error
            self.sync_task.status = 'failed'
            self.sync_task.error_message = str(e)
            self.sync_task.save()
            
            return {
                'status': 'failed',
                'error': str(e)
            }
