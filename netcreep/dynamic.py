from .base import NetLurker
import logging
from typing import Dict, List, Tuple
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

class DynamicLurker(NetLurker):
    def __init__(self, config: Dict[str, str]):
        super().__init__(config)
        self.jobs = config.get("jobs", [])

    def connect(self):
        logger.info(f"Connecting to {self.base_url} via Playwright")
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        self.page.goto(self.base_url)
        logger.info(f"Connected to page {self.base_url}")
    
    def lurk(self):
        for job in self.jobs:
            for action in job.get("pre_actions", []):
                self._actuate(action)
            if job.get("type") == "table":
                headers, results = self._table_lurker(job)
            elif self.config.get("type") == "item":
                self._item_lurker(job)
    
    def close(self):
        logger.info("Stopping playwright browser.")
        if self.browser:
            self.browser.close()
        if self.pw:
            self.pw.stop()
    

    def _item_lurker(self, job: Dict[str, str]):
        raise NotImplementedError("Item lurker is not implemented")
    
    def _table_lurker(self, job: Dict[str, str]) -> Tuple[List[str], List[str]]:
        table_id = job.get("name")
        logging.info(f"Lurking in table {table_id}.")
        self.page.wait_for_selector(f"#{table_id}")

        # Try to extract header
        headers, results = [], []
        header_elements = self.page.query_selector_all(f"#{table_id} thead td, #{table_id} thead th")
        if header_elements:
            headers = [h.inner_text().strip() or h.get_attribute("id") or ""
                       for h in header_elements]
        
        # Extract rows
        results = self.page.evaluate(f"""
            () => {{
                const rows = Array.from(document.querySelectorAll('#{table_id} tbody tr'));
                const seen = new Set();
                const uniqueResults = [];

                rows.forEach(tr => {{
                    const cells = Array.from(tr.querySelectorAll('td'));
                    const rowData = cells.map(td => {{
                        const img = td.querySelector('img');
                        if (img) {{
                            return img.getAttribute('title') || img.getAttribute('alt') || "";
                        }}
                        return td.innerText.trim();
                    }});

                    // Només processem si la fila té algun contingut
                    if (rowData.some(cell => cell !== "")) {{
                        // Creem una "clau" única unint el contingut de les cel·les
                        const rowKey = JSON.stringify(rowData);
                        
                        if (!seen.has(rowKey)) {{
                            seen.add(rowKey);
                            uniqueResults.push(rowData);
                        }}
                    }}
                }});

                return uniqueResults;
            }}
        """)
        # Bad. Really bad. Do not use. It will tank the performance
        """rows = self.page.query_selector_all(f"#{table_id} tbody tr")
        for row in rows:
            cells = row.query_selector_all("td")
            row = []
            if cells:
                for cell in cells:
                    img = cell.query_selector("img")
                    if img:
                        data = img.get_attribute("title") or img.get_attribute("alt")
                    else:
                        data = cell.inner_text()
                    row.append(data.strip() if data else "")
                if any(row):
                    results.append(row)"""
        return headers, results
    
    def _actuate(self, action: Dict[str, Any]):
        act = action.get("action")
        val = action.get("value")
        chk = action.get("check")
        try:
            if act == "click":
                logger.info(f"Click on {val}.")
                self.page.wait_for_selector(val)
                if not chk:
                    chk = 1
                else:
                    chk = int(chk)
                for i in range(chk):
                    self.page.click(val)
            if act == "click_if_not_checked":
                logger.info(f"Click if not checked on {val}.")
                is_checked = self.page.locator(f"{val}.{chk}").count() > 0
                if not is_checked:
                    logger.info(f"Activating toggle: {val}.")
                    self.page.click(val)
                    is_checked = self.page.locator(f"{val}.{chk}").count() > 0
            elif act == "wait":
                logger.info(f"Waiting {val} ms.")
                self.page.wait_for_timeout(val)
            elif act == "mouse_wheel":
                logger.info(f"Scrolling on {val}.")
                box = self.page.locator(val).bounding_box()
                if box:
                    # Move mouse
                    self.page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                    # Scrolling
                    chk = float(chk)
                    self.page.mouse.wheel(0, chk)

        except Exception as e:
            logger.error(f"Could not actuate {act}, value {val}: {e}")