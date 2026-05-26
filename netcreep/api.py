from netcreep.base import NetLurker, RestrictedError
from typing import Union, Dict, Any, List
from dotenv import load_dotenv
import logging
import requests

logger = logging.getLogger(__name__)
# Load api keys and env variables
load_dotenv()

def _delete_dict_node(res: Union[Dict[str, Any], ], nodes: str) -> None:
    keys = nodes.split(".")
    if len(keys) == 1:
        res.pop(keys[0])
    elif keys[0] in res and isinstance(res[keys[0]], dict):
        _delete_dict_node(res[keys[0]], ".".join(keys[1:]))


class APILurker(NetLurker):
    def __init__(self, config: Dict[str, str]):
        super().__init__(config)
        self.jobs = config.get("jobs", [])
    
    def connect(self):
        pass

    def lurk(self):
        akey = self.config.get("access_key", None)
        self.results = []
        api_headers = {
            "User-Agent": self.user_agent
        }

        try:
            for endpoint in self.config.get("endpoints", []):
                api = endpoint.get("api", None)
                if not api:
                    logger.error("No endpoint defined.")
                    raise KeyError("Endpoints must contain an API endpoint.")
                url = self.base_url
                if not url.endswith("/"):
                    url += "/"
                url += api
                self.verify_and_wait(url)
                parameters = {}
                config_key_reference = endpoint.get("access_key_env", None) or self.config.get("access_key_env", None)
                
                akey = None
                if config_key_reference:
                    # Intentamos extraer el valor real del entorno del sistema
                    akey = os.environ.get(config_key_reference)
                    if akey:
                        logger.info(f"API Key loaded securely from environment variable: {config_key_reference}")
                else:
                    akey = endpoint.get("access_key", None) or self.config.get("access_key", None)
                    if akey:
                        logger.warning(f"API Key loaded from configuration file.")
                
                if akey:
                    parameters["access_key"] = akey
                
                for parameter in endpoint.get("parameters", []):
                    param, val = parameter.get("parameter", None), parameter.get("value", None)
                    if param and val:
                        parameters[param] = val
                
                logger.info(f"Sending API request to {url}")
                resp = requests.get(url, headers=api_headers, params=parameters)
                if resp.status_code == 200:
                    result = resp.json()
                    for action in self.config.get("post_actions", []):
                        self._actuate(action, result)
                        self.results.append(result)
                else:
                    logger.error(f"API error. Status code: {resp.status_code}.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Critical error during request: {e}")
        except RestrictedError as re:
            logger.error(f"Restricted access. Cannot lurk.")
        except Exception as e2:
            logger.error(f"Unexpected exception: {e2}")
        
        return self.results
    
    def close(self):
        pass
    
    def _actuate(self, action: Dict[str, Any], result: Any):
        act = action.get("action", None)
        val = action.get("value", None)
        if act == "remove":
            _delete_dict_node(result, val)

