import re
import urllib.parse
from typing import List, Dict, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import zipfile
import io
from ..core_logic import BaseSource

class FanFictionSource(BaseSource):
    key = "fanfiction"
    name = "FanFiction.net / FictionPress"
    is_enabled_by_default = True

    # Class-level cache to hold fetched HTML content from Fichub
    _fichub_cache = {}

    def identify(self, url: str) -> bool:
        return 'fanfiction.net' in url or 'fictionpress.com' in url

    def _get_fichub_meta(self, url: str) -> Optional[Dict]:
        api_url = "https://fichub.net/api/v0/epub"
        headers = {"User-Agent": "Scrollarr/1.0"}
        res = requests.get(api_url, params={"q": url}, headers=headers)
        if res.status_code == 200:
            return res.json()
        return None

    def get_metadata(self, url: str) -> Dict:
        data = self._get_fichub_meta(url)
        if not data or 'meta' not in data:
            return {'title': 'Unknown', 'author': 'Unknown'}

        meta = data['meta']
        title = meta.get('title', 'Unknown Title')
        author = meta.get('author', 'Unknown Author')
        description = meta.get('description', 'No description available.')
        
        # Remove HTML tags from description if needed, or leave it
        if description.startswith('<p>'):
            soup = BeautifulSoup(description, 'html.parser')
            description = soup.get_text(strip=True)

        cover_url = None # Fichub doesn't seem to reliably provide cover images for FFnet
        publication_status = "Completed" if meta.get('status') == 'complete' else "Ongoing"
        
        rating = None
        if 'rawExtendedMeta' in meta and 'rated' in meta['rawExtendedMeta']:
            rating = meta['rawExtendedMeta']['rated']
            
        language = "English"
        if 'rawExtendedMeta' in meta and 'language' in meta['rawExtendedMeta']:
            language = meta['rawExtendedMeta']['language']

        return {
            'title': title,
            'author': author,
            'description': description,
            'cover_url': cover_url,
            'tags': None,
            'rating': rating,
            'language': language,
            'publication_status': publication_status
        }

    def get_chapter_list(self, url: str, **kwargs) -> List[Dict]:
        data = self._get_fichub_meta(url)
        if not data or 'meta' not in data:
            return []

        meta = data['meta']
        chapters_count = meta.get('chapters', 1)
        
        chapters = []
        match = re.search(r'/s/(\d+)', url)
        story_id = match.group(1) if match else "1"
        domain = "https://www.fanfiction.net" if "fanfiction.net" in url else "https://www.fictionpress.com"
        
        # Try to parse published/updated
        published_date = None
        updated_date = None
        try:
            if meta.get('created'):
                published_date = datetime.fromisoformat(meta['created'])
            if meta.get('updated'):
                updated_date = datetime.fromisoformat(meta['updated'])
        except:
            pass

        for i in range(1, chapters_count + 1):
            chap_url = f"{domain}/s/{story_id}/{i}"
            chap = {
                'title': f'Chapter {i}',
                'url': chap_url,
                'published_date': published_date if i == 1 else None
            }
            if i == chapters_count and chapters_count > 1 and updated_date:
                chap['published_date'] = updated_date
            chapters.append(chap)

        return chapters

    def get_chapter_content(self, chapter_url: str) -> str:
        match = re.search(r'/s/(\d+)', chapter_url)
        if not match:
            return "<p>Error: Invalid chapter URL</p>"
        story_id = match.group(1)
        
        chap_match = re.search(r'/s/\d+/(\d+)', chapter_url)
        chapter_idx = int(chap_match.group(1)) if chap_match else 1

        if story_id not in self._fichub_cache:
            # Fetch from Fichub
            data = self._get_fichub_meta(chapter_url)
            if not data or 'html_url' not in data:
                return "<p>Error: Could not retrieve from Fichub.</p>"
            
            html_url = "https://fichub.net" + data['html_url']
            res = requests.get(html_url, headers={"User-Agent": "Scrollarr/1.0"})
            if res.status_code != 200:
                return "<p>Error: Could not download Fichub HTML zip.</p>"
            
            # Unzip
            with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                # Expecting one html file
                names = [n for n in z.namelist() if n.endswith('.html')]
                if not names:
                    return "<p>Error: No HTML file in Fichub zip.</p>"
                
                with z.open(names[0]) as f:
                    soup = BeautifulSoup(f.read(), 'html.parser')
                    
                    # Fichub HTML structure: <h1>Title</h1> <h2>by Author</h2> <h2>Chapter 1</h2> <p>...</p> <h2>Chapter 2</h2> ...
                    # We can split elements based on <h2>
                    chapters_dict = {}
                    for h2 in soup.find_all('h2'):
                        text = h2.get_text(strip=True).lower()
                        if text.startswith('chapter '):
                            try:
                                num_str = text.replace('chapter ', '').split()[0]
                                current_idx = int(num_str)
                            except:
                                continue
                            
                            parent = h2.parent
                            if parent and parent.name == 'div':
                                chapters_dict[current_idx] = str(parent)
                            else:
                                # Fallback: collect siblings until next h2
                                content = [str(h2)]
                                node = h2.next_sibling
                                while node and getattr(node, 'name', '') != 'h2':
                                    content.append(str(node))
                                    node = node.next_sibling
                                chapters_dict[current_idx] = "".join(content)
                        
                    # If it's a single chapter story, there might not be a "Chapter 1" h2.
                    if not chapters_dict:
                        # Grab everything after h1 and h2(by Author)
                        content = []
                        past_header = False
                        for child in soup.body.children:
                            if child.name == 'h2' and getattr(child, 'text', '').startswith('by'):
                                past_header = True
                                continue
                            if past_header:
                                content.append(str(child))
                        chapters_dict[1] = "".join(content)

                    self._fichub_cache[story_id] = chapters_dict

        chapter_html = self._fichub_cache.get(story_id, {}).get(chapter_idx)
        if not chapter_html:
            return f"<p>Chapter {chapter_idx} content not found in Fichub export.</p>"
        
        return chapter_html

    def search(self, query: str) -> List[Dict]:
        # Search using DuckDuckGo Lite since FFN search is Cloudflare-blocked
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        url = "https://lite.duckduckgo.com/lite/"
        # Prioritize fanfiction.net
        data = {"q": f"site:fanfiction.net {query}"}
        res = requests.post(url, headers=headers, data=data)
        
        results = []
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            seen_urls = set()
            for a in soup.select('a.result-url'):
                href = a.get('href', '')
                title_text = a.get_text(strip=True)
                
                if 'fanfiction.net/s/' in href:
                    # Clean URL to base story url: https://www.fanfiction.net/s/12345/1/
                    match = re.search(r'(https?://(?:www\.)?fanfiction\.net/s/\d+)(?:/.*)?', href)
                    if match:
                        base_url = match.group(1) + "/1"
                        if base_url not in seen_urls:
                            seen_urls.add(base_url)
                            # Clean up title (remove "Chapter X" or ", a Stargate: SG-1 ...")
                            title = re.sub(r' Chapter \d+,.*$', '', title_text)
                            title = re.sub(r' \| FanFiction$', '', title)
                            
                            results.append({
                                'title': title,
                                'url': base_url,
                                'author': 'Unknown', # DDG doesn't cleanly provide author
                                'cover_url': None,
                                'provider': 'FanFiction.net'
                            })
        return results
