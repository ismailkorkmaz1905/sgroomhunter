from __future__ import annotations

import importlib.util
import os
from pathlib import Path


APP_PATH = Path(__file__).with_name("app.py")


def load_app():
    spec = importlib.util.spec_from_file_location("wordgames_runtime", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.app


if __name__ == "__main__":
    host = os.environ.get("WORDGAMES_HOST", "0.0.0.0")
    port = int(os.environ.get("WORDGAMES_PORT", "5051"))
    load_app().run(host=host, port=port, debug=False, use_reloader=False)
