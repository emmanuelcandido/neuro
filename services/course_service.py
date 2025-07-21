import os
import subprocess
from pathlib import Path
import json
import logging
import re
import shutil
from datetime import datetime

from services.ai_service import AIService
from services.drive_service import DriveService
from services.xml_service import XMLService
from services.github_service import GitHubService

# logger = logging.getLogger(__name__)

class CourseService:
    def __init__(self, db_service):
        self.db = db_service
        self.ai_service = AIService(db_service) # Instanciar AIService
        self.drive_service = DriveService(db_service) # Instanciar DriveService
        self.xml_service = XMLService(db_service) # Instanciar XMLService
        self.github_service = GitHubService(db_service) # Instanciar GitHubService
        self.supported_formats = ['.mp4', '.avi', '.mkv', '.mov', '.wmv']
        self.output_base_dir = Path("data/courses")

    def _select_course(self):
        print("📂 Selecione um curso:")
        courses = [d.name for d in self.output_base_dir.iterdir() if d.is_dir()]
        if not courses:
            print("Nenhum curso encontrado.")
            return None

        for i, course_name in enumerate(courses):
            print(f"[{i + 1}] {course_name}")

        while True:
            try:
                choice = int(input("Escolha um curso: "))
                if 1 <= choice <= len(courses):
                    return courses[choice - 1]
                else:
                    print("Escolha inválida.")
            except ValueError:
                print("Por favor, insira um número.")

    def process_complete_course(self, course_path, course_name):
        # logger.info(f"Iniciando processamento completo do curso: {course_name} em {course_path}")
        print(f"Iniciando processamento completo do curso: {course_name} em {course_path}")
        try:
            # 1. Descoberta e Validação
            if not self._validate_course_directory(course_path):
                # logger.error(f"Diretório do curso inválido ou sem vídeos: {course_path}")
                print(f"❌ Erro: Diretório do curso inválido ou sem vídeos: {course_path}")
                return

            course_files = self.scan_course_directory(course_path)
            if not course_files:
                # logger.warning(f"Nenhum vídeo suportado encontrado no diretório: {course_path}")
                print(f"⚠️ Aviso: Nenhum vídeo suportado encontrado no diretório: {course_path}")
                return

            # 2. Verificar se curso já foi processado
            existing_course = self.db.get_course(course_name)
            if existing_course:
                # logger.info(f"Curso '{course_name}' já existe na database. Oferecendo opção de retomar.")
                print(f"ℹ️ Curso '{course_name}' já existe. Deseja retomar o processamento?")
                # TODO: Implementar lógica de retomada
                return

            # 3. Preparação: Criar entrada na database
            course_id = self.db.create_course(course_name, course_path)
            if not course_id:
                # logger.error(f"Falha ao criar entrada para o curso '{course_name}' na database.")
                print(f"❌ Erro: Falha ao criar entrada para o curso '{course_name}' na database.")
                return
            # logger.info(f"Curso '{course_name}' registrado na database com ID: {course_id}")
            print(f"✅ Curso '{course_name}' registrado na database com ID: {course_id}")

            # TODO: Configurar diretórios de trabalho, verificar espaço em disco, validar APIs

            # 4. Conversão de Vídeo para Áudio
            print("Iniciando conversão de vídeo para áudio...")
            audio_output_dir = self.output_base_dir / course_name / "audios"
            audio_output_dir.mkdir(parents=True, exist_ok=True)

            for file_info in course_files:
                video_path = Path(file_info['full_path'])
                relative_audio_path = Path(file_info['relative_path']).with_suffix(".mp3")
                audio_path = audio_output_dir / relative_audio_path
                audio_path.parent.mkdir(parents=True, exist_ok=True)

                print(f"  Convertendo {video_path.name} para {audio_path.name}...")
                success, duration, file_size = self.convert_video_to_audio(str(video_path), str(audio_path))
                if success:
                    episode_id = self.db.create_episode(
                        course_id=course_id,
                        filename=audio_path.name,
                        title=video_path.stem, # Título do episódio
                        audio_path=str(audio_path),
                        duration=duration,
                        file_size=file_size,
                        relative_path=str(file_info['relative_path'])
                    )
                    print(f"    ✅ Áudio convertido e episódio registrado: {audio_path.name} (Duração: {duration}s, Tamanho: {file_size} bytes)")
                else:
                    print(f"    ❌ Falha na conversão de {video_path.name}")
            print("Conversão de vídeo para áudio concluída.")

            # 5. Transcrição
            print("Iniciando transcrição de áudio...")
            transcription_output_dir = self.output_base_dir / course_name / "transcriptions"
            transcription_output_dir.mkdir(parents=True, exist_ok=True)

            episodes = self.db.get_episodes_by_course(course_id)
            for episode in episodes:
                audio_path = Path(episode['audio_path'])
                transcription_path = transcription_output_dir / f"{audio_path.stem}.txt"
                
                print(f"  Transcrevendo {audio_path.name}...")
                transcription_text = self.ai_service.transcribe_audio(str(audio_path))
                
                if transcription_text:
                    with open(transcription_path, 'w', encoding='utf-8') as f:
                        f.write(transcription_text)
                    # TODO: Atualizar episódio na database com o caminho da transcrição
                    print(f"    ✅ Áudio transcrito: {transcription_path.name}")
                else:
                    print(f"    ❌ Falha na transcrição de {audio_path.name}")
            print("Transcrição de áudio concluída.")

            # 6. Geração de Resumos via IA
            print("Iniciando geração de resumos com IA...")
            summary_output_dir = self.output_base_dir / course_name / "summaries"
            summary_output_dir.mkdir(parents=True, exist_ok=True)

            episodes = self.db.get_episodes_by_course(course_id) # Recarregar episódios para garantir transcrição
            for episode in episodes:
                transcription_path = transcription_output_dir / f"{Path(episode['audio_path']).stem}.txt"
                if not transcription_path.exists():
                    print(f"    ⚠️ Transcrição não encontrada para {episode['filename']}. Pulando resumo.")
                    continue
                
                with open(transcription_path, 'r', encoding='utf-8') as f:
                    transcription_text = f.read()

                summary_path = summary_output_dir / f"{Path(episode['audio_path']).stem}.md"
                
                print(f"  Gerando resumo para {episode['filename']}...")
                summary_text = self.ai_service.generate_summary(transcription_text, 'resumo_detalhado')
                
                if summary_text:
                    with open(summary_path, 'w', encoding='utf-8') as f:
                        f.write(summary_text)
                    # TODO: Atualizar episódio na database com o caminho do resumo
                    print(f"    ✅ Resumo gerado: {summary_path.name}")
                else:
                    print(f"    ❌ Falha na geração do resumo para {episode['filename']}")
            print("Geração de resumos com IA concluída.")

            # 7. Unificação de Conteúdo
            print("Iniciando unificação de conteúdo...")
            final_output_dir = self.output_base_dir / course_name / "final"
            final_output_dir.mkdir(parents=True, exist_ok=True)

            # Gerar Resumo.md unificado
            unified_summary_path = final_output_dir / "Resumo.md"
            self._generate_unified_summary(course_id, unified_summary_path)
            
            # Criar áudio unificado
            unified_audio_path = final_output_dir / f"{course_name}.mp3"
            self._create_unified_audio(course_id, unified_audio_path)

            # Gerar timestamps.md
            timestamps_path = final_output_dir / "timestamps.md"
            self._generate_timestamps(course_id, timestamps_path)

            print("Unificação de conteúdo concluída.")

            # 8. Distribuição
            print("Iniciando distribuição (Google Drive, RSS, GitHub)....")
            
            # Upload para Google Drive
            print("  Fazendo upload para Google Drive...")
            drive_files_to_upload = {
                str(unified_audio_path): f"{course_name}.mp3",
                str(unified_summary_path): "Resumo.md",
                str(timestamps_path): "timestamps.md"
            }
            # TODO: Adicionar audios_individuais, transcricoes, resumos_individuais
            self.drive_service.upload_course_files(course_name, drive_files_to_upload)
            print("  Upload para Google Drive concluído.")

            # Atualizar feed RSS
            print("  Atualizando feed RSS...")
            # Obter URL pública do áudio unificado (após upload para o Drive)
            # TODO: Obter file_id e public_url do upload_course_files
            unified_audio_file_id = "SEU_AUDIO_ID_AQUI" # Placeholder
            unified_audio_public_url = self.drive_service.get_direct_download_url(unified_audio_file_id)
            
            course_data_for_rss = {
                'title': course_name,
                'description': "Resumo completo do curso.", # TODO: Usar resumo real
                'audio_url': unified_audio_public_url,
                'file_size': os.path.getsize(unified_audio_path),
                'duration': self._get_audio_info(unified_audio_path)[0],
                'pub_date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z'),
                'timestamps': [], # TODO: Obter timestamps reais
                'links': []
            }
            self.xml_service.create_or_update_feed(course_data_for_rss)
            print("  Feed RSS atualizado.")

            # Atualizar repositório GitHub
            print("  Atualizando repositório GitHub...")
            self.github_service.update_course_feed(self.xml_service.feed_path)
            print("  Repositório GitHub atualizado.")

            # Copiar arquivos finais para o diretório original do curso
            print("  Copiando arquivos finais para o diretório original do curso...")
            shutil.copy2(unified_summary_path, Path(course_path) / "Resumo.md")
            shutil.copy2(unified_audio_path, Path(course_path) / f"{course_name}.mp3")
            shutil.copy2(timestamps_path, Path(course_path) / "timestamps.md")
            print("  Arquivos finais copiados.")

            print("Distribuição concluída.")

            # 9. Finalização
            self.db.mark_course_completed(course_id)
            print(f"✅ Processamento completo do curso {course_name} FINALIZADO.")

        except Exception as e:
            # logger.exception(f"Erro inesperado durante o processamento do curso {course_name}")
            print(f"❌ Erro inesperado durante o processamento do curso {course_name}: {e}")

    def _validate_course_directory(self, path):
        if not Path(path).is_dir():
            return False
        # Verificar se contém vídeos suportados
        for root, _, files in os.walk(path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in self.supported_formats):
                    return True
        return False

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
        
        # Ordenação hierárquica: pastas primeiro, depois arquivos, por nome
        # Para isso, precisamos de uma chave de ordenação que considere a estrutura de diretórios
        def sort_key(item):
            parts = Path(item['relative_path']).parts
            # Prioriza diretórios (se o item for um diretório, ele virá antes dos arquivos no mesmo nível)
            # Para arquivos, a hierarquia é dada pelos diretórios pai
            # Para o mesmo nível e tipo (arquivo/diretório), ordena por nome
            return (len(parts),) + tuple(p.lower() for p in parts)

        course_files.sort(key=sort_key)
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
            duration, file_size = self._get_audio_info(audio_path)
            return True, duration, file_size
        except subprocess.CalledProcessError as e:
            print(f"Erro ao converter {video_path}: {e.stderr.decode()}")
            return False, 0, 0

    def _get_audio_info(self, audio_path):
        try:
            # Obter duração
            cmd_duration = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]
            duration_str = subprocess.check_output(cmd_duration, stderr=subprocess.STDOUT).decode().strip()
            duration = int(float(duration_str)) if duration_str else 0

            # Obter tamanho do arquivo
            file_size = os.path.getsize(audio_path)
            
            return duration, file_size
        except Exception as e:
            print(f"Erro ao obter informações do áudio {audio_path}: {e}")
            return 0, 0

    def _generate_unified_summary(self, course_id, output_path):
        print(f"  Gerando resumo unificado em {output_path}...")
        episodes = self.db.get_episodes_by_course(course_id)
        
        unified_content = []
        current_path_parts = []

        for episode in episodes:
            summary_file = Path(self.output_base_dir) / self.db.get_course_by_id(course_id)['name'] / "summaries" / f"{Path(episode['audio_path']).stem}.md"
            if not summary_file.exists():
                print(f"    ⚠️ Resumo individual não encontrado para {episode['filename']}. Pulando.")
                continue

            # Determinar a hierarquia para os cabeçalhos
            relative_parts = Path(episode['relative_path']).parts
            
            # Adicionar cabeçalhos de pasta
            for i, part in enumerate(relative_parts[:-1]): # Ignorar o nome do arquivo
                if i >= len(current_path_parts) or part != current_path_parts[i]:
                    unified_content.append(f"# {part}\n") # H1 para pastas
                    current_path_parts = relative_parts[:i+1]
            
            # Adicionar cabeçalho do arquivo
            unified_content.append(f"## {episode['title']}\n") # H2 para arquivos
            
            with open(summary_file, 'r', encoding='utf-8') as f:
                unified_content.append(f.read())
            unified_content.append("\n\n") # Espaço entre resumos

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("".join(unified_content))
        print(f"  ✅ Resumo unificado gerado: {output_path.name}")

    def _create_unified_audio(self, course_id, output_path):
        print(f"  Criando áudio unificado em {output_path}...")
        course = self.db.get_course_by_id(course_id)
        if not course:
            print(f"❌ Curso com ID {course_id} não encontrado.")
            return False

        episodes = self.db.get_episodes_by_course(course_id)
        audio_files = [episode['audio_path'] for episode in episodes if episode['audio_path']]

        if not audio_files:
            print("    ⚠️ Nenhum arquivo de áudio encontrado para unificação.")
            return False

        # Criar um arquivo de lista para ffmpeg
        list_file_path = output_path.parent / "audio_list.txt"
        with open(list_file_path, 'w', encoding='utf-8') as f:
            for audio_file in audio_files:
                f.write(f"file '{audio_file}'\n")

        command = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file_path),
            "-c", "copy",
            str(output_path)
        ]
        try:
            subprocess.run(command, check=True, capture_output=True)
            print(f"  ✅ Áudio unificado criado: {output_path.name}")
            os.remove(list_file_path) # Limpar arquivo de lista
            return True
        except subprocess.CalledProcessError as e:
            print(f"    ❌ Erro ao unificar áudios: {e.stderr.decode()}")
            return False

    def _generate_timestamps(self, course_id, output_path):
        print(f"  Gerando timestamps em {output_path}...")
        course = self.db.get_course_by_id(course_id)
        if not course:
            print(f"❌ Curso com ID {course_id} não encontrado.")
            return

        episodes = self.db.get_episodes_by_course(course_id)
        
        timestamps_content = []
        cumulative_duration = 0
        current_path_parts = []

        for episode in episodes:
            # Determinar a hierarquia para os cabeçalhos
            relative_parts = Path(episode['relative_path']).parts
            
            # Adicionar cabeçalhos de pasta
            for i, part in enumerate(relative_parts[:-1]): # Ignorar o nome do arquivo
                if i >= len(current_path_parts) or part != current_path_parts[i]:
                    timestamps_content.append(f"# {part}\n") # H1 para pastas
                    current_path_parts = relative_parts[:i+1]
            
            # Formatar timestamp
            hours = cumulative_duration // 3600
            minutes = (cumulative_duration % 3600) // 60
            seconds = cumulative_duration % 60
            timestamp_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            timestamps_content.append(f"## {episode['title']}\n") # H2 para arquivos
            timestamps_content.append(f"{timestamp_str} {episode['title']}\n")
            
            cumulative_duration += episode['duration']

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("".join(timestamps_content))
        print(f"  ✅ Timestamps gerados: {output_path.name}")

    def convert_courses_to_audio(self):
        print("🎬 Conversão de Cursos para Áudio")
        print("=" * 50)
        course_path = input("📁 Digite o caminho completo do diretório do curso: ").strip()
        course_name = input("📝 Digite o nome do curso: ").strip()

        if not course_path or not course_name:
            print("❌ Caminho e nome do curso são obrigatórios.")
            return

        if not self._validate_course_directory(course_path):
            print(f"❌ Erro: Diretório do curso inválido ou sem vídeos: {course_path}")
            return

        course_files = self.scan_course_directory(course_path)
        if not course_files:
            print(f"⚠️ Aviso: Nenhum vídeo suportado encontrado no diretório: {course_path}")
            return

        course_id = self.db.get_course(course_name)
        if not course_id:
            course_id = self.db.create_course(course_name, course_path)
            print(f"✅ Curso '{course_name}' registrado na database com ID: {course_id}")
        else:
            course_id = course_id['id']
            print(f"ℹ️ Curso '{course_name}' já existe na database (ID: {course_id}). Adicionando áudios.")

        audio_output_dir = self.output_base_dir / course_name / "audios"
        audio_output_dir.mkdir(parents=True, exist_ok=True)

        for file_info in course_files:
            video_path = Path(file_info['full_path'])
            relative_audio_path = Path(file_info['relative_path']).with_suffix(".mp3")
            audio_path = audio_output_dir / relative_audio_path
            audio_path.parent.mkdir(parents=True, exist_ok=True)

            print(f"  Convertendo {video_path.name} para {audio_path.name}...")
            success, duration, file_size = self._convert_video_to_audio(str(video_path), str(audio_path))
            if success:
                self.db.create_episode(
                    course_id=course_id,
                    filename=audio_path.name,
                    title=video_path.stem,
                    audio_path=str(audio_path),
                    duration=duration,
                    file_size=file_size
                )
                print(f"    ✅ Áudio convertido e episódio registrado: {audio_path.name}")
            else:
                print(f"    ❌ Falha na conversão de {video_path.name}")
        
        print("Conversão de vídeo para áudio concluída.")

    def transcribe_audio_files(self):
        print("📝 Transcrição de Arquivos de Áudio")
        print("=" * 50)
        course_name = self._select_course()
        if not course_name:
            return

        course = self.db.get_course(course_name)

        if not course:
            print(f"❌ Curso '{course_name}' não encontrado.")
            return

        course_id = course['id']
        episodes = self.db.get_episodes_by_course(course_id)

        if not episodes:
            print(f"⚠️ Nenhum episódio (áudio) encontrado para o curso '{course_name}'.")
            return

        transcription_output_dir = self.output_base_dir / course_name / "transcriptions"
        transcription_output_dir.mkdir(parents=True, exist_ok=True)

        for episode in episodes:
            audio_path = Path(episode['audio_path'])
            transcription_path = transcription_output_dir / f"{audio_path.stem}.txt"

            if transcription_path.exists():
                print(f"  ⏭️ Transcrição já existe para {audio_path.name}, pulando.")
                continue

            print(f"  Transcrevendo {audio_path.name}...")
            transcription_text = self.ai_service.transcribe_audio(str(audio_path))
            
            if transcription_text:
                with open(transcription_path, 'w', encoding='utf-8') as f:
                    f.write(transcription_text)
                # TODO: Atualizar episódio na database com o caminho da transcrição
                print(f"    ✅ Áudio transcrito: {transcription_path.name}")
            else:
                print(f"    ❌ Falha na transcrição de {audio_path.name}")
        print("Transcrição de áudio concluída.")

    def generate_ai_course_summaries(self):
        print("🤖 Geração de Resumos com IA")
        print("=" * 50)
        course_name = self._select_course()
        if not course_name:
            return

        course = self.db.get_course(course_name)

        if not course:
            print(f"❌ Curso '{course_name}' não encontrado.")
            return

        course_id = course['id']
        episodes = self.db.get_episodes_by_course(course_id)

        if not episodes:
            print(f"⚠️ Nenhum episódio encontrado para o curso '{course_name}'.")
            return

        summary_output_dir = self.output_base_dir / course_name / "summaries"
        summary_output_dir.mkdir(parents=True, exist_ok=True)
        transcription_output_dir = self.output_base_dir / course_name / "transcriptions"

        for episode in episodes:
            audio_path = Path(episode['audio_path'])
            transcription_path = transcription_output_dir / f"{audio_path.stem}.txt"
            summary_path = summary_output_dir / f"{audio_path.stem}.md"

            if summary_path.exists():
                print(f"  ⏭️ Resumo já existe para {audio_path.name}, pulando.")
                continue

            if not transcription_path.exists():
                print(f"    ⚠️ Transcrição não encontrada para {episode['filename']}. Pulando resumo.")
                continue
            
            with open(transcription_path, 'r', encoding='utf-8') as f:
                transcription_text = f.read()

            print(f"  Gerando resumo para {episode['filename']}...")
            summary_text = self.ai_service.generate_summary(transcription_text, 'resumo_detalhado')
            
            if summary_text:
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write(summary_text)
                # TODO: Atualizar episódio na database com o caminho do resumo
                print(f"    ✅ Resumo gerado: {summary_path.name}")
            else:
                print(f"    ❌ Falha na geração do resumo para {episode['filename']}")
        print("Geração de resumos com IA concluída.")

    def create_unified_audio(self):
        print("🎵 Criação de Áudio Unificado")
        print("=" * 50)
        course_name = self._select_course()
        if not course_name:
            return

        course = self.db.get_course(course_name)

        if not course:
            print(f"❌ Curso '{course_name}' não encontrado.")
            return

        course_id = course['id']
        final_output_dir = self.output_base_dir / course_name / "final"
        final_output_dir.mkdir(parents=True, exist_ok=True)
        unified_audio_path = final_output_dir / f"{course_name}.mp3"

        if unified_audio_path.exists():
            print(f"  ⏭️ Áudio unificado já existe para {course_name}, pulando.")
            return

        self._create_unified_audio(course_id, unified_audio_path)
        print("Criação de áudio unificado concluída.")

    def generate_timestamps_only(self):
        print("⏱️ Geração de Timestamps")
        print("=" * 50)
        course_name = self._select_course()
        if not course_name:
            return

        course = self.db.get_course(course_name)

        if not course:
            print(f"❌ Curso '{course_name}' não encontrado.")
            return

        course_id = course['id']
        final_output_dir = self.output_base_dir / course_name / "final"
        final_output_dir.mkdir(parents=True, exist_ok=True)
        timestamps_path = final_output_dir / "timestamps.md"

        if timestamps_path.exists():
            print(f"  ⏭️ Timestamps já existem para {course_name}, pulando.")
            return

        self._generate_timestamps(course_id, timestamps_path)
        print("Geração de timestamps concluída.")

    def generate_course_tts_audio_notes(self):
        print("🎙️ Geração de Notas de Áudio TTS")
        print("=" * 50)
        course_name = self._select_course()
        if not course_name:
            return

        course = self.db.get_course(course_name)

        if not course:
            print(f"❌ Curso '{course_name}' não encontrado.")
            return

        course_id = course['id']
        episodes = self.db.get_episodes_by_course(course_id)

        if not episodes:
            print(f"⚠️ Nenhum episódio encontrado para o curso '{course_name}'.")
            return

        tts_output_dir = self.output_base_dir / course_name / "tts_notes"
        tts_output_dir.mkdir(parents=True, exist_ok=True)
        summary_output_dir = self.output_base_dir / course_name / "summaries"

        for episode in episodes:
            summary_path = summary_output_dir / f"{Path(episode['audio_path']).stem}.md"
            tts_audio_path = tts_output_dir / f"{Path(episode['audio_path']).stem}.mp3"

            if tts_audio_path.exists():
                print(f"  ⏭️ Nota de áudio TTS já existe para {episode['filename']}, pulando.")
                continue

            if not summary_path.exists():
                print(f"    ⚠️ Resumo não encontrado para {episode['filename']}. Pulando nota de áudio.")
                continue
            
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary_text = f.read()

            print(f"  Gerando nota de áudio para {episode['filename']}...")
            # Placeholder for TTS service
            print("    (Simulação de serviço TTS)")
            # self.tts_service.convert_to_audio(summary_text, tts_audio_path)
            print(f"    ✅ Nota de áudio gerada: {tts_audio_path.name}")

        print("Geração de notas de áudio TTS concluída.")

    def upload_course_to_google_drive(self):
        print("📤 Upload para Google Drive")
        print("=" * 50)
        course_name = self._select_course()
        if not course_name:
            return

        course = self.db.get_course(course_name)

        if not course:
            print(f"❌ Curso '{course_name}' não encontrado.")
            return

        final_output_dir = self.output_base_dir / course_name / "final"
        if not final_output_dir.exists():
            print(f"❌ Diretório final não encontrado para o curso '{course_name}'. Gere os arquivos finais primeiro.")
            return

        files_to_upload = {
            str(final_output_dir / f"{course_name}.mp3"): f"{course_name}.mp3",
            str(final_output_dir / "Resumo.md"): "Resumo.md",
            str(final_output_dir / "timestamps.md"): "timestamps.md"
        }

        self.drive_service.upload_course_files(course_name, files_to_upload)
        print("Upload para Google Drive concluído.")

    def update_courses_xml(self):
        print("📋 Atualização do courses.xml")
        print("=" * 50)
        course_name = self._select_course()
        if not course_name:
            return

        course = self.db.get_course(course_name)

        if not course:
            print(f"❌ Curso '{course_name}' não encontrado.")
            return

        course_id = course['id']
        final_output_dir = self.output_base_dir / course_name / "final"
        unified_audio_path = final_output_dir / f"{course_name}.mp3"

        if not unified_audio_path.exists():
            print(f"❌ Áudio unificado não encontrado para o curso '{course_name}'. Crie o áudio primeiro.")
            return

        # TODO: Obter a URL pública do Google Drive
        drive_file_id = "PLACEHOLDER_DRIVE_FILE_ID"
        public_url = self.drive_service.get_direct_download_url(drive_file_id)

        duration, file_size = self._get_audio_info(str(unified_audio_path))

        course_data_for_rss = {
            'title': course_name,
            'description': f"Resumo do curso {course_name}", # Placeholder
            'audio_url': public_url,
            'file_size': file_size,
            'duration': duration,
            'pub_date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z'),
            'timestamps': [], # Placeholder
            'links': [] # Placeholder
        }

        self.xml_service.create_or_update_feed(course_data_for_rss)
        print("Atualização do courses.xml concluída.")

    def update_github_repository(self):
        print("🔄 Atualização do Repositório GitHub")
        print("=" * 50)
        self.github_service.update_course_feed(self.xml_service.feed_path)
        print("Atualização do repositório GitHub concluída.")

    def course_status_check(self):
        print("📋 Verificação de Status do Curso")
        print("=" * 50)
        course_name = self._select_course()
        if not course_name:
            return

        course = self.db.get_course(course_name)

        if not course:
            print(f"❌ Curso '{course_name}' não encontrado.")
            return

        print(f"Status do curso: {course['status']}")
        print(f"Estágio de processamento: {course['processing_stage']}")
        print(f"Total de episódios: {course['total_episodes']}")
        print(f"Episódios concluídos: {course['completed_episodes']}")

        operations = self.db.get_operations_log(course['id'])
        if operations:
            print("\n--- Log de Operações ---")
            for op in operations:
                print(f"[{op['completed_at']}] {op['operation_type']}: {op['status']}")

    def forget_course(self):
        print("🗑️ Esquecer Curso")
        print("=" * 50)
        course_name = self._select_course()
        if not course_name:
            return

        course = self.db.get_course(course_name)

        if not course:
            print(f"❌ Curso '{course_name}' não encontrado.")
            return

        confirm = input(f"Tem certeza que deseja esquecer o curso '{course_name}'? Isso removerá o registro do banco de dados. (s/n): ").strip().lower()
        if confirm == 's':
            self.db.forget_course(course['id'])
            print(f"✅ Curso '{course_name}' esquecido.")
        else:
            print("Operação cancelada.")

    def clear_all_data(self):
        print("🗑️ Limpar Todos os Dados")
        print("=" * 50)
        confirm = input("Tem certeza que deseja limpar todos os dados? Isso removerá todos os cursos, áudios, transcrições, etc. (s/n): ").strip().lower()
        if confirm == 's':
            self._clear_directory('data/courses')
            self._clear_directory('data/logs')
            self.db.clear_all_tables()
            print("✅ Todos os dados foram limpos.")
        else:
            print("Operação cancelada.")
