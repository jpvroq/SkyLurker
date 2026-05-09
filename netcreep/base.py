from abc import ABC, abstractmethod
from typing import Dict, List
import xml.etree.ElementTree as ET
import requests
import urllib.robotparser


def _get_robots(url: str) -> urllib.robotparser.RobotFileParser:
    """
    Retrieves the robots.txt file.
    """
    url_base = url
    if not url_base: raise ValueError('No base URL.')
    if not url_base.endswith('/'):
        url_base += '/'
    url_base += "robots.txt"
    # Get robots.txt
    robotparser = urllib.robotparser.RobotFileParser()
    try:
        robotparser.set_url(url_base)
        robotparser.read()
        return robotparser
    except Exception as e:
        # TODO: logger
        # TODO: throw Exception
        raise ValueError('Something happened.')

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
                if url.endswith('.xml') and url != site:
                    sites.extend(_get_sitemaps(url))
                else:
                    sites.append(url)
    except Exception as e:
        # TODO: logging
        pass
    return sites


class NetCreep(ABC):

    def __init__(self, config: Dict[str, str]):
        self.config = config
        # Key validation
        for key in ["base_url", "type"]:
            if key not in self.config:
                raise KeyError(f"Missing parameter in config file: {key}")
        
        self.type = self.config.get("type")
        self.base_url = self.config.get("base_url")
        if not self.base_url: return
        self.rp = _get_robots(self.base_url)
        sitemap = self.rp.site_maps()
        if sitemap:
            for site in sitemap:
                if site.endswith('.xml'):
                    self.sitemaps = _get_sitemaps(site)
                else:
                    pass
    

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def creep(self):
        pass

    @abstractmethod
    def close(self):
        pass

class TestCreep(NetCreep):
    def __init__(self, config_pas):
        if config_pas is None:
            config_pas = {
                "type": "test",
                "base_url": "https://skyosint.io"
            }
        super().__init__(config_pas)

    def connect(self): pass
    def creep(self): pass
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
    test_robots_info(TestCreep(None))
