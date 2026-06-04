import re
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from ..core_logic import BaseSource
from ..browser_manager import BrowserManager

logger = logging.getLogger(__name__)

class PatreonSource(BaseSource):
    key = "patreon"
    name = "Patreon"
    is_enabled_by_default = False

    def __init__(self):
        self.cookies = []

    def identify(self, url: str) -> bool:
        return 'patreon.com' in url

    def set_config(self, config: Dict):
        self.cookies = []
        if not config:
            return

        session_id = config.get('session_id')
        if session_id:
            self.cookies.append({
                'name': 'session_id',
                'value': session_id,
                'domain': '.patreon.com',
                'path': '/'
            })

        cookies_str = config.get('cookies')
        if cookies_str:
            for pair in cookies_str.split(';'):
                if '=' in pair:
                    k, v = pair.strip().split('=', 1)
                    # Deduplicate session_id if both are provided
                    if any(c['name'] == k for c in self.cookies):
                        continue
                    self.cookies.append({
                        'name': k,
                        'value': v,
                        'domain': '.patreon.com',
                        'path': '/'
                    })

    def _get_page(self):
        page = BrowserManager.get_page()
        if self.cookies:
            try:
                page.context.add_cookies(self.cookies)
            except Exception as e:
                logger.error(f"Failed to add Patreon cookies to page context: {e}")
        return page

    def _extract_campaign_id(self, html: str) -> Optional[str]:
        # Try finding standard patreon-media campaign link
        match = re.search(r'patreon-media/p/campaign/(\d+)', html)
        if match:
            return match.group(1)

        # Fallback to general campaign/digits
        match = re.search(r'campaign/(\d+)', html)
        if match:
            return match.group(1)

        return None

    def get_metadata(self, url: str) -> Dict:
        page = self._get_page()
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Extract Creator Name / Title
            og_title = soup.find('meta', property='og:title')
            title = og_title['content'] if og_title else "Patreon Creator"
            # Strip "is creating..." or "on Patreon" if present
            if " is creating " in title:
                title = title.split(" is creating ")[0].strip()
            elif " | Patreon" in title:
                title = title.split(" | Patreon")[0].strip()

            # Description
            og_desc = soup.find('meta', property='og:description')
            description = og_desc['content'] if og_desc else "No description available."

            # Cover Photo / Avatar
            og_image = soup.find('meta', property='og:image')
            cover_url = og_image['content'] if og_image else None

            return {
                'title': title,
                'author': title,
                'description': description,
                'cover_url': cover_url,
                'tags': None,
                'rating': None,
                'language': 'English',
                'publication_status': 'Ongoing'
            }
        except Exception as e:
            logger.error(f"Error fetching Patreon metadata for {url}: {e}")
            raise e

    def get_chapter_list(self, url: str, **kwargs) -> List[Dict]:
        page = self._get_page()
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            html = page.content()

            campaign_id = self._extract_campaign_id(html)
            if not campaign_id:
                logger.error(f"Could not find Patreon campaign ID in page {url}")
                return []

            logger.info(f"Patreon campaign ID: {campaign_id}")
            posts = []

            # Paginate through Patreon posts API
            posts_url = f"/api/posts?filter[campaign_id]={campaign_id}&filter[is_draft]=false&sort=-published_at"

            while posts_url:
                response_data = page.evaluate(f"""
                    async () => {{
                        try {{
                            const response = await fetch('{posts_url}');
                            if (!response.ok) {{
                                return {{ error: 'HTTP error', status: response.status, text: await response.text().then(t => t.slice(0, 200)) }};
                            }}
                            return await response.json();
                        }} catch (e) {{
                            return {{ error: e.toString() }};
                        }}
                    }}
                """)

                if 'error' in response_data:
                    logger.error(f"Patreon API returned error in get_chapter_list: {response_data.get('error')} (Status: {response_data.get('status')}, Text: {response_data.get('text')})")
                    break

                if 'data' not in response_data:
                    break

                for post in response_data['data']:
                    attrs = post.get('attributes', {})
                    title = attrs.get('title')
                    post_id = post.get('id')
                    chapter_url = f"https://www.patreon.com/posts/{post_id}"
                    
                    published_str = attrs.get('published_at')
                    published_date = None
                    if published_str:
                        try:
                            # Parse ISO format: 2026-06-01T05:42:44.000+00:00
                            # Strip milliseconds and timezone for datetime.strptime simplicity
                            base_str = published_str.split('.')[0]
                            published_date = datetime.strptime(base_str, "%Y-%m-%dT%H:%M:%S")
                        except Exception as date_err:
                            logger.warning(f"Failed to parse Patreon post date {published_str}: {date_err}")

                    # Determine access
                    can_view = attrs.get('current_user_can_view', False)

                    posts.append({
                        'title': title,
                        'url': chapter_url,
                        'published_date': published_date,
                        'has_access': can_view
                    })

                # Check for next page
                next_link = response_data.get('links', {}).get('next')
                if next_link:
                    if 'patreon.com' in next_link:
                        idx = next_link.find('/api/')
                        if idx != -1:
                            posts_url = next_link[idx:]
                        else:
                            posts_url = None
                    else:
                        posts_url = next_link
                else:
                    posts_url = None

            # Sort chapters by published date ASC (oldest first)
            posts.sort(key=lambda x: x['published_date'] or datetime.min)
            return posts

        except Exception as e:
            logger.error(f"Error fetching Patreon post list for {url}: {e}")
            return []

    def get_chapter_content(self, chapter_url: str) -> str:
        page = self._get_page()
        try:
            # Construct the API detail URL
            post_id_match = re.search(r'/posts/.*?(\d+)', chapter_url)
            if not post_id_match:
                # Try generic digits check
                post_id_match = re.search(r'/posts/(\d+)', chapter_url)

            if not post_id_match:
                logger.error(f"Could not extract Patreon post ID from URL: {chapter_url}")
                return ""

            post_id = post_id_match.group(1)
            detail_url = f"/api/posts/{post_id}"

            # Go to the base page to establish session/cookies context
            # We navigate to the actual post URL first
            page.goto(chapter_url, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            # Fetch specific post detail via API using the page session
            response_data = page.evaluate(f"""
                async () => {{
                    try {{
                        const response = await fetch('{detail_url}');
                        if (!response.ok) {{
                            return {{ error: 'HTTP error', status: response.status, text: await response.text().then(t => t.slice(0, 200)) }};
                        }}
                        return await response.json();
                    }} catch (e) {{
                        return {{ error: e.toString() }};
                    }}
                }}
            """)

            if 'error' in response_data:
                logger.error(f"Patreon API returned error in get_chapter_content: {response_data.get('error')} (Status: {response_data.get('status')}, Text: {response_data.get('text')})")
                return f"<p><strong>[Fetch Error]</strong> Failed to retrieve content from Patreon (Status: {response_data.get('status')}).</p>"

            data = response_data.get('data', {})
            attrs = data.get('attributes', {})

            if not attrs.get('current_user_can_view', False):
                return "<p><strong>[Content Locked]</strong> You do not have access to this paywalled Patreon post.</p>"

            # Process HTML content if present, or parse content_json_string
            content_html = attrs.get('content')
            if not content_html:
                json_string = attrs.get('content_json_string')
                if json_string:
                    try:
                        content_doc = json.loads(json_string)
                        content_html = self._prosemirror_to_html(content_doc)
                    except Exception as json_err:
                        logger.error(f"Failed to parse content_json_string for post {post_id}: {json_err}")

            if not content_html:
                content_html = "<p>No text content available in this post.</p>"

            # Handle attachments (e.g. image URLs or other media links)
            included = response_data.get('included', [])
            attachments_html = ""
            for item in included:
                if item.get('type') == 'attachment':
                    att_attrs = item.get('attributes', {})
                    name = att_attrs.get('name')
                    att_url = att_attrs.get('url')
                    if att_url:
                        attachments_html += f'<p><strong>Attachment:</strong> <a href="{att_url}">{name}</a></p>'

            # Combine content and attachments
            if attachments_html:
                content_html = f"{content_html}<hr/>{attachments_html}"

            return content_html

        except Exception as e:
            logger.error(f"Error fetching Patreon post content for {chapter_url}: {e}")
            return ""

    def search(self, query: str) -> List[Dict]:
        # Searching Patreon creators
        page = self._get_page()
        try:
            search_url = f"https://www.patreon.com/search?q={query}"
            page.goto(search_url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            results = []
            # Parse search results
            # Note: Patreon search uses a dynamic API.
            # As search is less critical for syncing, we can extract creators matching query if any are visible,
            # or return empty if none can be found easily.
            # Let's look for search cards:
            for card in soup.select('a[href^="https://www.patreon.com/"]'):
                href = card.get('href')
                # Exclude standard links
                if any(x in href for x in ['/home', '/login', '/signup', '/search', '/create', '/policy']):
                    continue
                name_tag = card.find('h3') or card.find('span')
                if name_tag:
                    name = name_tag.get_text(strip=True)
                    if name and query.lower() in name.lower() and href not in [r['url'] for r in results]:
                        results.append({
                            'title': name,
                            'url': href,
                            'author': name,
                            'cover_url': None,
                            'provider': 'Patreon'
                        })
            return results
        except Exception as e:
            logger.error(f"Patreon search failed: {e}")
            return []

    def _prosemirror_to_html(self, doc) -> str:
        if not doc:
            return ""
        if isinstance(doc, str):
            try:
                doc = json.loads(doc)
            except Exception:
                return doc
        if not isinstance(doc, dict):
            return ""

        node_type = doc.get("type")

        if node_type == "doc":
            html = ""
            for child in doc.get("content", []):
                html += self._prosemirror_to_html(child)
            return html

        elif node_type == "paragraph":
            child_html = ""
            for child in doc.get("content", []):
                child_html += self._prosemirror_to_html(child)
            return f"<p>{child_html}</p>"

        elif node_type == "heading":
            level = doc.get("attrs", {}).get("level", 1)
            child_html = ""
            for child in doc.get("content", []):
                child_html += self._prosemirror_to_html(child)
            return f"<h{level}>{child_html}</h{level}>"

        elif node_type == "bulletList":
            child_html = ""
            for child in doc.get("content", []):
                child_html += self._prosemirror_to_html(child)
            return f"<ul>{child_html}</ul>"

        elif node_type == "orderedList":
            child_html = ""
            for child in doc.get("content", []):
                child_html += self._prosemirror_to_html(child)
            return f"<ol>{child_html}</ol>"

        elif node_type == "listItem":
            child_html = ""
            for child in doc.get("content", []):
                child_html += self._prosemirror_to_html(child)
            return f"<li>{child_html}</li>"

        elif node_type == "text":
            text = doc.get("text", "")
            for mark in doc.get("marks", []):
                mark_type = mark.get("type")
                if mark_type == "bold":
                    text = f"<strong>{text}</strong>"
                elif mark_type == "italic":
                    text = f"<em>{text}</em>"
                elif mark_type == "underline":
                    text = f"<u>{text}</u>"
                elif mark_type == "strike":
                    text = f"<s>{text}</s>"
                elif mark_type == "link":
                    href = mark.get("attrs", {}).get("href", "#")
                    text = f'<a href="{href}">{text}</a>'
            return text

        elif node_type == "hardBreak":
            return "<br/>"

        elif node_type == "horizontalRule":
            return "<hr/>"

        elif "content" in doc:
            child_html = ""
            for child in doc.get("content", []):
                child_html += self._prosemirror_to_html(child)
            return child_html

        return ""
