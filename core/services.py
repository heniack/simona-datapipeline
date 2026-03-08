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
        import json
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # PRIMERO: Obtener el schema actual de la tabla
            cursor.execute(f"SELECT * FROM {sync_task.table_name} LIMIT 0")
            current_columns = [desc[0] for desc in cursor.description]
            
            # SEGUNDO: Comparar con el schema anterior ANTES de hacer el query
            schema_changed = False
            force_full_sync = False
            
            if sync_task.last_schema:
                previous_columns = json.loads(sync_task.last_schema)
                if current_columns != previous_columns:
                    schema_changed = True
                    force_full_sync = True
                    print(f"🔄 SCHEMA CAMBIÓ:")
                    print(f"   Anterior: {previous_columns}")
                    print(f"   Actual: {current_columns}")
                    print(f"   → Forzando FULL SYNC para que todos los registros tengan las nuevas columnas")
            
            # TERCERO: Construir query según corresponda
            if sync_task.last_sync_time and not force_full_sync:
                # Sync incremental normal
                last_sync_naive = sync_task.last_sync_time
                if django_timezone.is_aware(last_sync_naive):
                    last_sync_naive = django_timezone.make_naive(last_sync_naive, timezone=django_timezone.get_current_timezone())
                
                print(f"DEBUG: Sincronización incremental. Last sync: {last_sync_naive}")
                
                query = f"""
                    SELECT * FROM {sync_task.table_name}
                    WHERE {sync_task.timestamp_column} > %s
                    ORDER BY {sync_task.timestamp_column}
                """
                cursor.execute(query, (last_sync_naive,))
            else:
                if force_full_sync:
                    print(f"DEBUG: FULL SYNC por cambio de schema")
                else:
                    print(f"DEBUG: Primera sincronización - trayendo todos los datos")
                # Full sync
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
            
            return columns, rows, max_timestamp, schema_changed
            
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
        """Obtiene las credenciales OAuth del usuario y las refresca si están expiradas"""
        from .models import GoogleDriveToken
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        
        token_obj = GoogleDriveToken.objects.get(user=self.user)
        
        credentials = Credentials(
            token=token_obj.token,
            refresh_token=token_obj.refresh_token,
            token_uri=token_obj.token_uri,
            client_id=token_obj.client_id,
            client_secret=token_obj.client_secret,
            scopes=token_obj.scopes.split(',') if token_obj.scopes else []
        )
        
        # Si el token está expirado, refrescarlo automáticamente
        if credentials.expired and credentials.refresh_token:
            print("DEBUG: Token expirado, refrescando...")
            credentials.refresh(Request())
            
            # Guardar el token actualizado
            token_obj.token = credentials.token
            token_obj.save()
            print("DEBUG: Token refrescado y guardado")
        
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
    
    def upload_csv(self, csv_content, database_name, table_name, schema_changed=False):
        """Sube o actualiza archivo CSV en Google Drive"""
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
        import io
        import csv
        
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
        
        if files and schema_changed:
            # SCHEMA CAMBIÓ: Renombrar archivo viejo y crear uno nuevo con todos los datos
            file_id = files[0]['id']
            
            from datetime import datetime
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            old_filename = f"{table_name}_old_{timestamp_str}.csv"
            
            # Renombrar archivo existente
            service.files().update(
                fileId=file_id,
                body={'name': old_filename},
                fields='id, name'
            ).execute()
            print(f"📦 Archivo renombrado a: {old_filename} (schema viejo preservado)")
            
            # Crear archivo nuevo con todos los datos y schema actualizado
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
            print(f"✨ Archivo nuevo creado con schema actualizado: {filename}")
            
        elif files:
            # Archivo existe y schema NO cambió: hacer append
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
            
            # Actualizar archivo existente (append)
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
            print("📝 Archivo actualizado (append)")
            
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
            print("📄 Archivo nuevo creado")
        
        return file


