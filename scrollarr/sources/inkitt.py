import re
import time
import subprocess
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from ..core_logic import BaseSource

class InkittSource(BaseSource):
    key = "inkitt"
    name = "Inkitt"
    is_enabled_by_default = True

    def identify(self, url: str) -> bool:
        return 'inkitt.com' in url

    def _get_playwright(self):
        try:
            from playwright.sync_api import sync_playwright
            return sync_playwright()
        except ImportError:
            raise ImportError("Playwright is not installed. Please install it to use Inkitt source.")

    def _ensure_browser_installed(self):
        """Attempts to install Playwright browsers if missing."""
        print("Playwright browsers not found. Installing...")
        try:
            subprocess.run(["playwright", "install", "chromium"], check=True)
            print("Playwright browsers installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install Playwright browsers: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error installing Playwright browsers: {e}")
            raise

    def get_metadata(self, url: str) -> Dict:
        with self._get_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as e:
                if "Executable doesn't exist" in str(e):
                    self._ensure_browser_installed()
                    browser = p.chromium.launch(headless=True)
                else:
                    raise e

            page = browser.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded")
                try:
                    page.wait_for_selector('h1', timeout=15000)
                except:
                    pass

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Title
                title = "Unknown Title"
                h1 = soup.select_one('h1')
                if h1:
                    title = h1.get_text(strip=True)

                # Author
                author = "Unknown Author"
                author_link = soup.select_one('a[href^="/users/"]') # Inkitt user links
                if not author_link:
                     # Check meta author
                     meta_author = soup.find('meta', attrs={'name': 'author'})
                     if meta_author:
                         author = meta_author.get('content')
                else:
                    author = author_link.get_text(strip=True)

                # Description
                description = "No description available."
                desc_div = soup.select_one('.story-summary')
                if not desc_div:
                     desc_div = soup.select_one('.summary')

                if desc_div:
                    description = desc_div.get_text(strip=True)
                else:
                    og_desc = soup.find('meta', property='og:description')
                    if og_desc:
                        description = og_desc.get('content', '')

                # Cover
                cover_url = None
                cover_img = soup.select_one('.story-cover img')
                if cover_img:
                    cover_url = cover_img.get('src')
                else:
                    og_image = soup.find('meta', property='og:image')
                    if og_image:
                        cover_url = og_image.get('content')

                # Tags / Genres
                tags = []
                for tag in soup.select('a[href^="/genres/"]'):
                    tags.append(tag.get_text(strip=True))

                for tag in soup.select('a[href^="/tags/"]'):
                    tags.append(tag.get_text(strip=True))

                # Status
                publication_status = "Ongoing"
                if "Completed" in soup.get_text():
                    publication_status = "Completed"

                return {
                    'title': title,
                    'author': author,
                    'description': description,
                    'cover_url': cover_url,
                    'tags': ", ".join(tags) if tags else None,
                    'rating': None,
                    'language': "English",
                    'publication_status': publication_status
                }
            finally:
                browser.close()

    def get_chapter_list(self, url: str, **kwargs) -> List[Dict]:
        with self._get_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as e:
                if "Executable doesn't exist" in str(e):
                    self._ensure_browser_installed()
                    browser = p.chromium.launch(headless=True)
                else:
                    raise e

            page = browser.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded")

                # Inkitt usually lists chapters on the story page or a "Read" button leads to first chapter
                # and then there is a chapter navigation menu.

                # Try to find chapter list on main page first
                try:
                    page.wait_for_selector('.chapter-list, .chapters', timeout=5000)
                except:
                    pass

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                chapters = []

                # Check for chapter list container
                chapter_list = soup.select('.chapter-list-item a, li.chapter a')

                if not chapter_list:
                    # Maybe it's a "Read Now" button only?
                    # If so, we might need to click read and extract TOC from reader.
                    read_btn = soup.select_one('a.read-btn')
                    if read_btn:
                         read_url = read_btn['href']
                         if not read_url.startswith('http'):
                             read_url = f"https://www.inkitt.com{read_url}"

                         # Go to reader
                         page.goto(read_url, wait_until="domcontentloaded")
                         # Click TOC button if needed? usually TOC is hidden in side menu.
                         # Try to extract from data or hidden menu.

                         # Let's assume for now we can find links in the source or via script.
                         # Inkitt reader usually has a TOC dropdown.

                         hrefs = page.evaluate("""() => {
                             return Array.from(document.querySelectorAll('a')).map(a => ({href: a.href, text: a.innerText}))
                         }""")

                         # Filter for chapter links
                         # usually /stories/ID/chapters/NUM
                         seen_urls = set()
                         for link in hrefs:
                             href = link['href']
                             text = link['text']
                             if '/chapters/' in href:
                                 if href not in seen_urls:
                                     # Extract number to sort?
                                     # Assuming scraped order is roughly correct or we can deduce

                                     chapters.append({
                                         'title': text.strip() or "Chapter",
                                         'url': href,
                                         'published_date': None # No easy date in reader TOC
                                     })
                                     seen_urls.add(href)

                else:
                    # Try to extract dates from chapter list if available
                    # Inkitt often hides dates but sometimes puts them in span.date or similar

                    for link in chapter_list:
                         href = link['href']
                         if not href.startswith('http'):
                             href = f"https://www.inkitt.com{href}"

                         title = link.get_text(strip=True)

                         published_date = None
                         # Look for sibling/parent date
                         # Usually <li><a ...>Title</a> <span class="date">...</span></li>
                         parent = link.find_parent('li')
                         if parent:
                             date_span = parent.find(class_='date')
                             if date_span:
                                 try:
                                     # Inkitt date format varies, but often YYYY-MM-DD
                                     raw_date = date_span.get_text(strip=True)
                                     published_date = datetime.strptime(raw_date, "%Y-%m-%d")
                                 except:
                                     pass

                         chapters.append({
                             'title': title,
                             'url': href,
                             'published_date': published_date
                         })

                # Attempt to get 'last_updated' from page metadata to at least have ONE date
                try:
                    # Look for schema.org data
                    schema_script = soup.find('script', type='application/ld+json')

                    # Or meta updated_time
                    meta_updated = soup.find('meta', property='og:updated_time')
                    if meta_updated and chapters:
                        # Apply to last chapter as a fallback if no specific dates
                        try:
                            ts = meta_updated.get('content')
                            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                            chapters[-1]['published_date'] = dt
                        except:
                            pass
                except:
                    pass

                return chapters

            finally:
                browser.close()

    def get_chapter_content(self, chapter_url: str) -> str:
        with self._get_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as e:
                if "Executable doesn't exist" in str(e):
                    self._ensure_browser_installed()
                    browser = p.chromium.launch(headless=True)
                else:
                    raise e

            page = browser.new_page()
            try:
                page.goto(chapter_url, wait_until="domcontentloaded")

                # Check if locked? Inkitt is mostly free but has subscription model for beta reading?

                try:
                    page.wait_for_selector('.story-text, #story-text', timeout=10000)
                except:
                    pass

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                content_div = soup.select_one('.story-text')
                if not content_div:
                    content_div = soup.select_one('#story-text')

                if content_div:
                    self.remove_hidden_elements(soup, content_div)
                    return content_div.decode_contents()

                return "<p>No content found.</p>"

            finally:
                browser.close()

    def search(self, query: str) -> List[Dict]:
        search_url = f"https://www.inkitt.com/stories?q={query}"

        results = []
        with self._get_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as e:
                if "Executable doesn't exist" in str(e):
                    self._ensure_browser_installed()
                    browser = p.chromium.launch(headless=True)
                else:
                    raise e

            page = browser.new_page()
            try:
                page.goto(search_url, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Results usually in .story-card
                items = soup.select('.story-card')

                for item in items:
                    title_tag = item.select_one('.story-title')
                    if not title_tag:
                         continue

                    title = title_tag.get_text(strip=True)

                    link = item.find('a', href=True)
                    # Usually wrapping card or title
                    if not link:
                         # try finding link inside
                         link = item.find('a')

                    if not link:
                        continue

                    url = link['href']
                    if not url.startswith('http'):
                        url = f"https://www.inkitt.com{url}"

                    author = "Unknown"
                    author_tag = item.select_one('.author-name')
                    if author_tag:
                        author = author_tag.get_text(strip=True)

                    cover_url = None
                    img = item.find('img')
                    if img:
                        cover_url = img.get('src')

                    results.append({
                        'title': title,
                        'url': url,
                        'author': author,
                        'cover_url': cover_url,
                        'provider': 'Inkitt'
                    })

            finally:
                browser.close()

        return results
