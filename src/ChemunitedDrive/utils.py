from typing import Tuple, Any
from appdirs import user_data_dir
import requests
import inspect


TEMPORARY_FILES_FOLDER = user_data_dir("ChemUnited", "ChemUnited_Recent_Projects")


def is_url_accessible(url: str, timeout=5) -> Tuple[bool, Any]:
    try:
        response = requests.get(
            url=url, timeout=timeout
        )  # Set a timeout to avoid hanging
        if response.status_code == 200:
            try:
                return True, response.json()  # Return parsed JSON if available
            except ValueError:
                return True, response.text  # Return raw text if JSON parsing fails
        else:
            return False, response  # Return the entire response for non-200 status
    except requests.exceptions.RequestException as error:
        print(f"Error while trying to access the URL '{url}': {error}")
        return False, None


def method_params_dict(cls, method_name: str) -> dict:
    fn = getattr(cls, method_name)
    sig = inspect.signature(fn)

    out = {}
    for name, p in sig.parameters.items():
        out[name] = {
            "kind": p.kind.name,
            "default": None if p.default is inspect._empty else p.default,
            "annotation": None if p.annotation is inspect._empty else p.annotation,
        }
    return out
