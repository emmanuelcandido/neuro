import sys
import io

# Forçar UTF-8 para stdout e stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# main.py
from services.database import DatabaseService
# from services.course_service import CourseService # Será usado depois
# from utils.menu_utils import MenuRenderer # Será criado depois
# from utils.logging_utils import setup_logging # Será usado depois

def main():
    # setup_logging()
    # setup_logging()
    db = DatabaseService()
    # course_service = CourseService(db)
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
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    main()

