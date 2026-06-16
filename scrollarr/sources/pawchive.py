from .kemono import KemonoSource

class PawchiveSource(KemonoSource):
    BASE_URLS = ["https://pawchive.st"]
    key = "pawchive"
    name = "Pawchive"
    is_enabled_by_default = False

    URL_REGEX = r'pawchive\.st/([^/]+)/user/([^/]+)'
    DEFAULT_DOMAIN = "https://pawchive.st"
    IMG_DOMAIN = "https://pawchive.st"

    def get_base_domain(self, url: str) -> str:
        return self.DEFAULT_DOMAIN

    def get_img_domain(self, url: str) -> str:
        # Check if URL specifies another image subdomain, otherwise use DEFAULT_DOMAIN
        if "img.pawchive.st" in url:
            return "https://img.pawchive.st"
        return self.DEFAULT_DOMAIN
