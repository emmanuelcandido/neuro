import xml.etree.ElementTree as ET
from datetime import datetime
import os
import shutil
import json

class XMLService:
    def __init__(self, db_service):
        self.db = db_service
        self.feed_path = "github/neurodeamon-feeds/cursos.xml"
        self.feed_config = self._load_feed_config()
        os.makedirs(os.path.dirname(self.feed_path), exist_ok=True)
    
    def _load_feed_config(self):
        config_path = "config/feed_config.json"
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        print("🎙️ Configuração do Feed RSS")
        print("=" * 50)
        
        config = {
            'title': input("Nome do podcast: "),
            'description': input("Descrição do podcast: "),
            'image_url': input("URL da capa (opcional): "),
            'website': input("Website (opcional): "),
            'language': 'pt-BR',
            'category': 'Education'
        }
        
        os.makedirs('config', exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return config

    def _create_base_feed(self):
        rss = ET.Element("rss", version="2.0")
        rss.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
        rss.set("xmlns:content", "http://purl.org/rss/1.0/modules/content/")
        
        channel = ET.SubElement(rss, "channel")
        
        ET.SubElement(channel, "title").text = self.feed_config['title']
        ET.SubElement(channel, "description").text = self.feed_config['description']
        ET.SubElement(channel, "language").text = self.feed_config.get('language', 'pt-BR')
        ET.SubElement(channel, "lastBuildDate").text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        
        ET.SubElement(channel, "itunes:category", text=self.feed_config.get('category', 'Education'))
        ET.SubElement(channel, "itunes:explicit").text = "false"
        
        if self.feed_config.get('image_url'):
            image = ET.SubElement(channel, "image")
            ET.SubElement(image, "url").text = self.feed_config['image_url']
            ET.SubElement(image, "title").text = self.feed_config['title']
            ET.SubElement(image, "link").text = self.feed_config.get('website', '')
        
        return rss, channel

    def _create_episode_xml(self, course_data):
        item = ET.Element("item")
        
        ET.SubElement(item, "title").text = course_data['title']
        ET.SubElement(item, "pubDate").text = course_data['pub_date']
        ET.SubElement(item, "guid").text = course_data['audio_url']
        
        description_content = self._format_description(course_data)
        description = ET.SubElement(item, "description")
        description.text = description_content
        
        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", course_data['audio_url'])
        enclosure.set("type", "audio/mpeg")
        enclosure.set("length", str(course_data['file_size']))
        
        ET.SubElement(item, "itunes:duration").text = self._format_duration(course_data['duration'])
        ET.SubElement(item, "itunes:explicit").text = "false"
        
        return item

    def _format_description(self, course_data):
        timestamps = "\n".join([
            f"{ts['time']} - {ts['title']}" 
            for ts in course_data.get('timestamps', [])
        ])
        
        links = "\n".join([
            f"• {link['title']}: {link['url']}"
            for link in course_data.get('links', [])
        ]) if course_data.get('links') else "Nenhum link adicional"
        
        return f"""<![CDATA[
⏱️ Timestamps
{timestamps}

🌐 Links
{links}

📝 Descrição
{course_data.get('description', 'Curso processado automaticamente')}
]]>"""

    def _format_duration(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def create_or_update_feed(self, course_data):
        self._backup_feed()
        
        try:
            if os.path.exists(self.feed_path):
                tree = ET.parse(self.feed_path)
                rss = tree.getroot()
                channel = rss.find("channel")
            else:
                rss, channel = self._create_base_feed()
            
            existing_guids = [item.find("guid").text for item in channel.findall("item")]
            if course_data['audio_url'] not in existing_guids:
                episode = self._create_episode_xml(course_data)
                
                items = channel.findall("item")
                if items:
                    channel.insert(list(channel).index(items[0]), episode)
                else:
                    channel.append(episode)
                
                last_build = channel.find("lastBuildDate")
                if last_build is not None:
                    last_build.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            
            os.makedirs(os.path.dirname(self.feed_path), exist_ok=True)
            tree = ET.ElementTree(rss)
            tree.write(self.feed_path, encoding='utf-8', xml_declaration=True)
            
            if self.validate_feed():
                print(f"✅ Feed RSS atualizado: {self.feed_path}")
                return True
            else:
                print("❌ Feed RSS inválido, restaurando backup")
                self._restore_backup()
                return False
                
        except Exception as e:
            print(f"❌ Erro ao atualizar feed: {e}")
            self._restore_backup()
            return False

    def _backup_feed(self):
        if os.path.exists(self.feed_path):
            backup_path = f"{self.feed_path}.backup"
            shutil.copy2(self.feed_path, backup_path)

    def _restore_backup(self):
        backup_path = f"{self.feed_path}.backup"
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, self.feed_path)

    def validate_feed(self):
        try:
            ET.parse(self.feed_path)
            return True
        except ET.ParseError as e:
            print(f"XML inválido: {e}")
            return False
