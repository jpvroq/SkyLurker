import os
import json
import logging
from typing import Dict, Any, List
import asyncio
from pathlib import Path

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

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def _execute_single_job(job_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Function to be executen in each thread.
    """
    result = None
    lurker = None
    report = {
            "target": job_config.get("base_url", "ERROR"),
            "type": job_config.get("type", "ERROR"),
            "status": "SUCCESS",
            "data": None
        }
    try:
        logger.info("Creating lurker.")
        lurker = LurkerFactory.create(job_config)
        logger.info(f"Created {lurker.type} lurker for {lurker.base_url}.")
        

        await lurker.connect()
        result = await lurker.lurk()
        await lurker.close()

        report["data"] = result

    except Exception as e:
        logger.error(f"Critical error with concurrent job {report['target']}, type {report['type']}."
                     f"ERROR: {e}")
        report["status"] = "FAILED"
        if lurker and hasattr(lurker, "close"):
            try:
                await lurker.close()
            except:
                pass
    return report

def _save_results(results: List[Dict[str, Any]], filename: str = "default_name.json"):
    """
    Saves result based on configuration.
    """
    output_path = os.path.join(os.getcwd(), filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    logger.info(f"Results saved on: {output_path}")

async def main_async(save_file: str=None):
    logger.info("=== Initializing SkyLurker Concurrent Orchestrator ===")
    path = Path("./configs")
    logger.info(f"Job path: {path}")
    configs = []
    compiled_results = []
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
    logger.info(f"Loaded {len(configs)} jobs. Initializing asynchronous threads...")

    jobs = [_execute_single_job(job) for job in configs]
    compiled_results = await asyncio.gather(*jobs)

    logger.info("=== Concurrent Orchestrator finalized ===")
    
    if save_file:
        _save_results(compiled_results, save_file)
    else:
        return compiled_results

if __name__ == "__main__":
    results = None
    results = asyncio.run(main_async("result.json"))
    if results:
        print(results)