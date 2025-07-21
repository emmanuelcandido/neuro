import sys
import io

# Forçar UTF-8 para stdout e stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# main.py
from services.database import DatabaseService
from services.course_service import CourseService
from services.ai_service import AIService
from services.drive_service import DriveService
from services.xml_service import XMLService
from services.github_service import GitHubService
from services.settings import SettingsService # Importar SettingsService
from utils.logging_utils import setup_logging
from utils.menu_utils import MenuRenderer

def course_processor_menu(course_service, menu):
    while True:
        choice = menu.show_course_processor_menu()
        
        if choice == "1":  # Process Complete Course
            course_directory = input("📁 Digite o caminho completo do diretório do curso: ").strip()
            course_name = input("📝 Digite o nome do curso (ex: Marketing Digital): ").strip()
            if course_directory and course_name:
                print(f"Iniciando processamento para '{course_name}' em '{course_directory}'...")
                course_service.process_complete_course(course_directory, course_name)
            else:
                print("❌ Caminho do diretório ou nome do curso não podem ser vazios.")
        elif choice == "2":  # Convert Courses to Audio
            course_service.convert_courses_to_audio()
        elif choice == "3":  # Transcribe Audio Files
            course_service.transcribe_audio_files()
        elif choice == "4":  # Generate AI Course Summaries
            course_service.generate_ai_course_summaries()
        elif choice == "5":  # Create Unified Audio
            course_service.create_unified_audio()
        elif choice == "6":  # Generate Timestamps Only
            course_service.generate_timestamps_only()
        elif choice == "7":  # Generate Course TTS Audio Notes
            course_service.generate_course_tts_audio_notes()
        elif choice == "8":  # Upload Course to Google Drive
            course_service.upload_course_to_google_drive()
        elif choice == "9":  # Update courses.xml
            course_service.update_courses_xml()
        elif choice == "10": # Update GitHub Repository
            course_service.update_github_repository()
        elif choice == "11": # Course Status Check
            course_service.course_status_check()
        elif choice == "12": # Forget Course
            course_service.forget_course()
        elif choice == "13": # Clear All Data
            course_service.clear_all_data()
        elif choice == "0":  # Back to Main Menu
            break
        else:
            print("Opção inválida.")

def settings_menu(menu, ai_service, github_service, settings_service):
    while True:
        choice = menu.show_settings_menu()

        if choice == "1":  # API Keys & Validation
            settings_service.api_keys_settings()
        elif choice == "2":  # Voice Settings
            settings_service.voice_settings()
        elif choice == "3":  # Output Directory
            settings_service.output_directory()
        elif choice == "4":  # GitHub Repository
            print("Validando configuração do GitHub...")
            github_status = github_service.validate_setup()
            for key, value in github_status.items():
                print(f"  {key}: {value}")
        elif choice == "5":  # Cleanup Tools
            settings_service.cleanup_tools()
        elif choice == "6":  # Processing Preferences
            settings_service.processing_preferences()
        elif choice == "0":  # Back to Main Menu
            break
        else:
            print("Opção inválida.")

def show_logs():
    print("Exibindo logs...")
    # Implementar lógica para exibir logs

def main():
    setup_logging()
    db = DatabaseService()
    course_service = CourseService(db)
    ai_service = AIService(db)
    drive_service = DriveService(db)
    xml_service = XMLService(db)
    github_service = GitHubService(db)
    settings_service = SettingsService(db, ai_service) # Instanciar SettingsService
    menu = MenuRenderer()
    
    while True:
        choice = menu.show_main_menu()
        
        if choice == "1":  # Course Processor
            course_processor_menu(course_service, menu)
        elif choice == "9":  # Settings
            settings_menu(menu, ai_service, github_service, settings_service)
        elif choice == "11":  # Logs
            show_logs()
        elif choice == "12":  # Exit
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    main()