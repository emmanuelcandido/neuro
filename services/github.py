import os
import git
import json
from github import Github
from datetime import datetime
import shutil

class GitHubService:
    def __init__(self, db_service):
        self.db = db_service
        self.repo_name = "neurodeamon-feeds"
        self.local_path = "github/neurodeamon-feeds"
        self.github_client = None
        self.repo = None
        self.git_repo = None
        self.config = self._load_github_config()
        self.setup_github()
    
    def _load_github_config(self):
        config_path = "config/github_config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            config = self._interactive_setup()
            os.makedirs('config', exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return config

    def _interactive_setup(self):
        print("🐙 Configuração do GitHub")
        print("=" * 50)
        
        config = {
            'token': input("Token do GitHub (Personal Access Token): "),
            'username': input("Nome de usuário GitHub: "),
            'email': input("Email do GitHub: "),
            'repo_name': input(f"Nome do repositório [{self.repo_name}]: ") or self.repo_name,
            'branch': 'main'
        }
        
        return config

    def setup_github(self):
        self.github_client = Github(self.config['token'])
        self._setup_git_config(self.config)
        self._ensure_repository_exists(self.config)

    def _setup_git_config(self, config):
        try:
            git.Git().config('--global', 'user.name', config['username'])
            git.Git().config('--global', 'user.email', config['email'])
        except Exception as e:
            print(f"Aviso: Não foi possível configurar Git globalmente: {e}")

    def _ensure_repository_exists(self, config):
        try:
            self.repo = self.github_client.get_repo(f"{config['username']}/{config['repo_name']}")
            print(f"✅ Repositório encontrado: {self.repo.html_url}")
        except Exception:
            print(f"📁 Criando repositório {config['repo_name']}...")
            self.repo = self.github_client.get_user().create_repo(
                name=config['repo_name'],
                description="Feeds RSS automatizados pelo NeuroDeamon",
                private=False,
                has_issues=True,
                has_projects=False,
                has_wiki=False
            )
            print(f"✅ Repositório criado: {self.repo.html_url}")

    def clone_or_pull_repo(self):
        if not os.path.exists(self.local_path) or not os.path.isdir(os.path.join(self.local_path, '.git')):
            print(f"📥 Clonando repositório...")
            os.makedirs(os.path.dirname(self.local_path), exist_ok=True)
            try:
                self.git_repo = git.Repo.clone_from(
                    self.repo.clone_url.replace('https://', f'https://{self.config["token"]}@'),
                    self.local_path
                )
                print("✅ Repositório clonado com sucesso")
                self._create_repository_structure()
            except git.exc.GitCommandError as e:
                print(f"❌ Erro ao clonar repositório: {e}")
                raise
        else:
            print(f"🔄 Atualizando repositório local...")
            self.git_repo = git.Repo(self.local_path)
            origin = self.git_repo.remotes.origin
            origin.pull()
            print("✅ Repositório atualizado")

    def _create_repository_structure(self):
        structure = {
            'README.md': '''# NeuroDeamon Feeds\n\nFeeds RSS automatizados para cursos, podcasts e conteúdo educacional.\n\n## Feeds Disponíveis\n\n- `cursos.xml` - Feed de cursos processados\n- `youtube.xml` - Feed de vídeos do YouTube\n- `podcasts.xml` - Feed de podcasts externos\n\n## Gerado automaticamente pelo NeuroDeamon Course Processor\n''',
            'assets/README.md': '''# Assets\n\nRecursos compartilhados para os feeds RSS.\n\n- Imagens de capa\n- Arquivos de estilo\n- Recursos estáticos\n''',
            '.gitignore': '''# Logs\n*.log\n\n# Temporary files\n*.tmp\n*.temp\n\n# OS generated files\n.DS_Store\nThumbs.db\n'''
        }
        
        for file_path, content in structure.items():
            full_path = os.path.join(self.local_path, file_path)
            if not os.path.exists(full_path):
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)

    def commit_and_push(self, files, message):
        try:
            self.clone_or_pull_repo()
            
            for local_file, repo_file in files.items():
                local_full_path = os.path.join(self.local_path, repo_file)
                os.makedirs(os.path.dirname(local_full_path), exist_ok=True)
                
                if os.path.exists(local_file):
                    shutil.copy2(local_file, local_full_path)
                    print(f"📄 Arquivo copiado: {repo_file}")
            
            self.git_repo.git.add(A=True)
            
            if self.git_repo.is_dirty():
                commit_msg = f"{message} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                self.git_repo.index.commit(commit_msg)
                print(f"💾 Commit realizado: {commit_msg}")
                
                origin = self.git_repo.remotes.origin
                origin.push()
                print("🚀 Push realizado com sucesso")
                
                self.db.log_operation(
                    course_id=None,
                    operation_type="github_commit",
                    details=f"Commit: {commit_msg}"
                )
                
                return True
            else:
                print("ℹ️ Nenhuma mudança detectada")
                return False
                
        except Exception as e:
            print(f"❌ Erro no commit/push: {e}")
            return False

    def update_course_feed(self, feed_path):
        if not os.path.exists(feed_path):
            print(f"❌ Feed não encontrado: {feed_path}")
            return False
        
        files = {
            feed_path: "cursos.xml"
        }
        
        return self.commit_and_push(files, "Atualização automática do feed de cursos")

    def deploy_course_feed(self, course_name, feed_path):
        print(f"🚀 Fazendo deploy do feed para GitHub...")
        
        success = self.update_course_feed(feed_path)
        
        if success:
            feed_url = f"https://raw.githubusercontent.com/{self.config['username']}/{self.config['repo_name']}/main/cursos.xml"
            self.db.save_setting('course_feed_url', feed_url)
            
            print(f"✅ Feed publicado em: {feed_url}")
            return feed_url
        else:
            print("❌ Falha no deploy do feed")
            return None

    def validate_setup(self):
        status = {
            'token_valid': False,
            'repo_accessible': False,
            'git_configured': False,
            'local_repo_ok': False
        }
        
        try:
            user = self.github_client.get_user()
            status['token_valid'] = True
            
            repo = self.github_client.get_repo(f"{user.login}/{self.repo_name}")
            status['repo_accessible'] = True
            
            git_config_user = git.Git().config('--get', 'user.name')
            git_config_email = git.Git().config('--get', 'user.email')
            status['git_configured'] = bool(git_config_user) and bool(git_config_email)
            
            if os.path.exists(self.local_path):
                repo = git.Repo(self.local_path)
                status['local_repo_ok'] = not repo.bare
            
        except Exception as e:
            print(f"Erro na validação: {e}")
        
        return status
