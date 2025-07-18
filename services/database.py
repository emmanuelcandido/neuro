
import sqlite3
import os

class DatabaseService:
    def __init__(self, db_path='data/neurodeamon.db'):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Tabela de cursos
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            directory_path TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_videos INTEGER DEFAULT 0,
            total_duration_seconds INTEGER DEFAULT 0,
            processing_stage TEXT DEFAULT 'not_started'
        );
        """)

        # Tabela de episódios/vídeos
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER REFERENCES courses(id),
            filename TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            duration_seconds INTEGER DEFAULT 0,
            file_size_bytes INTEGER DEFAULT 0,
            hierarchy_level INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending'
        );
        """)

        # Tabela de operações/logs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER REFERENCES courses(id),
            operation_type TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT,
            details TEXT
        );
        """)

        # Tabela de configurações
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Tabela de prompts utilizados
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompt_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER REFERENCES courses(id),
            prompt_name TEXT NOT NULL,
            prompt_content TEXT NOT NULL,
            used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        self.conn.commit()

    def close(self):
        self.conn.close()
