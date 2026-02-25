import re
import time
import subprocess
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from ..core_logic import BaseSource

class FanFictionSource(BaseSource):
    key = "fanfiction"
    name = "FanFiction.net / FictionPress"
    is_enabled_by_default = True

    def identify(self, url: str) -> bool:
        return 'fanfiction.net' in url or 'fictionpress.com' in url

    def _get_playwright(self):
        try:
            from playwright.sync_api import sync_playwright
            return sync_playwright()
        except ImportError:
            raise ImportError("Playwright is not installed. Please install it to use FanFiction source.")

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
                # Wait for Cloudflare/Content
                try:
                    page.wait_for_selector('#profile_top', timeout=15000)
                except:
                    pass

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Profile Top contains metadata
                profile_top = soup.select_one('#profile_top')
                if not profile_top:
                    # Maybe mobile view or error
                    # Try finding title elsewhere or raise error
                    # For now return basics
                    return {'title': 'Unknown', 'author': 'Unknown'}

                # Title
                title_tag = profile_top.find('b', class_='xcontrast_txt')
                title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

                # Author
                author_tag = profile_top.find('a', href=re.compile(r'/u/\d+/'))
                author = author_tag.get_text(strip=True) if author_tag else "Unknown Author"

                # Description
                description_div = profile_top.find('div', class_='xcontrast_txt')
                description = "No description available."
                if description_div:
                     description = description_div.get_text(strip=True)

                # Cover
                cover_url = None
                img = profile_top.find('img', class_='cimage')
                if img:
                    cover_url = img.get('src')
                    if cover_url and not cover_url.startswith('http'):
                        cover_url = f"https:{cover_url}"

                # Tags / Metadata Text
                # The text usually looks like: "Rated: T - English - Romance/Humor - Chapters: 10 - Words: 20k - ..."
                metadata_text = profile_top.get_text(" | ", strip=True)

                # Extract status
                publication_status = "Ongoing"
                if "Status: Complete" in metadata_text:
                    publication_status = "Completed"

                # Extract rating
                rating = None
                rating_match = re.search(r'Rated:\s*([^\s|]+)', metadata_text)
                if rating_match:
                    rating = rating_match.group(1)

                # Extract language
                language = "English"
                # Often the second item, but hard to guarantee.
                # Let's just default to English for now or parse better later if needed.

                return {
                    'title': title,
                    'author': author,
                    'description': description,
                    'cover_url': cover_url,
                    'tags': None, # Tags are mixed in text, hard to separate cleanly without strict parsing
                    'rating': rating,
                    'language': language,
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
                try:
                    page.wait_for_selector('#chap_select, #storytext', timeout=15000)
                except:
                    pass

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                chapters = []

                # Check for chapter dropdown
                select = soup.select_one('#chap_select')
                if select:
                    options = select.find_all('option')
                    for opt in options:
                        chap_id = opt.get('value')
                        chap_title = opt.get_text(strip=True)
                        # Construct URL. URL structure: /s/{story_id}/{chapter_id}/{slug}
                        # We need base story url.
                        # Input url might be /s/12345/1/Title
                        # We can extract story ID.
                        match = re.search(r'/s/(\d+)', url)
                        if match:
                            story_id = match.group(1)
                            # Domain
                            domain = "https://www.fanfiction.net" if "fanfiction.net" in url else "https://www.fictionpress.com"
                            chap_url = f"{domain}/s/{story_id}/{chap_id}"

                            # Clean title: "1. Chapter Title" -> "Chapter Title"
                            # If just number, use it.
                            clean_title = re.sub(r'^\d+\.\s*', '', chap_title)

                            chapters.append({
                                'title': clean_title,
                                'url': chap_url
                            })
                else:
                    # Single chapter
                    # If we are on a valid story page but no dropdown, it's 1 chapter.
                    if soup.select_one('#storytext'):
                        chapters.append({
                            'title': "Chapter 1",
                            'url': url
                        })

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
                try:
                    page.wait_for_selector('#storytext', timeout=15000)
                except:
                    pass

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                content_div = soup.select_one('#storytext')
                if content_div:
                    self.remove_hidden_elements(soup, content_div)
                    return content_div.decode_contents()

                return "<p>No content found.</p>"

            finally:
                browser.close()

    def search(self, query: str) -> List[Dict]:
        # Search URL: https://www.fanfiction.net/search/?keywords=query&ready=1&type=story
        # We need to handle both domains? usually search implies one.
        # Let's default to fanfiction.net for now, or maybe try both if we could (but we return list).
        # Let's check which domain is more "default". FanFiction.net is bigger.

        base_url = "https://www.fanfiction.net"
        search_url = f"{base_url}/search/?keywords={query}&ready=1&type=story"

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
                try:
                    page.wait_for_selector('.z-list', timeout=15000)
                except:
                    pass

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                items = soup.select('.z-list')
                for item in items:
                    try:
                        # Title
                        title_link = item.find('a', class_='stitle')
                        if not title_link:
                            continue

                        title = title_link.get_text(strip=True)
                        url = f"{base_url}{title_link['href']}"

                        # Author
                        author_link = item.find('a', href=re.compile(r'/u/'))
                        author = author_link.get_text(strip=True) if author_link else "Unknown"

                        # Cover
                        cover_url = None
                        img = item.find('img', class_='cimage')
                        if img:
                            src = img.get('src')
                            if src:
                                cover_url = src if src.startswith('http') else f"https:{src}"

                        results.append({
                            'title': title,
                            'url': url,
                            'author': author,
                            'cover_url': cover_url,
                            'provider': 'FanFiction.net'
                        })
                    except Exception:
                        continue
            finally:
                browser.close()

        return results
