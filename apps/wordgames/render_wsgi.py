from __future__ import annotations

import importlib.util
from pathlib import Path


APP_PATH = Path(__file__).with_name("app.py")


def load_app():
    spec = importlib.util.spec_from_file_location("wordgames_render_runtime", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.app


app = load_app()
