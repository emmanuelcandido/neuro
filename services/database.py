import sqlite3
import os
import logging
from datetime import datetime

# Configuração de logging para o DatabaseService
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, db_path="data/neurodeamon.db"):
        self.db_path = db_path
        self.conn = None
        self.connect()
        self.create_tables()

    def connect(self):
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row # Permite acessar colunas por nome
            # logger.info(f"Conectado ao banco de dados: {self.db_path}")
        except sqlite3.Error as e:
            # logger.error(f"Erro ao conectar ao banco de dados: {e}")
            raise

    def close(self):
        if self.conn:
            self.conn.close()
            # logger.info("Conexão com o banco de dados fechada.")

    def _execute_query(self, query, params=(), fetchone=False, fetchall=False, commit=False):
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            if commit:
                self.conn.commit()
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
            return cursor.lastrowid
        except sqlite3.Error as e:
            # logger.error(f"Erro ao executar query: {query} com params {params} - {e}")
            raise

    def create_tables(self):
        # logger.info("Verificando e criando tabelas do banco de dados...")
        queries = [
            """
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                source_path TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processing_stage TEXT DEFAULT 'not_started',
                total_episodes INTEGER DEFAULT 0,
                completed_episodes INTEGER DEFAULT 0,
                drive_folder_id TEXT,
                rss_generated BOOLEAN DEFAULT FALSE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER,
                filename TEXT NOT NULL,
                title TEXT,
                audio_path TEXT,
                transcription TEXT,
                summary TEXT,
                duration INTEGER,
                file_size INTEGER,
                drive_file_id TEXT,
                processed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                relative_path TEXT,
                FOREIGN KEY (course_id) REFERENCES courses (id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER,
                operation_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                details TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses (id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS prompt_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER,
                prompt_name TEXT NOT NULL,
                prompt_content TEXT,
                ai_service TEXT,
                response_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses (id)
            );
            """
        ]
        for query in queries:
            self._execute_query(query, commit=True)

        # Add relative_path column if it doesn't exist
        try:
            self._execute_query("ALTER TABLE episodes ADD COLUMN relative_path TEXT;", commit=True)
            # logger.info("Coluna 'relative_path' adicionada à tabela 'episodes'.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                # logger.info("Coluna 'relative_path' já existe na tabela 'episodes'.")
                pass # Column already exists, no action needed
            else:
                # logger.error(f"Erro ao adicionar coluna 'relative_path': {e}")
                raise # Re-raise other operational errors

        # logger.info("Tabelas verificadas/criadas com sucesso.")

    def create_course(self, name, source_path):
        # logger.info(f"Criando novo curso: {name}")
        query = "INSERT INTO courses (name, source_path) VALUES (?, ?)"
        try:
            course_id = self._execute_query(query, (name, source_path), commit=True)
            # logger.info(f"Curso '{name}' criado com ID: {course_id}")
            return course_id
        except sqlite3.IntegrityError:
            # logger.warning(f"Curso '{name}' já existe.")
            return None
        except Exception as e:
            # logger.error(f"Erro ao criar curso '{name}': {e}")
            raise

    def get_course(self, name):
        # logger.info(f"Buscando curso: {name}")
        query = "SELECT * FROM courses WHERE name = ?"
        return self._execute_query(query, (name,), fetchone=True)

    def get_course_by_id(self, course_id):
        # logger.info(f"Buscando curso por ID: {course_id}")
        query = "SELECT * FROM courses WHERE id = ?"
        return self._execute_query(query, (course_id,), fetchone=True)

    def update_course_status(self, course_id, status):
        # logger.info(f"Atualizando status do curso {course_id} para {status}")
        query = "UPDATE courses SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        self._execute_query(query, (status, course_id), commit=True)

    def create_episode(self, course_id, filename, title, audio_path=None, duration=0, file_size=0, relative_path=None):
        # logger.info(f"Criando episódio '{filename}' para o curso {course_id}")
        query = "INSERT INTO episodes (course_id, filename, title, audio_path, duration, file_size, relative_path) VALUES (?, ?, ?, ?, ?, ?, ?)"
        return self._execute_query(query, (course_id, filename, title, audio_path, duration, file_size, relative_path), commit=True)

    def get_episodes_by_course(self, course_id):
        # logger.info(f"Buscando episódios para o curso {course_id}")
        query = "SELECT * FROM episodes WHERE course_id = ? ORDER BY created_at ASC"
        return self._execute_query(query, (course_id,), fetchall=True)

    def log_operation(self, course_id, operation_type, details=None, error_message=None, status='pending'):
        # logger.info(f"Registrando operação '{operation_type}' para o curso {course_id}")
        query = "INSERT INTO operations (course_id, operation_type, details, error_message, status) VALUES (?, ?, ?, ?, ?)"
        return self._execute_query(query, (course_id, operation_type, details, error_message, status), commit=True)

    def get_operations_log(self, course_id):
        # logger.info(f"Buscando logs de operações para o curso {course_id}")
        query = "SELECT * FROM operations WHERE course_id = ? ORDER BY created_at DESC"
        return self._execute_query(query, (course_id,), fetchall=True)

    def save_setting(self, key, value):
        # logger.info(f"Salvando configuração: {key} = {value}")
        query = "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)"
        self._execute_query(query, (key, value), commit=True)

    def get_setting(self, key, default=None):
        # logger.info(f"Buscando configuração: {key}")
        query = "SELECT value FROM settings WHERE key = ?"
        result = self._execute_query(query, (key,), fetchone=True)
        return result['value'] if result else default

    def course_exists(self, name):
        # logger.info(f"Verificando se o curso '{name}' existe.")
        query = "SELECT 1 FROM courses WHERE name = ?"
        result = self._execute_query(query, (name,), fetchone=True)
        return result is not None

    def mark_course_completed(self, course_id):
        # logger.info(f"Marcando curso {course_id} como concluído.")
        query = "UPDATE courses SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        self._execute_query(query, (course_id,), commit=True)

    def get_processing_stage(self, course_id):
        # logger.info(f"Obtendo estágio de processamento para o curso {course_id}")
        query = "SELECT processing_stage FROM courses WHERE id = ?"
        result = self._execute_query(query, (course_id,), fetchone=True)
        return result['processing_stage'] if result else None

    def set_processing_stage(self, course_id, stage):
        # logger.info(f"Definindo estágio de processamento para o curso {course_id}: {stage}")
        query = "UPDATE courses SET processing_stage = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        self._execute_query(query, (stage, course_id), commit=True)

    def update_operation_status(self, operation_id, status, details=None, error_message=None):
        # logger.info(f"Atualizando status da operação {operation_id} para {status}")
        query = "UPDATE operations SET status = ?, details = ?, error_message = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?"
        self._execute_query(query, (status, details, error_message, operation_id), commit=True)

    def clear_all_tables(self):
        # logger.warning("Limpando todas as tabelas do banco de dados.")
        tables = ['prompt_usage', 'operations', 'episodes', 'courses', 'settings']
        for table in tables:
            self._execute_query(f"DELETE FROM {table}", commit=True)
        # logger.info("Todas as tabelas foram limpas.")

    def forget_course(self, course_id):
        # logger.info(f"Removendo curso {course_id} e seus dados associados.")
        self._execute_query("DELETE FROM prompt_usage WHERE course_id = ?", (course_id,), commit=True)
        self._execute_query("DELETE FROM operations WHERE course_id = ?", (course_id,), commit=True)
        self._execute_query("DELETE FROM episodes WHERE course_id = ?", (course_id,), commit=True)
        self._execute_query("DELETE FROM courses WHERE id = ?", (course_id,), commit=True)
        # logger.info(f"Curso {course_id} removido do banco de dados.")

    def log_prompt_usage(self, course_id, prompt_name, prompt_content, ai_service, response_content):
        # logger.info(f"Registrando uso de prompt para o curso {course_id}: {prompt_name}")
        query = "INSERT INTO prompt_usage (course_id, prompt_name, prompt_content, ai_service, response_content) VALUES (?, ?, ?, ?, ?)"
        self._execute_query(query, (course_id, prompt_name, prompt_content, ai_service, response_content), commit=True)
