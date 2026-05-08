from abc import ABC, abstractmethod
from typing import Dict, Union
from pathlib import Path
import json, os
import urllib.robotparser

class NetCreep(ABC):

    def __init__(self, config: Dict[str, str]):
        self.config = config
        # Key validation
        for key in ["base_url", "type"]:
            if key not in self.config:
                raise KeyError(f"Missing parameter in config file: {key}")
        
        self.type = self.config.get("type")
        self.base_url = self.config.get("base_url")
        self.rp = self._get_robots()
    
    def _get_robots(self) -> urllib.robotparser.RobotFileParser:
        """
        Retrieves the robots.txt file.
        """
        url_base = self.base_url
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
    def __init__(self):
        config = {
            "type": "test",
            "base_url": "https://skyosint.io"
        }
        super().__init__(config)

    def connect(self): pass
    def creep(self): pass
    def close(self): pass

def test_robots_info(crawler: TestCreep):
    rp = crawler.rp
    if not rp:
        print(f"[-] There is no robots.txt file for the URL {crawler.url_base}")
        return
    print(f"\n{'=' * 40}")
    print(f"SUMMARY OF ROBOTS FOR {crawler.base_url}")
    print(f"{'=' * 40}")

    print(f"{'\n' * 2}{'=' * 40}")
    print("SITEMAPS FOUND:")
    sitemaps = rp.site_maps()
    if not sitemaps:
        print("---NO SITEMAPS FOUND---")
    else:
        for site in sitemaps:
            print(f"[+]    - {site}")
        print(f"{'\n' * 4}")
    
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
    test_robots_info(TestCreep())
