import re
import time
import subprocess
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from ..core_logic import BaseSource

class TapasSource(BaseSource):
    key = "tapas"
    name = "Tapas"
    is_enabled_by_default = True

    def identify(self, url: str) -> bool:
        return 'tapas.io' in url

    def _get_playwright(self):
        try:
            from playwright.sync_api import sync_playwright
            return sync_playwright()
        except ImportError:
            raise ImportError("Playwright is not installed. Please install it to use Tapas source.")

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
                    page.wait_for_selector('.series-header-title', timeout=15000)
                except:
                    pass

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Title
                title = "Unknown Title"
                title_tag = soup.select_one('.series-header-title')
                if title_tag:
                    title = title_tag.get_text(strip=True)

                # Author
                author = "Unknown Author"
                author_tag = soup.select_one('.author-name') # or .creator-name
                if author_tag:
                    author = author_tag.get_text(strip=True)
                else:
                    # Try finding creator link
                    creator_link = soup.select_one('a.creator-link')
                    if creator_link:
                        author = creator_link.get_text(strip=True)

                # Description
                description = "No description available."
                desc_div = soup.select_one('.series-desc') # .series-info .description
                if not desc_div:
                    desc_div = soup.select_one('.description__body')

                if desc_div:
                    description = desc_div.get_text(strip=True)
                else:
                    og_desc = soup.find('meta', property='og:description')
                    if og_desc:
                        description = og_desc.get('content', '')

                # Cover
                cover_url = None
                cover_img = soup.select_one('.series-thumb img')
                if cover_img:
                    cover_url = cover_img.get('src')
                else:
                    og_image = soup.find('meta', property='og:image')
                    if og_image:
                        cover_url = og_image.get('content')

                # Tags / Genre
                tags = []
                genre_tag = soup.select_one('.genre-name')
                if genre_tag:
                    tags.append(genre_tag.get_text(strip=True))

                for tag in soup.select('.tag-list a'):
                    tags.append(tag.get_text(strip=True))

                # Status
                publication_status = "Ongoing"
                # Check for "Completed" badge or text
                # Tapas often doesn't explicitly state completed in metadata easily accessible
                # Sometimes in info modal

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

                # Tapas usually has a "Episodes" tab or list
                # Often need to scroll or click "Show more"
                # Or handle pagination

                # Check for "Episodes" tab and click
                try:
                    page.click("text=Episodes", timeout=5000)
                    page.wait_for_timeout(2000)
                except:
                    pass

                # Auto-scroll to load all episodes if lazy loaded
                # Tapas uses infinite scroll or pagination often
                # Let's try to scroll to bottom a few times
                for _ in range(5):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1000)

                hrefs = page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a.episode-list-item__link, li.episode-list-item a')).map(a => {
                        let dateText = null;
                        let p = a.closest('.episode-list-item') || a.parentElement;
                        if (p) {
                             let d = p.querySelector('.date, .created-at, .episode-date');
                             if (d) dateText = d.innerText;
                        }
                        return {
                            href: a.href,
                            text: a.innerText,
                            is_locked: a.querySelector('.icon-lock') !== null || a.innerText.includes('Free in'),
                            date: dateText
                        };
                    })
                }""")

                chapters = []
                seen_urls = set()

                # Expected URL structure: /series/SERIESID/episodes/EPISODEID

                for link in hrefs:
                    href = link['href']
                    text = link['text']
                    is_locked = link['is_locked']
                    date_text = link['date']

                    if not href:
                        continue

                    if '/episode/' in href or '/episodes/' in href:
                        if href not in seen_urls:
                            title = text.strip().replace('\n', ' ')
                            # Remove "Episode X" prefix if desired, or keep

                            if is_locked:
                                title += " [LOCKED]"

                            published_date = None
                            if date_text:
                                try:
                                    # Tapas format: "Jan 01, 2024"
                                    raw = date_text.strip()
                                    published_date = datetime.strptime(raw, "%b %d, %Y")
                                except:
                                    pass

                            chapters.append({
                                'title': title,
                                'url': href,
                                'published_date': published_date
                            })
                            seen_urls.add(href)

                # Reverse if needed? Tapas usually lists newest first or oldest first depending on user setting.
                # Often newest first. We might want to reverse to get oldest first (Chapter 1).
                # But without knowing, let's keep as is. User can sort.
                # Actually standard is usually oldest to newest for reading.
                # If IDs are increasing, we can sort by ID?
                # Let's leave as scraped order.

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

                # Check locked
                if "Unlock this episode" in page.content() or "Subscribe to unlock" in page.content():
                     return "<p>This chapter is locked.</p>"

                try:
                    page.wait_for_selector('.viewer__body, .episode-viewer', timeout=10000)
                except:
                    pass

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Content for novels is usually in .viewer__body or .ep-content
                content_div = soup.select_one('.viewer__body') # New UI?
                if not content_div:
                    content_div = soup.select_one('.episode-viewer') # Comic viewer often has images
                    if content_div:
                         # Handle comics: find all images
                         imgs = content_div.find_all('img', class_='content-image')
                         if imgs:
                             html_content = ""
                             for img in imgs:
                                 src = img.get('data-src') or img.get('src')
                                 if src:
                                     html_content += f'<img src="{src}" /><br/>'
                             return html_content

                # For novels (text)
                # Text usually in <article class="viewer__body"> -> <p>
                if content_div:
                    self.remove_hidden_elements(soup, content_div)
                    return content_div.decode_contents()

                return "<p>No content found.</p>"

            finally:
                browser.close()

    def search(self, query: str) -> List[Dict]:
        search_url = f"https://tapas.io/search?q={query}"
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

                # Search results
                # .search-item-list .search-item
                items = soup.select('.search-item-list .search-item')
                if not items:
                     # New UI? .search-result-row?
                     items = soup.select('.content-list-row .content-item')

                for item in items:
                    title_tag = item.select_one('.title') # or .content-title
                    if not title_tag:
                         continue

                    title = title_tag.get_text(strip=True)

                    link = item.find('a', class_='thumb-link') # or wraps title
                    if not link:
                        link = item.find('a', href=True)

                    if not link:
                        continue

                    url = link['href']
                    if not url.startswith('http'):
                        url = f"https://tapas.io{url}"

                    author = "Unknown"
                    author_tag = item.select_one('.author') # or .creator
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
                        'provider': 'Tapas'
                    })

            finally:
                browser.close()

        return results