class S3Uploader:
    """Maneja la subida de archivos CSV a Amazon S3"""
    
    def __init__(self, connector):
        self.connector = connector
    
    def get_s3_client(self):
        """Crea cliente S3 con las credenciales del connector"""
        import boto3
        
        return boto3.client(
            's3',
            aws_access_key_id=self.connector.s3_access_key,
            aws_secret_access_key=self.connector.s3_secret_key,
            region_name=self.connector.s3_region
        )
    
    def upload_csv(self, csv_content, database_name, table_name, schema_changed=False):
        """Sube o actualiza archivo CSV en S3 con estructura carpetas/nombre_db/nombre_tabla/archivo.csv"""
        import io
        from datetime import datetime
        
        s3_client = self.get_s3_client()
        bucket_name = self.connector.s3_bucket_name
        
        # Estructura de carpetas: nombre_bd/nombre_tabla/tabla.csv
        filename = f"{table_name}.csv"
        s3_key = f"{database_name}/{table_name}/{filename}"
        
        # Verificar si existe el archivo
        try:
            response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            file_exists = True
        except:
            file_exists = False
        
        if file_exists and schema_changed:
            # SCHEMA CAMBIÓ: Renombrar archivo viejo y crear uno nuevo
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            old_filename = f"{table_name}_old_{timestamp_str}.csv"
            old_s3_key = f"{database_name}/{table_name}/{old_filename}"
            
            # Copiar archivo actual a nombre old
            s3_client.copy_object(
                Bucket=bucket_name,
                CopySource={'Bucket': bucket_name, 'Key': s3_key},
                Key=old_s3_key
            )
            print(f"📦 Archivo S3 renombrado a: {old_filename} (schema viejo preservado)")
            
            # Subir archivo nuevo con todos los datos y schema actualizado
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=csv_content.encode('utf-8'),
                ContentType='text/csv'
            )
            print(f"✨ Archivo S3 nuevo creado con schema actualizado: {filename}")
            
        elif file_exists:
            # Archivo existe y schema NO cambió: hacer append
            # Descargar contenido actual
            response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
            existing_content = response['Body'].read().decode('utf-8')
            
            # Separar el nuevo contenido (sin header)
            new_rows = '\n'.join(csv_content.split('\n')[1:])  # Skip header
            
            # Combinar contenido
            combined_content = existing_content.rstrip('\n') + '\n' + new_rows
            
            # Subir contenido combinado
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=combined_content.encode('utf-8'),
                ContentType='text/csv'
            )
            print("📝 Archivo S3 actualizado (append)")
            
        else:
            # Archivo no existe: crear nuevo
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=csv_content.encode('utf-8'),
                ContentType='text/csv'
            )
            print("📄 Archivo S3 nuevo creado")
        
        # Generar URL del archivo (pre-signed URL válida por 1 hora)
        file_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': s3_key},
            ExpiresIn=3600
        )
        
        return {'webViewLink': file_url, 's3_key': s3_key}


class SyncOrchestrator:
    """Orquesta el proceso completo de sincronización"""
    
    def __init__(self, sync_task):
        self.sync_task = sync_task
        self.connector = sync_task.connector
    
    def execute(self):
        """Ejecuta la sincronización completa"""
        from .models import SyncTask
        from django.utils import timezone as django_timezone
        import json
        
        try:
            # Actualizar estado a running
            self.sync_task.status = 'running'
            self.sync_task.save()
            
            # 1. Extraer datos de PostgreSQL
            pg_sync = PostgreSQLSync(self.connector)
            columns, rows, max_timestamp, schema_changed = pg_sync.extract_data(self.sync_task)
            
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
                    self.sync_task.table_name,
                    schema_changed=schema_changed
                )
                file_url = result.get('webViewLink', '')
            elif self.connector.destination_type == 's3':
                uploader = S3Uploader(self.connector)
                result = uploader.upload_csv(
                    csv_content,
                    self.connector.pg_database,
                    self.sync_task.table_name,
                    schema_changed=schema_changed
                )
                file_url = result.get('webViewLink', '')
            else:
                raise ValueError(f"Tipo de destino no soportado: {self.connector.destination_type}")
            
            # 4. Asegurar que max_timestamp sea timezone-aware antes de guardar
            if max_timestamp and not django_timezone.is_aware(max_timestamp):
                max_timestamp = django_timezone.make_aware(max_timestamp)
            
            # Agregar 1 microsegundo para evitar traer los mismos datos
            if max_timestamp:
                from datetime import timedelta
                max_timestamp = max_timestamp + timedelta(microseconds=1)
            
            print(f"DEBUG: Guardando last_sync_time como: {max_timestamp}")
            
            # 5. Actualizar SyncTask (incluir schema actual)
            self.sync_task.status = 'success'
            self.sync_task.records_synced = len(rows)
            self.sync_task.last_sync_time = max_timestamp
            self.sync_task.last_schema = json.dumps(columns)  # Guardar schema actual
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


