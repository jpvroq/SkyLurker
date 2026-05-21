from pathlib import Path
import netcreep
import logging
import json
import os

logger = logging.Logger(__name__)

if __name__ == "__main__":
    path = Path("./configs")
    for file in path.glob("*.json"):
        if file.name.startswith("exclude_"):
            logger.info(f"Excluding file {file.name}")
            continue
        logger.info(f"Configuration {file.name}.")
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                try:
                    lurker = netcreep.LurkerFactory.create(data)
                    lurker.connect()
                    data = lurker.lurk()
                    lurker.close()
                except Exception as e:
                    logger.error(f"Lurker error: {e}")
                print(data)
        except json.JSONDecodeError as e:
            logger.error(f"Cannot decode JSON file {file.name}. {e}")
