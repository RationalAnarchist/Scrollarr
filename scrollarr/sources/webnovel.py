import re
import time
import subprocess
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from ..core_logic import BaseSource

class WebNovelSource(BaseSource):
    key = "webnovel"
    name = "WebNovel"
    is_enabled_by_default = True

    def identify(self, url: str) -> bool:
        return 'webnovel.com' in url

    def _get_playwright(self):
        try:
            from playwright.sync_api import sync_playwright
            return sync_playwright()
        except ImportError:
            raise ImportError("Playwright is not installed. Please install it to use WebNovel source.")

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
                # Often in a span or link near title
                # Structure varies, looking for common patterns
                # Try finding 'Author:' or similar context if specific selector fails
                # Often <h2 class="author-name"> or similar?
                # Let's try broad search or specific selector if known.
                # Common pattern: .g_txt_over a[href*="/profile/"]
                author_link = soup.select_one('a[href*="/profile/"]')
                if author_link:
                    author = author_link.get_text(strip=True)

                # Description
                description = "No description available."
                desc_div = soup.select_one('.j_synopsis')
                if desc_div:
                    description = desc_div.get_text(strip=True)
                else:
                    # Fallback to OG tag
                    og_desc = soup.find('meta', property='og:description')
                    if og_desc:
                        description = og_desc.get('content', '')

                # Cover
                cover_url = None
                og_image = soup.find('meta', property='og:image')
                if og_image:
                    cover_url = og_image.get('content')
                    if cover_url and not cover_url.startswith('http'):
                        cover_url = f"https:{cover_url}"

                # Tags
                tags = []
                # Often in .m-tags a
                for tag in soup.select('.m-tags a'):
                    tags.append(tag.get_text(strip=True))

                # Status
                publication_status = "Ongoing"
                # Check for "Completed" text in headers or metadata
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
                # WebNovel chapter list is often in a "Catalog" tab.
                # Sometimes URL is /book/xyz
                # We might need to click "Catalog" tab or navigate to /catalog

                # If url ends with /catalog, use it. Else append /catalog? No, usually click.
                page.goto(url, wait_until="domcontentloaded")

                # Try to click "Catalog" or "Chapters" tab if present
                try:
                    # Look for tab with text "Catalog"
                    page.click("text=Catalog", timeout=5000)
                    page.wait_for_timeout(2000) # Wait for load
                except:
                    # Maybe it's already catalog or different layout
                    pass

                # If the list is long, it might lazy load.
                # Ideally scroll to bottom?
                # For now, let's grab what's visible.

                hrefs = page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a')).map(a => ({
                        href: a.href,
                        text: a.innerText,
                        is_locked: a.querySelector('.lock-icon') !== null || a.querySelector('svg[class*="lock"]') !== null
                    }))
                }""")

                chapters = []
                seen_urls = set()

                # Filter for chapter links
                # Usually contain /book/BOOKID/CHAPTERID
                # Regex for /book/(\d+)/(\d+)

                for link in hrefs:
                    href = link['href']
                    text = link['text']
                    is_locked = link['is_locked']

                    if not href:
                        continue

                    if '/book/' in href and re.search(r'/\d+/\d+', href):
                        # Ensure it's not a duplicate
                        if href not in seen_urls:
                            title = text.strip().replace('\n', ' ')
                            if is_locked:
                                title += " [LOCKED]"
                                # We might skip locked ones if we can't download them
                                # But listing them helps user know progress

                            chapters.append({
                                'title': title,
                                'url': href
                            })
                            seen_urls.add(href)

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

                # Check if locked
                # Look for lock message or obscured content
                if "unlock this chapter" in page.content().lower():
                    return "<p>This chapter is locked and cannot be downloaded.</p>"

                try:
                    page.wait_for_selector('.chapter_content', timeout=10000)
                except:
                    pass

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Content usually in .chapter_content or .cha-content
                content_div = soup.select_one('.chapter_content')
                if not content_div:
                    content_div = soup.select_one('.cha-content')

                if content_div:
                    self.remove_hidden_elements(soup, content_div)

                    # Also remove pirated warning or watermarks if any known classes
                    # WebNovel sometimes inserts random characters?
                    # Assuming basic scraping for now.

                    return content_div.decode_contents()

                return "<p>No content found.</p>"

            finally:
                browser.close()

    def search(self, query: str) -> List[Dict]:
        search_url = f"https://www.webnovel.com/search?keywords={query}"
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
                page.wait_for_timeout(3000) # Wait for results

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Search results list
                # Usually .search-result-container li or div
                # Looking for links to books

                items = soup.select('li[data-bookid]') # If available
                if not items:
                     items = soup.select('.search-result-item') # Generic guess

                if not items:
                     # Try finding anchors with /book/ in href and image
                     anchors = soup.select('a[href^="/book/"]')
                     # Filter for main book links (usually have title and img)
                     for a in anchors:
                        if a.find('img'):
                            # Likely a result card
                            # We need to process this carefully to avoid duplicates
                            pass

                # Let's assume a structure similar to what we can see or generic fallback
                # Trying to find containers

                for item in soup.select('li'):
                     # Check if it has a book link
                     link = item.find('a', href=re.compile(r'/book/'))
                     if link:
                         title_tag = item.find('h3')
                         if not title_tag:
                             continue

                         title = title_tag.get_text(strip=True)
                         url = link['href']
                         if not url.startswith('http'):
                             url = f"https://www.webnovel.com{url}"

                         cover_url = None
                         img = item.find('img')
                         if img:
                             cover_url = img.get('src')
                             if cover_url and not cover_url.startswith('http'):
                                 cover_url = f"https:{cover_url}"

                         author = "Unknown"
                         author_tag = item.find(class_='author')
                         if author_tag:
                             author = author_tag.get_text(strip=True)

                         results.append({
                             'title': title,
                             'url': url,
                             'author': author,
                             'cover_url': cover_url,
                             'provider': 'WebNovel'
                         })

            finally:
                browser.close()

        return results
