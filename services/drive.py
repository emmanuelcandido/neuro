import os
import io
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from googleapiclient.errors import HttpError

# logger = logging.getLogger(__name__)

class DriveService:
    def __init__(self, db_service):
        self.db = db_service
        self.scopes = ['https://www.googleapis.com/auth/drive']
        self.service = None
        self.authenticate()
    
    def authenticate(self):
        # logger.info("Iniciando autenticação com Google Drive...")
        creds = None
        token_path = 'config/drive_token.json'
        
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, self.scopes)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'config/credentials.json', self.scopes)
                creds = flow.run_local_server(port=0)
            
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('drive', 'v3', credentials=creds)
        # logger.info("Autenticação com Google Drive concluída.")

    def create_course_folder(self, course_name):
        # logger.info(f"Criando pasta para o curso: {course_name}")
        # ID da pasta 'Media' no seu Drive (se existir, caso contrário, crie-a manualmente ou via API)
        # Ou procure por ela
        media_folder_id = self._get_or_create_folder('Media', None)
        cursos_folder_id = self._get_or_create_folder('Cursos', media_folder_id)
        course_folder_id = self._get_or_create_folder(course_name, cursos_folder_id)
        # logger.info(f"Pasta do curso '{course_name}' criada/encontrada com ID: {course_folder_id}")
        return course_folder_id

    def _get_or_create_folder(self, folder_name, parent_id=None):
        # logger.debug(f"Buscando/criando pasta: {folder_name} em {parent_id}")
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        response = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        folders = response.get('files', [])
        
        if folders:
            return folders[0]['id']
        else:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(body=file_metadata, fields='id').execute()
            return folder.get('id')

    def upload_file(self, file_path, folder_id, make_public=False):
        # logger.info(f"Iniciando upload de arquivo: {file_path} para pasta {folder_id}")
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        
        mime_type = self._get_mime_type(file_path)
        
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
        request = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        )
        
        # Progress bar apenas para arquivos > 2MB
        if file_size > 2 * 1024 * 1024:
            print(f"Uploading {filename}...")
            # Implementar progress bar (rich.progress)
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status and file_size > 2 * 1024 * 1024:
                print(f"Upload progress: {int(status.progress() * 100)}%")
        
        file_id = response.get('id')
        # logger.info(f"Arquivo {filename} uploaded com ID: {file_id}")
        
        if make_public:
            public_url = self.make_file_public(file_id)
            # logger.info(f"Arquivo {filename} tornado público. URL: {public_url}")
            return file_id, public_url
        
        return file_id, None

    def make_file_public(self, file_id):
        # logger.info(f"Tornando arquivo {file_id} público.")
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        
        try:
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            return self.get_direct_download_url(file_id)
        except HttpError as e:
            # logger.error(f"Erro ao tornar arquivo {file_id} público: {e}")
            return None

    def get_direct_download_url(self, file_id):
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    def _get_mime_type(self, file_path):
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type if mime_type else 'application/octet-stream'

    def upload_course_files(self, course_path, course_name):
        # logger.info(f"Iniciando upload de todos os arquivos do curso: {course_name}")
        course_folder_id = self.create_course_folder(course_name)
        if not course_folder_id:
            # logger.error(f"Não foi possível criar/encontrar pasta para o curso {course_name}")
            return False

        # Simulação de upload de arquivos
        # Aqui você percorreria os arquivos processados e faria o upload
        # Exemplo: self.upload_file(f"{course_path}/audio_completo.mp3", course_folder_id, make_public=True)
        # self.upload_file(f"{course_path}/resumo_completo.md", course_folder_id)
        # logger.info(f"Upload de arquivos do curso {course_name} concluído (simulado).")
        return True
