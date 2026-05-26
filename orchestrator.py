import os
import json
import logging
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from netcreep import LurkerFactory

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="skylurker_execution.log",
    filemode="w"
)
# Add console logging
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"))
logging.getLogger("").addHandler(console)

logger = logging.getLogger(__name__)

def _execute_single_job(job_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Function to be executen in each thread.
    """
    result = None
    report = {
            "target": job_config.get("base_url", "ERROR"),
            "type": job_config.get("type", "ERROR"),
            "status": "SUCCESS",
            "data": None
        }
    try:
        logger.info("Creating lurker.")
        lurker = LurkerFactory(job_config)
        logger.info(f"Created {lurker.type} lurker for {lurker.base_url}.")
        

        lurker.connect()
        result = lurker.lurk()
        lurker.close()

        report["data"] = result

    except Exception as e:
        logger.error(f"Critical error with concurrent job {report['base_url']}, type {report['type']}."
                     f"ERROR: {e}")
        report["status"] = "FAILED"
        if lurker and hasattr(lurker, "close"):
            try:
                lurker.close()
            except:
                pass
    return report

def _save_results(results: List[Dict[str, Any]], filename: str = "default_name.json"):
    """
    Saves result based on configuration.
    """
    raise NotImplemented("Function not implemented.")

def orchestrator():
    logger.info("=== Initializing SkyLurker Concurrent Orchestrator ===")
    path = Path("./configs")
    logger.info(f"Job path: {path}")
    configs = []
    for file in path.glob("*.json"):
        if file.name.startswith("exclude_"):
            logger.info(f"Excluding file {file.name}")
            continue
        logger.info(f"Configuration {file.name} loaded.")
        try:
            with open(file, "r", encoding="utf-8") as f:
                configs.append(json.load(f))
        except json.JSONDecodeError as e:
            logger.error(f"Cannot decode JSON file {file.name}. {e}")
    logger.info(f"Loaded {len(configs)} jobs. Initializing Threads...")

    compiled_results = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures_map = {executor.submit(_execute_single_job, job): job for job in configs}
        
        for future in as_completed(futures_map):
            job_result = futures_map[future]
            try:
                result = future.result()
                compiled_results.append(result)
                logger.info(f"Job completed for {result['target']}. Status: {result['status']}.")
            except Exception as e:
                logger.error(f"Thread for job {job_result.get('base_url')} has encountered an error."
                             f"ERROR: {e}")
    logger.info("=== Concurrent Orchestrator finalized ===")
    return compiled_results
