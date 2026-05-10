from abc import ABC, abstractmethod
from typing import Dict, List, Union
import xml.etree.ElementTree as ET
import requests
import urllib.robotparser
import logging

logger = logging.getLogger(__name__)

def _get_robots(url: str) -> Union[urllib.robotparser.RobotFileParser, None]:
    """
    Retrieves the robots.txt file.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url_base = url
    if not url_base: raise ValueError('No base URL.')
    if not url_base.endswith('/'):
        url_base += '/'
    url_base += "robots.txt"
    # Get robots.txt
    response = requests.get(url_base, timeout=10, headers=headers)
    if response.status_code == 200:
        try:
            robotparser = urllib.robotparser.RobotFileParser()
            robotparser.parse(response.text.splitlines())
            logger.info("robots.txt found.")
            return robotparser
        except Exception as e:
            logger.error(f"Cannot read robots.txt from {url_base}: {e}.")
            raise e
    else:
        return None

def _get_sitemaps(site: str) -> List[str]:
    """
    From an xml sitemap, gets the paths contained in them.
    """
    sites = []
    try:
        response = requests.get(site, timeout=5)
        root = ET.fromstring(response.content)

        for loc in root.findall('.//{*}loc'):
            url = loc.text.strip() if loc.text else ""
            if url:
                if url.endswith('.xml') and (url != site or url not in sites):
                    sites.extend(_get_sitemaps(url))
                else:
                    sites.append(url)
    except Exception as e:
        # TODO: logging
        pass
    return sites


class NetLurker(ABC):

    def __init__(self, config: Dict[str, str]):
        self.config = config
        # Key validation
        if "base_url" not in self.config:
            logger.error("JSON Schema error.")
            raise KeyError(f"Missing parameter in config file: {key}.")
        
        self.type = self.config.get("type")
        self.base_url = self.config.get("base_url")
        if not self.base_url: return
        self.rp = _get_robots(self.base_url)
        if self.rp:
            sitemap = self.rp.site_maps()
            self.sitemaps = []
            if sitemap:
                for site in sitemap:
                    if site.endswith('.xml'):
                        self.sitemaps.extend(_get_sitemaps(site))
                    else:
                        self.sitemaps.append(site)
    

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def lurk(self):
        pass

    @abstractmethod
    def close(self):
        pass

class TestLurker(NetLurker):
    def __init__(self, config_pas):
        if config_pas is None:
            config_pas = {
                "type": "test",
                "base_url": "https://www.flightradar24.com/"
            }
        super().__init__(config_pas)

    def connect(self): pass
    def lurk(self): pass
    def close(self): pass

def test_robots_info(crawler: TestCreep):
    rp = crawler.rp
    if not rp:
        print(f"[-] There is no robots.txt file for the URL {crawler.base_url}")
        return
    print(f"\n{'=' * 80}")
    print(f"SUMMARY OF ROBOTS FOR {crawler.base_url}")
    print(f"{'=' * 40}")

    print(f"{'\n' * 2}{'=' * 80}")
    print("SITEMAPS FOUND:")
    sitemaps = rp.site_maps()
    if not sitemaps:
        print("---NO SITEMAPS FOUND---")
    else:
        for site in sitemaps:
            if site.endswith('.xml'):
                print(f"Processing XML Sitemap: {site}")
                sites = _get_sitemaps(site)
                for urls in sites:
                    print(f"[+]    - {urls}")
            else:
                print(f"[+]    - {site}")
        print(f"{'\n' * 2}")
    
    delay = rp.crawl_delay("*")
    if delay:
        print(f"CRAWL-DELAY DETECTED: {delay} SECONDS")
    
    rules = str(rp)
    if not rules:
        print("---NO RULES DETECTED---")
    else:
        for line in rules.splitlines():
            print(f"[+]    {line}")

    

if __name__ == "__main__":
    test_robots_info(TestLurker(None))
