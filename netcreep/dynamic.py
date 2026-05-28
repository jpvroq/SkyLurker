from .base import NetLurker, RestrictedError
import logging, operator
from typing import Dict, List, Tuple
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)

OPERATORS = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    ">": operator.gt,
    "<=": operator.le,
    ">=": operator.ge
}

def _typecast(val: Any) -> Any:
    """
    Tries to cast a string to an int or float.
    """
    if not isinstance(val, str):
        return val
    
    clean = val.strip()
    if not clean:
        return ""
    try:
        return int(clean)
    except ValueError:
        pass
    try:
        return float(clean)
    except ValueError:
        pass
    return val

class DynamicLurker(NetLurker):
    def __init__(self, config: Dict[str, str]):
        super().__init__(config)
        self.jobs = config.get("jobs", [])
        self.pw = None
        self.browser = None
        self.page = None

    async def connect(self):
        logging.info(f"Connecting to {self.base_url}")
        self.can_lurk = True
        try:
            self.stealth_context = Stealth().use_async(async_playwright())
            self.pw = await self.stealth_context.__aenter__()
            self.browser = await self.pw.chromium.launch(headless=True)

            self.page = await self.browser.new_page(
                user_agent=self.user_agent,
                viewport={"width": 1920, "height": 1080},
                locale="es-ES",
                timezone_id="Europe/Madrid"
            )
        
            self.verify_and_wait(self.base_url)

            await self.page.goto(self.base_url, wait_until="domcontentloaded")
            logger.info(f"Connected to page {self.base_url}")
        except RestrictedError as re:
            self.can_lurk = False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
    
    async def lurk(self):
        result = None
        if not self.can_lurk:
            return None
        for job in self.jobs:
            ty = job.get("type")
            for action in job.get("pre_actions", []):
                await self._actuate(action)
            if ty == "table":
                result = await self._table_lurker_hybrid(job)
            elif ty == "item":
                result = await self._item_lurker(job)
            
            for action in job.get("post_actions", []):
                await self._actuate(action, result=result)
            if ty == "table" and result:
                return [dict(zip(result[1], row)) for row in result[2]]
            if ty == "item" and result:
                return result[2]
    
    async def close(self):
        logger.info("Stopping playwright browser.")
        if hasattr(self, "browser") and self.browser:
            await self.browser.close()
        if hasattr(self, "stealth_context") and self.stealth_context:
            await self.stealth_context.__aexit__(None, None, None)
    

    async def _item_lurker(self, job: Dict[str, str]):
        """
        Gets a single text form the webpage.
        """
        item_name = job.get("name", None)
        logger.info(f"Searching for {item_name}.")

        data = {}
        fields = job.get("fields", [])

        if not fields:
            logger.warning(f"No fields defined for item job: {item_name}")
            return data
        
        for field in fields:
            field_name = field.get("field_name", None)
            if not field_name:
                logger.warning(f"Fields must have a name: {item_name}")
                continue
            selector = field.get("selector", None)
            if not selector:
                logger.warning(f"Fields must have a selector: {item_name}")
                continue
            try:
                await self.page.wait_for_selector(selector, timeout=5000)
                element = await self.page.locator(selector).first

                if await element.count() > 0:
                    text = (await element.inner_text()).strip()
                    type = field.get("type", None)
                    aux = None
                    if type:
                        try:
                            if type == 'int':
                                aux = int(text)
                            if type == 'float':
                                aux = float(text)
                            text = aux
                        except:
                            logger.warning(f"Cannot cast {text} to {type} for {field_name}.")
                    data[field_name] = text
            except Exception as e:
                logger.warning(f"Error extracting field '{field_name} using selector ¡{selector}: {e}")
            return {"item", item_name, data}
    
    async def _table_lurker_hybrid(self, job: Dict[str, str]) -> Tuple[List[str], List[str]]:
        table_id = job.get("name")
        logging.info(f"Lurking in table {table_id} (Hybrid Selector Asynchronous).")
        await self.page.wait_for_selector(f"#{table_id}", timeout=5000)

        selectors_js = f"#{table_id} thead td, #{table_id} thead th, #{table_id} [role='columnheader'], #{table_id} .grid-header-cell"
        row_selectors = f"#{table_id} tbody tr, #{table_id} [role='row'], #{table_id} .grid-row"
        
        data = await self.page.evaluate("""
            function(args) {
                var selJs = args[0];
                var rowSel = args[1];
                
                var headerElements = Array.from(document.querySelectorAll(selJs));
                var headers = headerElements.map(function(h) {
                    return (h.innerText.trim() || h.getAttribute("id") || "").toLowerCase();
                });

                var rows = Array.from(document.querySelectorAll(rowSel));
                var seen = new Set();
                var uniqueResults = [];

                rows.forEach(function(tr) {
                    if (tr.tagName === 'THEAD' || tr.querySelector('th') || tr.querySelector('[role="columnheader"]') || tr.classList.contains('grid-header')) {
                        return;
                    }

                    var cellSelectors = 'td, [role="cell"], [role="gridcell"], .grid-cell';
                    var cells = Array.from(tr.querySelectorAll(cellSelectors));
                
                    var rowData = cells.map(function(td) {
                        var img = td.querySelector('img');
                        if (img) {
                            return img.getAttribute('title') || img.getAttribute('alt') || "";
                        }
                        return td.innerText.trim();
                    });

                    var rowKey = JSON.stringify(rowData);
                    if (!seen.has(rowKey)) {
                        seen.add(rowKey);
                        uniqueResults.push(rowData);
                    }
                });

                return { headers: headers, results: uniqueResults };
            }
        """, [selectors_js, row_selectors])
        
        return ["table", data["headers"], data["results"]]
    
    async def _actuate(self, action: Dict[str, Any], result: List[Any]=None):
        act = action.get("action")
        val = action.get("value")
        chk = action.get("check")
        sym = action.get("sym", "")
        try:
            if act in ["click", "click_if_not_checked"]:
                await self._click(act, val, chk)
            elif act == "wait":
                logger.info(f"Waiting {val} ms.")
                await self.page.wait_for_timeout(val)
            elif act == "mouse_wheel":
                logger.info(f"Scrolling on {val}.")
                box = await self.page.locator(val).bounding_box()
                if box:
                    # Move mouse
                    await self.page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                    # Scrolling
                    chk = float(chk)
                    await self.page.mouse.wheel(0, chk)
            elif act == "filter":
                logger.info(f"Filtering with {val} {sym} {chk}.")
                self._filter(val, chk, sym, result)
        except Exception as e:
            logger.error(f"Could not actuate {act}, value {val}: {e}")

    async def _click(self, act: str, val, chk):
        try:
            logger.info(f"Targeting action [{act}] on selector: {val}")
                
            await self.page.wait_for_selector(val, timeout=2500, state="attached")
                    
            locator = self.page.locator(val).first
            
            should_click = True
            
            if act == "click_if_not_checked":
                classes = ""
                if await locator.count() > 0:
                    classes = await locator.get_attribute("class") or ""
                
                if str(chk) in classes.split():
                    should_click = False
                    logger.info(f"Toggle is already active. Skipping execution.")
            
            if should_click:
                vegades = int(chk) if (act == "click" and chk) else 1
                for _ in range(vegades):
                    try:
                        await locator.click(force=True, timeout=1500)
                        logger.info(f"Successful click dispatch on {val}.")
                    except Exception as e_click:
                        logger.warning(f"Standard click failed. Dispatching native browser click event: {e_click}")
                        await locator.evaluate("el => el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}))")
            
            if act == "click_if_not_checked" and should_click:
                await self.page.wait_for_timeout(300)
                classes_post = await locator.get_attribute("class") or ""
                logger.info(f"Toggle verified. Status: {str(chk) in classes_post.split()}")
                
        except Exception as e:
            logger.warning(f"Could not complete action [{act}] on {val}. Web might be laggy or selector changed. Moving forward... Error: {e}")
    
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
            logger.info(f"Filtering {len(result[2])} rows with column {name} and value {value}.")
            index = result[1].index(name.lower())
            clean_val = _typecast(value)
            filter_row = []
            for row in result[2]:
                try:
                    if index >= len(row):
                        continue
                    web_value = _typecast(row[index])
                    if func(web_value, clean_val):
                        filter_row.append(row)
                except TypeError as e:
                    logger.error(f"Incompatible types during filter evaluation"
                                 f"cannot compare '{row[index]} with '{value}' using '{sym}'. Error: {e}")
                    filter_row.append(row)
            result[2][:] = filter_row