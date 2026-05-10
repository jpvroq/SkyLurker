from typing import Dict, Union, Any
from .static import StaticLurker
from .dynamic import DynamicLurker
from .base import TestLurker
from pathlib import Path
import json
class CreepFactory:
    @classmethod
    def create(cls, config_input: Union[str, Any]):
        if isinstance(config_input, str):
            config = _load_from_file(config_input)
        else:
            config = config_input
        type = config.get("type").lower()

        if type == "static": return StaticLurker(config)
        if type == "dynamic": return DynamicLurker(config)
        if type == "API": return APILurker(config)
        if type == "test": return TestCreep(config)
        # TODO: exception
    
    def _load_from_file(path_json: str) -> Dict[str, str]:
        """
        Parses the json file containing the site crawler configuration.
        """
        path = Path(path_json)
        if path.exists():
            with open(path, 'r', encoding="utf-8") as f:
                return json.load(f)
        raise FileExistsError("Config file does not exist")
