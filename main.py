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
    print("Iniciando a aplicação...")
    try:
        db = DatabaseService()
        print("DatabaseService instanciado com sucesso.")
        db.create_tables()
        print("Tabelas criadas ou já existentes.")
        db.close()
        print("Conexão com o banco de dados fechada.")
        print("\n🎓 NEURODEAMON MEDIA PROCESSOR")
        print("Menu principal exibido com sucesso (simulação).")
        print("\nSINAL DE SUCESSO: Execução concluída sem erros.")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    main()

