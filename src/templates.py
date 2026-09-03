from __future__ import annotations

import json
from pathlib import Path

from .utils import BASE_DIR


TEMPLATE_FILE = BASE_DIR / "config" / "field_templates.json"


def load_field_templates() -> dict:
    """读取场地类型默认尺寸参数。"""
    with TEMPLATE_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_template(field_type: str) -> dict:
    """按场地类型返回模板；找不到时返回非标模板。"""
    templates = load_field_templates()
    return templates.get(field_type, templates["非标定制场地"])
