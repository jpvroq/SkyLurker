from .base import NetLurker
from typing import Dict, List, Tuple
from bs4 import BeautifulSoup
import logging, requests

logger = logging.getLogger(__name__)

class StaticLurker(NetLurker):
    def __init__(self, config: Dict[str, str]):
        super().__init__(config)
        self.jobs = config.get("jobs", [])
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def connect(self):
        logger.info(f"Connecting to {self.base_url} via Playwright")
        try:
            response = self.session.get(self.base_url)
            response.raise_for_status()
            self.last_html = response.text
        except requests.RequestException as e:
            logger.error(f"Failed to connect: {e}")
    
    def lurk(self):
        for job in self.jobs:
            if job.get("type") == "table":
                headers, results = self.table_lurker(job)
                print(headers)
                print(results)
            elif self.config.get("type") == "item":
                self.item_lurker(job)
    def close(self):
        logger.info("Crawler closed.")
    

    def item_lurker(self, job: Dict[str, str]):
        raise NotImplementedError("Item lurker is not implemented")
    
    def table_lurker(self, job: Dict[str, str]) -> Tuple[List[str], List[str]]:
        table_id = job.get("name")
        logging.info(f"Lurking in table {table_id}.")

        soup = BeautifulSoup(self.last_html, 'html.parser')
        table = soup.find("table", {"id": table_id})
        headers, result = [], []
        if not table:
            logger.warning(f"Table with id {table_id} not found.")
            return headers, result

        # Try to extract header
        thead = table.find("thead")
        if thead:
            header_elems = thead.find_all(["th", "td"])
            headers = [h.get_text(strip=True) for h in header_elems]
        
        # Extract rows
        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody else table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            row_data = []
            if cells:
                for cell in cells:
                    img = cell.find("img")
                    if img and img.get("title"):
                        data = img.get("title")
                    else:
                        data = cell.get_text(strip=True)
                    row_data.append(data if data else "")
                if any(row_data):
                    results.append(row_data)
        return headers, results