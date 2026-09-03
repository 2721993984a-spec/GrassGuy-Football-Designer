from __future__ import annotations

import json
from typing import Any

from .utils import BASE_DIR


RULES_FILE = BASE_DIR / "knowledge" / "football_field_standards" / "field_rules.json"

FIELD_TYPE_ALIASES = {
    "非标定制场地": "非标定制足球场",
}

FIVE_A_SIDE_TEMPLATE = {
    "length": 31.50,
    "width": 17.20,
    "buffer": 1.00,
    "penalty_arc_radius": 4.50,
    "center_circle_radius": 2.25,
    "penalty_mark_distance": 7.50,
    "goal_opening_width": 2.34,
    "goal_box_depth": 1.00,
}


def is_five_a_side(field_type: str) -> bool:
    """判断是否使用五人制模板比例。"""
    return "5人制" in field_type


def five_a_side_template_metrics(length: float, width: float) -> dict[str, float]:
    """按万盈镇沈灶小学五人制模板比例推导标线尺寸。"""
    base = FIVE_A_SIDE_TEMPLATE
    penalty_r = width * base["penalty_arc_radius"] / base["width"]
    center_r = width * base["center_circle_radius"] / base["width"]
    spot = length * base["penalty_mark_distance"] / base["length"]
    goal_width = width * base["goal_opening_width"] / base["width"]
    goal_depth = length * base["goal_box_depth"] / base["length"]
    return {
        "penalty_arc_radius": penalty_r,
        "penalty_area_depth": penalty_r,
        "penalty_area_width": penalty_r * 2,
        "center_circle_radius": center_r,
        "penalty_mark_distance": spot if spot < length / 2 else length * 0.35,
        "goal_area_depth": goal_depth,
        "goal_area_width": goal_width,
    }


def load_field_rules() -> dict[str, Any]:
    """读取足球场标准经验库。"""
    with RULES_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize_field_type(field_type: str) -> str:
    """统一旧模板名称和标准库名称。"""
    return FIELD_TYPE_ALIASES.get(field_type, field_type)


def get_field_rule(field_type: str) -> dict[str, Any]:
    """按场地类型读取标准规则，找不到时回落到非标规则。"""
    rules = load_field_rules()["field_types"]
    normalized = normalize_field_type(field_type)
    return rules.get(normalized, rules["非标定制足球场"])


def number_at(rule: dict[str, Any], section: str, key: str = "value") -> float | None:
    """从标准库节点里安全读取数值。"""
    value = rule.get(section, {}).get(key)
    return float(value) if value is not None else None


def recommended_template(field_type: str, fallback: dict[str, Any] | None = None) -> dict[str, float]:
    """把标准库转换成页面默认参数。"""
    fallback = fallback or {}
    rule = get_field_rule(field_type)

    def choose(section: str, key: str, fallback_key: str, default: float = 0.0) -> float:
        value = rule.get(section, {}).get(key)
        if value is None:
            value = fallback.get(fallback_key, default)
        return float(value or default)

    runoff = rule.get("runoff_area", {})
    side_buffer = runoff.get("side")
    end_buffer = runoff.get("end")

    return {
        "length": choose("pitch_length", "recommended", "length", 50.0),
        "width": choose("pitch_width", "recommended", "width", 30.0),
        "buffer_left_right": float(side_buffer if side_buffer is not None else fallback.get("buffer_left_right", 1.0)),
        "buffer_top_bottom": float(end_buffer if end_buffer is not None else fallback.get("buffer_top_bottom", 1.0)),
        "center_circle_radius": choose("center_circle_radius", "value", "center_circle_radius", 3.0),
        "line_width": choose("line_width", "value", "line_width", 0.08),
        "penalty_area_depth": choose("penalty_area", "depth", "penalty_area_depth", 0.0),
        "penalty_area_width": choose("penalty_area", "width", "penalty_area_width", 0.0),
        "goal_area_depth": choose("goal_area", "depth", "goal_area_depth", 0.0),
        "goal_area_width": choose("goal_area", "width", "goal_area_width", 0.0),
    }


def corner_arc_radius(field_type: str, length: float, width: float) -> float:
    """按标准库读取角球弧半径，缺失时使用保守 fallback。"""
    value = number_at(get_field_rule(field_type), "corner_arc_radius")
    if value is not None:
        return value
    return min(1.0, length / 40, width / 20)


def penalty_mark_distance(field_type: str, length: float, penalty_depth: float) -> float | None:
    """读取点球点距离；缺失时给出可画图的保守 fallback。"""
    if is_five_a_side(field_type):
        return five_a_side_template_metrics(length, 17.20)["penalty_mark_distance"]
    value = number_at(get_field_rule(field_type), "penalty_mark_distance")
    if value is not None and value < length / 2:
        return value
    if penalty_depth > 0:
        fallback = penalty_depth * 0.65
        return fallback if fallback < length / 2 else None
    return None


def penalty_arc_radius(field_type: str, penalty_depth: float) -> float | None:
    """读取罚球弧半径；缺失时用罚球区深度的一半作为小场显示 fallback。"""
    if is_five_a_side(field_type):
        return penalty_depth if penalty_depth > 0 else FIVE_A_SIDE_TEMPLATE["penalty_arc_radius"]
    value = number_at(get_field_rule(field_type), "penalty_arc_radius")
    if value is not None:
        return value
    if penalty_depth > 0:
        return penalty_depth / 2
    return None


def goal_size(field_type: str) -> tuple[float | None, float | None]:
    """读取球门宽高。"""
    rule = get_field_rule(field_type)
    goal = rule.get("goal_size", {})
    width = goal.get("width")
    height = goal.get("height")
    return (float(width) if width is not None else None, float(height) if height is not None else None)


def validate_pitch_size(field_type: str, length: float, width: float) -> list[str]:
    """检查当前长宽是否落在标准范围内。"""
    rule = get_field_rule(field_type)
    messages: list[str] = []
    for label, section, value in [("长度", "pitch_length", length), ("宽度", "pitch_width", width)]:
        data = rule.get(section, {})
        minimum = data.get("min")
        maximum = data.get("max")
        if minimum is None or maximum is None:
            messages.append(f"{label}暂无权威范围，当前按非标/经验值处理。")
            continue
        if value < minimum:
            messages.append(f"当前{label} {value:g}m 低于标准范围 {minimum:g}-{maximum:g}m。")
        elif value > maximum:
            messages.append(f"当前{label} {value:g}m 高于标准范围 {minimum:g}-{maximum:g}m。")
    return messages


def rule_source_summary(field_type: str) -> str:
    """生成页面和图纸可显示的来源说明。"""
    rule = get_field_rule(field_type)
    source_id = rule.get("primary_source", "")
    source = load_field_rules().get("sources", {}).get(source_id, {})
    source_name = source.get("name", source_id or "未指定来源")
    level = rule.get("source_level", "unknown")
    return f"{source_name}（{level}）"
