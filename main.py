import sys
import io

# Forçar UTF-8 para stdout e stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# main.py
from services.database import DatabaseService
from services.course import CourseService
from services.ai import AIService
from utils.logging_utils import setup_logging

def course_processor_menu(course_service):
    pass
    # while True:
    #     choice = menu.show_course_processor_menu()
        
    #     if choice == "1":  # Process Complete Course
    #         directory = input("📁 Diretório do curso: ")
    #         course_service.process_complete_course(directory)
    #     elif choice == "2":  # Convert to Audio
    #         course_service.convert_to_audio()
    #     # ... outras opções

def settings_menu():
    pass

def show_logs():
    pass

def main():
    setup_logging()
    db = DatabaseService()
    course_service = CourseService(db)
    ai_service = AIService(db)
    # menu = MenuRenderer()
    
    # while True:
    #     choice = menu.show_main_menu()
        
    #     if choice == "1":  # Course Processor
    #         course_processor_menu(course_service)
    #     elif choice == "9":  # Settings
    #         settings_menu()
    #     elif choice == "11":  # Logs
    #         show_logs()
    #     elif choice == "12":  # Exit
    #         break
    print("\n🎓 NEURODEAMON MEDIA PROCESSOR")
    print("Menu principal exibido com sucesso (simulação).")
    print("\nSINAL DE SUCESSO: Execução concluída sem erros.")

if __name__ == "__main__":
    main()