class CleanupOrchestrator:
    """Orquestador de limpieza automática de datos antiguos"""
    
    def __init__(self, cleanup_task):
        from .models import CleanupTask
        self.cleanup_task = cleanup_task
    
    def get_connection(self):
        """Conecta al PostgreSQL"""
        return psycopg2.connect(
            host=self.cleanup_task.pg_host,
            port=self.cleanup_task.pg_port,
            database=self.cleanup_task.pg_database,
            user=self.cleanup_task.pg_user,
            password=self.cleanup_task.pg_password
        )
    
    @staticmethod
    def get_timestamp_columns(host, port, database, user, password, table_name):
        """Obtiene solo las columnas de tipo timestamp/datetime de una tabla"""
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' 
                AND table_name = %s
                AND data_type IN ('timestamp without time zone', 'timestamp with time zone', 'date')
                ORDER BY ordinal_position;
            """, (table_name,))
            
            columns = [{'name': row[0], 'type': row[1]} for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return columns
        except Exception as e:
            print(f"Error obteniendo columnas timestamp: {e}")
            return []
    
    def execute(self):
        """Ejecuta la limpieza eliminando registros antiguos"""
        from .models import CleanupExecution
        from django.utils import timezone as django_timezone
        
        # Crear registro de ejecución
        execution = CleanupExecution.objects.create(
            cleanup_task=self.cleanup_task,
            status='running'
        )
        
        try:
            # 1. Calcular fecha límite
            from datetime import timedelta
            now = django_timezone.now()
            retention_delta = timedelta(
                days=self.cleanup_task.retention_months * 30 + self.cleanup_task.retention_days,
                hours=self.cleanup_task.retention_hours
            )
            cutoff_date = now - retention_delta
            
            print(f"🧹 Ejecutando limpieza: {self.cleanup_task.name}")
            print(f"   Tabla: {self.cleanup_task.table_name}")
            print(f"   Campo: {self.cleanup_task.timestamp_column}")
            print(f"   Retención: {self.cleanup_task.retention_display}")
            print(f"   Fecha límite: {cutoff_date}")
            
            # 2. Conectar y ejecutar DELETE
            conn = self.get_connection()
            cursor = conn.cursor()
            
            delete_query = f"""
                DELETE FROM {self.cleanup_task.table_name}
                WHERE {self.cleanup_task.timestamp_column} < %s
            """
            
            cursor.execute(delete_query, (cutoff_date,))
            rows_deleted = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Limpieza exitosa: {rows_deleted} filas eliminadas")
            
            # 3. Actualizar ejecución
            execution.status = 'success'
            execution.rows_deleted = rows_deleted
            execution.finished_at = django_timezone.now()
            execution.save()
            
            # 4. Actualizar tarea
            self.cleanup_task.last_cleanup_at = django_timezone.now()
            self.cleanup_task.save()
            
            return {
                'status': 'success',
                'rows_deleted': rows_deleted
            }
            
        except Exception as e:
            print(f"❌ Error en limpieza: {e}")
            
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.finished_at = django_timezone.now()
            execution.save()
            
            return {
                'status': 'failed',
                'error': str(e)
            }
