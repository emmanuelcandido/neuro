import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED
from rich.align import Align
from pyfiglet import Figlet

console = Console(quiet=False, stderr=False)

class MenuRenderer:
    def __init__(self):
        self.main_menu_options = [
            {"id": "1", "name": "Course Processor", "category": "Media", "emoji": "🎓"},
            {"id": "2", "name": "YouTube Manager", "category": "Media", "emoji": "📹"},
            {"id": "3", "name": "Feed", "category": "Media", "emoji": "📡"},
            {"id": "4", "name": "Snipd", "category": "Media", "emoji": "✂️"},
            {"id": "5", "name": "Manage Obsidian Vault", "category": "Notes", "emoji": "🧠"},
            {"id": "6", "name": "Authors", "category": "Notes", "emoji": "👥"},
            {"id": "7", "name": "Questions", "category": "Notes", "emoji": "❓"},
            {"id": "8", "name": "Wiki", "category": "Notes", "emoji": "📚"},
            {"id": "9", "name": "Settings", "category": "Configuration", "emoji": "🔧"},
            {"id": "10", "name": "Monitor", "category": "Information", "emoji": "📈"},
            {"id": "11", "name": "Logs", "category": "Information", "emoji": "📋"},
            {"id": "12", "name": "Exit", "category": "Information", "emoji": "🚪"},
        ]

        self.course_processor_menu_options = [
            {"id": "1", "name": "Process Complete Course", "category": "Core Processing", "emoji": "📁"},
            {"id": "2", "name": "Convert Courses to Audio", "category": "Individual Operations", "emoji": "🎬"},
            {"id": "3", "name": "Transcribe Audio Files", "category": "Individual Operations", "emoji": "📝"},
            {"id": "4", "name": "Generate AI Course Summaries", "category": "Individual Operations", "emoji": "🤖"},
            {"id": "5", "name": "Create Unified Audio", "category": "Individual Operations", "emoji": "🎵"},
            {"id": "6", "name": "Generate Timestamps Only", "category": "Individual Operations", "emoji": "⏱️"},
            {"id": "7", "name": "Generate Course TTS Audio Notes", "category": "Individual Operations", "emoji": "🎙️"},
            {"id": "8", "name": "Upload Course to Google Drive", "category": "Cloud & Distribution", "emoji": "📤"},
            {"id": "9", "name": "Update courses.xml", "category": "Cloud & Distribution", "emoji": "📋"},
            {"id": "10", "name": "Update GitHub Repository", "category": "Cloud & Distribution", "emoji": "🔄"},
            {"id": "11", "name": "Course Status Check", "category": "Course Management", "emoji": "📋"},
            {"id": "12", "name": "Forget Course", "category": "Course Management", "emoji": "🗑️"},
            {"id": "13", "name": "Clear All Data", "category": "Course Management", "emoji": "🗑️"},
            {"id": "0", "name": "Back to Main Menu", "category": "", "emoji": "⬅️"},
        ]

        self.settings_menu_options = [
            {"id": "1", "name": "API Keys & Validation", "category": "General Settings", "emoji": "🔑"},
            {"id": "2", "name": "Voice Settings", "category": "General Settings", "emoji": "🎙️"},
            {"id": "3", "name": "Output Directory", "category": "General Settings", "emoji": "📁"},
            {"id": "4", "name": "GitHub Repository", "category": "General Settings", "emoji": "🗂️"},
            {"id": "5", "name": "Cleanup Tools", "category": "General Settings", "emoji": "🧹"},
            {"id": "6", "name": "Processing Preferences", "category": "Course Processor", "emoji": "🎯"},
            {"id": "0", "name": "Back to Main Menu", "category": "", "emoji": "⬅️"},
        ]

    def _render_main_title(self, app_name: str):
        os.system('cls' if os.name == 'nt' else 'clear')
        figlet = Figlet(font="big")
        art = figlet.renderText(app_name)
        centered_art = Align.center(Text(art, style="bold bright_cyan"))
        console.print(centered_art)
        console.print()

    def _render_submenu_header(self, menu_name: str, emoji: str = "⚙️"):
        os.system('cls' if os.name == 'nt' else 'clear')
        header = f"{emoji} {menu_name}"
        console.print(f"\n[bold bright_cyan]{header}[/]")
        console.print("[bright_blue]" + "─" * len(header) + "[/]")
        console.print()

    def _create_menu_panel(self, content: str, title: str) -> Panel:
        return Panel(
            content,
            title=f"[bold bright_blue]{title}[/]",
            border_style="bright_blue",
            box=ROUNDED,
            padding=(1, 2)
        )

    def _render_menu_options(self, options):
        menu_text = Text()
        current_category = ""
        for option in options:
            if option["category"] and option["category"] != current_category:
                menu_text.append(Text(f"\n{option['category']}\n", style="bold bright_white"))
                current_category = option["category"]
            
            menu_text.append(Text(f"[{option['id']}] {option['emoji']} {option['name']}\n", style="bright_white"))
        return menu_text

    def _get_menu_choice(self, prompt: str = "Enter your choice", show_back: bool = True) -> str:
        try:
            if show_back:
                choice = console.input(f"\n[bold bright_white]➤ {prompt} (0 or ESC to go back): [/]").strip()
            else:
                choice = console.input(f"\n[bold bright_white]➤ {prompt}: [/]").strip()
            return choice
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bright_yellow]⚠️ Returning to previous menu...[/]")
            return "0"

    def show_main_menu(self):
        self._render_main_title("Neuro")
        menu_content = self._render_menu_options(self.main_menu_options)
        console.print(self._create_menu_panel(menu_content, "Functions"))
        return self._get_menu_choice()

    def show_course_processor_menu(self):
        self._render_submenu_header("COURSE PROCESSOR", "🎓")
        menu_content = self._render_menu_options(self.course_processor_menu_options)
        console.print(self._create_menu_panel(menu_content, "🎯 Core Processing"))
        return self._get_menu_choice()

    def show_settings_menu(self):
        self._render_submenu_header("CONFIGURAÇÕES", "⚙️")
        menu_content = self._render_menu_options(self.settings_menu_options)
        console.print(self._create_menu_panel(menu_content, "🌐 Configurações Gerais"))
        return self._get_menu_choice()