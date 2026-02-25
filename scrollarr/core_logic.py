import re
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# The "Contract" for any new website (Royal Road, AO3, etc.)
class BaseSource(ABC):
    key: str = ""
    name: str = ""
    is_enabled_by_default: bool = True

    @abstractmethod
    def identify(self, url: str) -> bool:
        """Returns True if this provider handles the given URL."""
        pass

    @abstractmethod
    def get_metadata(self, url: str) -> Dict:
        """Returns title, author, description, and cover_url."""
        pass

    @abstractmethod
    def get_chapter_list(self, url: str, **kwargs) -> List[Dict]:
        """Returns a list of chapter objects: {id, title, url}."""
        pass

    @abstractmethod
    def get_chapter_content(self, chapter_url: str) -> str:
        """Returns the raw HTML/Text content of a single chapter."""
        pass

    @abstractmethod
    def search(self, query: str) -> List[Dict]:
        """
        Searches for stories matching the query.
        Returns a list of dictionaries containing metadata (title, url, author, etc.).
        """
        pass

    def remove_hidden_elements(self, soup: BeautifulSoup, root_element):
        """
        Removes elements that are hidden via CSS classes (display: none) or inline styles.
        Args:
            soup: The BeautifulSoup object of the entire page (to access <style> blocks).
            root_element: The element (or soup) from which to remove hidden content.
        """
        if not root_element:
            return

        hidden_classes = set()
        # Scan all style tags in the soup (document)
        for style in soup.find_all('style'):
            if style.string:
                # Look for class definitions with display: none
                matches = re.finditer(r'\.([a-zA-Z0-9_\-]+)\s*\{[^}]*display\s*:\s*none', style.string, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    hidden_classes.add(match.group(1))

        # Check for inline styles display:none
        # Note: root_element might be a tag or the soup itself
        if hasattr(root_element, 'find_all'):
            for tag in root_element.find_all(style=re.compile(r'display\s*:\s*none', re.IGNORECASE)):
                tag.decompose()

            # Remove elements with hidden classes
            if hidden_classes:
                for hidden_class in hidden_classes:
                    for tag in root_element.find_all(class_=hidden_class):
                        tag.decompose()

    def set_config(self, config: Dict):
        """
        Sets provider-specific configuration (e.g. cookies, API keys).
        """
        pass

# The "Dispatcher" that picks the right source
class SourceManager:
    def __init__(self):
        self.providers: List[BaseSource] = []

    def register_provider(self, provider: BaseSource):
        self.providers.append(provider)

    def clear_providers(self):
        self.providers = []

    def get_provider_for_url(self, url: str) -> Optional[BaseSource]:
        for provider in self.providers:
            if provider.identify(url):
                return provider
        return None

    def get_provider_by_key(self, key: str) -> Optional[BaseSource]:
        for provider in self.providers:
            if provider.key == key:
                return provider
        return None
