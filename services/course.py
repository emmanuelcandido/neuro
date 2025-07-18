import os
import subprocess
from pathlib import Path
import json

class CourseService:
    def __init__(self, db_service):
        self.db = db_service
        self.supported_formats = ['.mp4', '.avi', '.mkv', '.mov', '.wmv']
        self.output_base_dir = Path("data/courses")

    def process_complete_course(self, course_path, course_name):
        # Implementar fluxo completo
        pass

    def scan_course_directory(self, path):
        course_files = []
        for root, _, files in os.walk(path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in self.supported_formats):
                    full_path = Path(root) / file
                    relative_path = full_path.relative_to(path)
                    course_files.append({
                        "full_path": str(full_path),
                        "relative_path": str(relative_path),
                        "filename": file,
                        "hierarchy_level": len(relative_path.parts) - 1 # 0 for root files, 1 for first level subfolders
                    })
        # TODO: Implement hierarchical sorting
        return course_files

    def convert_video_to_audio(self, video_path, audio_path):
        command = [
            "ffmpeg",
            "-i", video_path,
            "-vn", # No video
            "-ar", "44100", # Audio sample rate
            "-ac", "2", # Stereo
            "-b:a", "128k", # Audio bitrate
            audio_path
        ]
        try:
            subprocess.run(command, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Erro ao converter {video_path}: {e.stderr.decode()}")
            return False

    # Outros métodos serão adicionados aqui
