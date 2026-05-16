from .base import NetLurker
import logging, operator
from typing import Dict, List, Tuple
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

OPERATORS = {
    "==", operator.eq,
    "!=", operator.ne,
    "<", operator.lt,
    ">", operator.gt,
    "<=", operator.le,
    ">=", operator.ge
}

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
            ty = job.get("type")
            for action in job.get("pre_actions", []):
                self._actuate(action)
            if ty == "table":
                result = self._table_lurker(job)
            elif ty == "item":
                self._item_lurker(job)
            for action in job.get("pre_actions", []):
                self._actuate(action, result=result)
            if ty == "table":
                return [dict(zip(result[1], row)) for row in result[2]]
    
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

                    // Only process if its not null
                    if (rowData.some(cell => cell !== "")) {{
                        // Creem una "clau" única unint el contingut de les cel·les
                        const rowKey = JSON.stringify(rowData);
                        // Do not process duplicated rows
                        if (!seen.has(rowKey)) {{
                            seen.add(rowKey);
                            uniqueResults.push(rowData);
                        }}
                    }}
                }});

                return uniqueResults;
            }}
        """)
        return ["table", headers, results]
    
    def _actuate(self, action: Dict[str, Any], result: List[Any]=None):
        act = action.get("action")
        val = action.get("value")
        chk = action.get("check")
        sym = action.get("sym", "")
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
            elif act == "filter":
                logger.info(f"Filtering with {val} {sym} {chk}.")
                self._filter(val, chk, sym, result)
        except Exception as e:
            logger.error(f"Could not actuate {act}, value {val}: {e}")
    
    def _filter(self, name, value, sym, result):
        func = OPERATORS.get(sym)
        if not func:
            logger.error(f"No existing operator {sym}")
            return
        # Validate outer listchar
        if not isinstance(result, list):
            logger.error("Cannot filter. Wrong parametertype for result list.")
            return

        if result[0] == "table":
            # Validate table format
            if len(result) != 3:
                logger.error("Cannot filter. Wrong parameter number in result list.")
                return

            # Validate header list
            if not isinstance(result[1], list) or not all(
                isinstance(c, str) for c in result[1]
            ):
                logger.error("Column headers must be a list of strings.")
                return

            # Validate result table
            if not isinstance(result[2], list) or not all(
                isinstance(fila, list) for fila in result[2]
            ):
                logger.error("Rows must be a list of lists.")
                return
            if name.lower() not in result[1]:
                logger.warning(f"No column named {name}.")
                return
            index = result[1].index(name.lower())
            result[2][:] = [row for row in result[2] if func(row[index], value)]