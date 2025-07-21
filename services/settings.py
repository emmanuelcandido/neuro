import os
import json
import shutil
from pathlib import Path

class SettingsService:
    def __init__(self, db_service, ai_service):
        self.db = db_service
        self.ai_service = ai_service

    def api_keys_settings(self):
        print("🔑 Configuração de Chaves de API")
        print("=" * 50)
        
        api_keys = self.ai_service._load_api_keys()

        print("\n--- OpenAI (ChatGPT / Whisper) ---")
        openai_key = input(f"Chave OpenAI (atual: {api_keys.get('openai_api_key', '')}): ").strip()
        if openai_key:
            api_keys['openai_api_key'] = openai_key

        print("\n--- Anthropic (Claude) ---")
        anthropic_key = input(f"Chave Anthropic (atual: {api_keys.get('anthropic_api_key', '')}): ").strip()
        if anthropic_key:
            api_keys['anthropic_api_key'] = anthropic_key

        print("\n--- Google (Gemini) ---")
        google_ai_key = input(f"Chave Google AI (atual: {api_keys.get('google_ai_key', '')}): ").strip()
        if google_ai_key:
            api_keys['google_ai_key'] = google_ai_key

        print("\n--- Ollama ---")
        ollama_base_url = input(f"URL Base Ollama (atual: {api_keys.get('ollama_base_url', 'http://localhost:11434')}): ").strip()
        if ollama_base_url:
            api_keys['ollama_base_url'] = ollama_base_url

        self.ai_service.save_api_keys(api_keys)
        print("✅ Chaves de API salvas.")

    def voice_settings(self):
        print("🎙️ Configurações de Voz")
        print("=" * 50)
        
        # Carregar configurações existentes ou padrão
        current_pt_voice = self.db.get_setting('pt_br_voice', 'pt-BR-AntonioNeural')
        current_en_voice = self.db.get_setting('en_us_voice', 'en-US-AriaNeural')
        
        print(f"Voz atual para PT-BR: {current_pt_voice}")
        new_pt_voice = input("Nova voz para PT-BR (deixe em branco para manter): ").strip()
        if new_pt_voice:
            self.db.save_setting('pt_br_voice', new_pt_voice)
            print(f"✅ Voz para PT-BR atualizada para: {new_pt_voice}")

        print(f"Voz atual para EN-US: {current_en_voice}")
        new_en_voice = input("Nova voz para EN-US (deixe em branco para manter): ").strip()
        if new_en_voice:
            self.db.save_setting('en_us_voice', new_en_voice)
            print(f"✅ Voz para EN-US atualizada para: {new_en_voice}")

    def output_directory(self):
        print("📁 Configuração do Diretório de Saída")
        print("=" * 50)
        
        current_output_dir = self.db.get_setting('output_directory', str(Path.home() / 'NeuroDeamon_Output'))
        
        print(f"Diretório de saída atual: {current_output_dir}")
        new_output_dir = input("Novo diretório de saída (deixe em branco para manter): ").strip()
        
        if new_output_dir:
            try:
                Path(new_output_dir).mkdir(parents=True, exist_ok=True)
                self.db.save_setting('output_directory', new_output_dir)
                print(f"✅ Diretório de saída atualizado para: {new_output_dir}")
            except Exception as e:
                print(f"❌ Erro ao criar o diretório: {e}")

    def cleanup_tools(self):
        print("🧹 Ferramentas de Limpeza")
        print("=" * 50)
        
        print("Opções de limpeza:")
        print("[1] Limpar arquivos temporários")
        print("[2] Limpar cache de cursos")
        print("[3] Limpar logs")
        
        choice = input("Escolha uma opção: ").strip()
        
        if choice == '1':
            self._clear_directory('temp/audio_conversion')
            self._clear_directory('temp/transcriptions')
            self._clear_directory('temp/processing')
            print("✅ Arquivos temporários limpos.")
        elif choice == '2':
            self._clear_directory('data/courses')
            print("✅ Cache de cursos limpo.")
        elif choice == '3':
            self._clear_directory('data/logs')
            print("✅ Logs limpos.")
        else:
            print("Opção inválida.")

    def _clear_directory(self, dir_path):
        path = Path(dir_path)
        if path.exists() and path.is_dir():
            for item in path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

    def processing_preferences(self):
        print("🎯 Preferências de Processamento")
        print("=" * 50)

        # Exemplo de preferência: IA padrão
        current_default_ai = self.db.get_setting('default_ai', 'claude')
        print(f"IA padrão atual: {current_default_ai}")
        new_default_ai = input("Nova IA padrão (claude, chatgpt, gemini, ollama): ").strip().lower()
        if new_default_ai in ['claude', 'chatgpt', 'gemini', 'ollama']:
            self.db.save_setting('default_ai', new_default_ai)
            print(f"✅ IA padrão atualizada para: {new_default_ai}")
        elif new_default_ai:
            print("❌ Opção de IA inválida.")

        # Exemplo 2: Manter arquivos individuais após unificação
        keep_files = self.db.get_setting('keep_individual_files', 'true')
        print(f"Manter arquivos individuais após unificação: {keep_files}")
        new_keep_files = input("Manter arquivos? (true/false): ").strip().lower()
        if new_keep_files in ['true', 'false']:
            self.db.save_setting('keep_individual_files', new_keep_files)
            print(f"✅ Preferência de manter arquivos atualizada para: {new_keep_files}")
        elif new_keep_files:
            print("❌ Opção inválida. Use 'true' ou 'false'.")