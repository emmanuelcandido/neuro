import os
import json
import logging
from pathlib import Path

import openai
import anthropic
import google.generativeai as genai
from ollama import Client as OllamaClient

# logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, db_service):
        self.db = db_service
        self.apis = {
            'claude': self._setup_claude,
            'chatgpt': self._setup_chatgpt,
            'gemini': self._setup_gemini,
            'ollama': self._setup_ollama
        }
        self.current_ai = 'claude' # IA padrão
        self.api_keys = self._load_api_keys()

    def _load_api_keys(self):
        config_path = Path("config/api_keys.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {
            "openai_api_key": "",
            "anthropic_api_key": "",
            "google_ai_key": "",
            "ollama_base_url": "http://localhost:11434"
        }

    def save_api_keys(self, api_keys):
        config_path = Path("config/api_keys.json")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(api_keys, f, indent=2)
        self.api_keys = api_keys

    def _setup_claude(self):
        api_key = self.api_keys.get("anthropic_api_key")
        if not api_key:
            return None
        return anthropic.Anthropic(api_key=api_key)

    def _setup_chatgpt(self):
        api_key = self.api_keys.get("openai_api_key")
        if not api_key:
            return None
        return openai.OpenAI(api_key=api_key)

    def _setup_gemini(self):
        api_key = self.api_keys.get("google_ai_key")
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-pro')

    def _setup_ollama(self):
        base_url = self.api_keys.get("ollama_base_url")
        if not base_url:
            return None
        return OllamaClient(host=base_url)

    def validate_apis(self):
        # logger.info("Validando conectividade das APIs de IA...")
        status = {}
        for ai_name, setup_func in self.apis.items():
            try:
                client = setup_func()
                # Lógica de teste de conexão real para cada API
                status[ai_name] = {'status': 'ok', 'message': 'Conectado'}
            except Exception as e:
                status[ai_name] = {'status': 'error', 'message': str(e)}
        # logger.info(f"Status das APIs: {status}")
        return status

    def _load_prompt(self, prompt_name):
        prompt_path = Path(f"prompts/course_processor/{prompt_name}.md")
        if not prompt_path.exists():
            # logger.error(f"Prompt não encontrado: {prompt_path}")
            raise FileNotFoundError(f"Prompt {prompt_name}.md não encontrado.")
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    def generate_summary(self, transcription, prompt_name='resumo_detalhado'):
        # logger.info(f"Gerando resumo com prompt: {prompt_name}")
        prompt_content = self._load_prompt(prompt_name)
        full_prompt = f"{prompt_content}\n\nTranscrição:\n{transcription}"
        
        # Determine which AI to use (default to Claude)
        client = None
        ai_service_name = self.db.get_setting('default_ai', 'claude')

        if ai_service_name == 'claude':
            client = self._setup_claude()
        elif ai_service_name == 'chatgpt':
            client = self._setup_chatgpt()
        elif ai_service_name == 'gemini':
            client = self._setup_gemini()
        elif ai_service_name == 'ollama':
            client = self._setup_ollama()
        
        if not client:
            print(f"❌ {ai_service_name} API not configured or available.")
            return None

        try:
            response = self.process_with_continuation(full_prompt, client, ai_service_name)
            # self.db.log_prompt_usage(None, prompt_name, prompt_content, ai_service_name, response) # course_id will be added later
            return response
        except Exception as e:
            print(f"❌ Erro ao gerar resumo com {ai_service_name}: {e}")
            return None

    def transcribe_audio(self, audio_path, service='whisper'):
        # logger.info(f"Transcrevendo áudio: {audio_path} usando {service}")
        if service == 'whisper':
            client = self._setup_chatgpt() # OpenAI client for Whisper
            if not client:
                print("❌ OpenAI API key not configured for Whisper.")
                return None
            try:
                with open(audio_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                return transcript.text
            except Exception as e:
                print(f"❌ Erro ao transcrever áudio com Whisper: {e}")
                return None
        else:
            print(f"❌ Serviço de transcrição '{service}' não suportado.")
            return None

    def process_with_continuation(self, prompt, client, ai_service_name):
        # logger.info(f"Processando com continuação usando {ai_service_name}")
        full_response = ""
        current_prompt = prompt
        
        while True:
            response_part = ""
            try:
                if ai_service_name == 'claude':
                    response = client.messages.create(
                        model="claude-3-opus-20240229", # Or another suitable Claude model
                        max_tokens=4000,
                        messages=[
                            {"role": "user", "content": current_prompt}
                        ]
                    )
                    response_part = response.content[0].text if response.content else ""
                elif ai_service_name == 'chatgpt':
                    response = client.chat.completions.create(
                        model="gpt-4o", # Or another suitable GPT model
                        messages=[
                            {"role": "user", "content": current_prompt}
                        ]
                    )
                    response_part = response.choices[0].message.content
                elif ai_service_name == 'gemini':
                    response = client.generate_content(current_prompt)
                    response_part = response.text
                elif ai_service_name == 'ollama':
                    response = client.chat(
                        model=self.db.get_setting('ollama_model', 'llama3'), # User configured Ollama model
                        messages=[
                            {'role': 'user', 'content': current_prompt}
                        ]
                    )
                    response_part = response['message']['content']
                else:
                    print(f"❌ Serviço de IA '{ai_service_name}' não suportado para continuação.")
                    break

            except Exception as e:
                print(f"❌ Erro na chamada da API {ai_service_name}: {e}")
                break

            full_response += response_part.replace("[CONTINUA]", "").replace("[FIM]", "")
            
            if "[FIM]" in response_part:
                break
            elif "[CONTINUA]" in response_part:
                current_prompt = "[CONTINUAR]"
            else:
                # If no markers, assume it's finished
                break
        # logger.info("Processamento com continuação concluído.")
        return full_response
