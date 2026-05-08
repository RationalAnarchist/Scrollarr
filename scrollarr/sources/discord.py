import re
import os
import requests
import tempfile
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime
from ..core_logic import BaseSource
from ..config import config_manager

class DiscordSource(BaseSource):
    key = "discord"
    name = "Discord Channel"
    is_enabled_by_default = True

    def identify(self, url: str) -> bool:
        return url.startswith("discord://")

    def _get_token(self):
        return os.getenv('DISCORD_TOKEN', config_manager.get('discord_bot_token', ''))

    def _get_headers(self):
        token = self._get_token()
        if not token:
            raise ValueError("DISCORD_TOKEN environment variable or discord_bot_token config is not set. Please set it to use the Discord source.")
        return {"Authorization": f"Bot {token}"}

    def get_metadata(self, url: str) -> Dict:
        match = re.search(r'discord://(\d+)', url)
        if not match:
            return {'title': 'Invalid Discord URL', 'author': 'Unknown'}
        
        channel_id = match.group(1)
        try:
            res = requests.get(f"https://discord.com/api/v10/channels/{channel_id}", headers=self._get_headers())
            if res.status_code == 200:
                data = res.json()
                channel_name = data.get('name', channel_id)
                return {
                    'title': f"#{channel_name}",
                    'author': 'Discord Bot',
                    'description': data.get('topic', f"Automated EPUB downloads from Discord channel #{channel_name}"),
                    'cover_url': None,
                    'tags': ['discord'],
                    'rating': None,
                    'language': 'English',
                    'publication_status': 'Ongoing'
                }
        except Exception as e:
            print(f"Error fetching Discord metadata: {e}")
            
        return {'title': f"Discord Channel {channel_id}", 'author': 'Unknown'}

    def get_chapter_list(self, url: str, **kwargs) -> List[Dict]:
        match = re.search(r'discord://(\d+)', url)
        if not match:
            return []
        
        channel_id = match.group(1)
        last_chapter = kwargs.get('last_chapter')
        last_msg_id = None
        if last_chapter and last_chapter.get('url'):
            url_match = re.search(r'discord://\d+/(\d+)', last_chapter['url'])
            if url_match:
                last_msg_id = url_match.group(1)

        chapters = []
        api_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        params = {'limit': 50}
        
        has_more = True
        before_id = None
        
        while has_more:
            if before_id:
                params['before'] = before_id
                
            try:
                res = requests.get(api_url, headers=self._get_headers(), params=params)
                if res.status_code != 200:
                    print(f"Discord API Error: {res.status_code} {res.text}")
                    break
                    
                messages = res.json()
                if not messages:
                    break
                    
                for msg in messages:
                    msg_id = msg['id']
                    if msg_id == last_msg_id:
                        has_more = False
                        break
                        
                    for attachment in msg.get('attachments', []):
                        if attachment['filename'].endswith('.epub'):
                            pub_date = None
                            try:
                                # Example: 2024-10-10T12:00:00.000000+00:00
                                pub_str = msg.get('timestamp', '').split('+')[0]
                                if '.' in pub_str:
                                    pub_date = datetime.strptime(pub_str, "%Y-%m-%dT%H:%M:%S.%f")
                                else:
                                    pub_date = datetime.strptime(pub_str, "%Y-%m-%dT%H:%M:%S")
                            except Exception as e:
                                pass
                                
                            chapters.append({
                                'title': attachment['filename'].replace('.epub', ''),
                                'url': f"discord://{channel_id}/{msg_id}",
                                'published_date': pub_date
                            })
                            
                before_id = messages[-1]['id']
                if not has_more or len(messages) < 50:
                    break
                    
            except Exception as e:
                print(f"Error fetching Discord messages: {e}")
                break

        # Messages are newest to oldest, reverse to get chronological order
        chapters.reverse()
        return chapters

    def _extract_epub_content(self, path):
        try:
            book = epub.read_epub(path, options={'ignore_ncx': True})
            html_parts = []
            for item_id, _ in book.spine:
                item = book.get_item_with_id(item_id)
                if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
                    content = item.get_content()
                    soup = BeautifulSoup(content, 'html.parser')
                    body = soup.body
                    if body:
                        html_parts.append(body.decode_contents())
                    else:
                        html_parts.append(soup.decode_contents())
            return "".join(html_parts)
        except Exception as e:
            print(f"Error extracting EPUB: {e}")
            return f"<p>Error extracting EPUB: {e}</p>"

    def get_chapter_content(self, chapter_url: str) -> str:
        match = re.search(r'discord://(\d+)/(\d+)', chapter_url)
        if not match:
            return "<p>Invalid Discord Chapter URL</p>"
            
        channel_id, msg_id = match.groups()
        
        try:
            # 1. Fetch the message to get the fresh attachment URL
            res = requests.get(f"https://discord.com/api/v10/channels/{channel_id}/messages/{msg_id}", headers=self._get_headers())
            if res.status_code != 200:
                return f"<p>Failed to fetch message from Discord: {res.status_code}</p>"
                
            msg = res.json()
            epub_url = None
            for attachment in msg.get('attachments', []):
                if attachment['filename'].endswith('.epub'):
                    epub_url = attachment['url']
                    break
                    
            if not epub_url:
                return "<p>No EPUB attachment found in this message.</p>"
                
            # 2. Download the EPUB
            file_res = requests.get(epub_url)
            if file_res.status_code != 200:
                return f"<p>Failed to download EPUB from Discord CDN: {file_res.status_code}</p>"
                
            # 3. Save to temp and extract HTML
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".epub")
            os.close(tmp_fd)
            try:
                with open(tmp_path, 'wb') as f:
                    f.write(file_res.content)
                
                content = self._extract_epub_content(tmp_path)
                if not content:
                    content = "<p>Extracted EPUB was empty.</p>"
                return content
            finally:
                os.remove(tmp_path)
                
        except Exception as e:
            return f"<p>Error processing Discord chapter: {e}</p>"

    def search(self, query: str) -> List[Dict]:
        return []
