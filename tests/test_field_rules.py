from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from src.calculator import FieldParams  # noqa: E402
from src.drawing import _roll_plan_rows, draw_dimension_image  # noqa: E402
from src.standards import get_field_rule, load_field_rules, recommended_template  # noqa: E402


def test_field_rules_json_can_be_read() -> None:
    path = PROJECT_DIR / "knowledge" / "football_field_standards" / "field_rules.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"]
    assert "field_types" in data


def test_each_field_type_has_length_width_range_or_fallback() -> None:
    rules = load_field_rules()["field_types"]
    for field_type, rule in rules.items():
        assert "pitch_length" in rule, field_type
        assert "pitch_width" in rule, field_type
        assert "source" in rule["pitch_length"], field_type
        assert "source" in rule["pitch_width"], field_type


def test_line_width_and_center_circle_are_present() -> None:
    for field_type in load_field_rules()["field_types"]:
        rule = get_field_rule(field_type)
        assert "line_width" in rule
        assert rule["line_width"].get("value") is not None
        assert "center_circle_radius" in rule


def test_11v11_key_markings_are_complete() -> None:
    rule = get_field_rule("11人制足球场")
    assert rule["pitch_length"]["min"] == 90
    assert rule["pitch_width"]["max"] == 90
    assert rule["center_circle_radius"]["value"] == 9.15
    assert rule["penalty_mark_distance"]["value"] == 11
    assert rule["penalty_area"]["depth"] == 16.5
    assert rule["goal_area"]["depth"] == 5.5
    assert rule["goal_size"]["width"] == 7.32


def test_custom_field_can_fallback() -> None:
    template = recommended_template("非标定制场地", {"length": 50, "width": 30})
    assert template["length"] == 50
    assert template["width"] == 30
    assert template["line_width"] > 0


def test_drawing_generation_does_not_crash_with_rules() -> None:
    template = recommended_template("5人制足球场")
    params = FieldParams(
        project_name="标准库测试",
        customer_name="客户",
        field_type="5人制足球场",
        length=template["length"],
        width=template["width"],
        include_buffer=True,
        buffer_left_right=template["buffer_left_right"],
        buffer_top_bottom=template["buffer_top_bottom"],
        main_color="绿色",
        line_color="白色",
        center_circle_radius=template["center_circle_radius"],
        line_width=template["line_width"],
        has_penalty_area=True,
        has_goal_area=True,
        has_halfway_line=True,
        has_center_circle=True,
        has_corner_arc=True,
        color_scheme="深浅绿条纹",
        stripe_width=4,
        waste_rate=5,
        roll_width=4,
        glue_per_sqm=0.25,
        seam_tape_extra_rate=5,
        penalty_area_depth=template["penalty_area_depth"],
        penalty_area_width=template["penalty_area_width"],
        goal_area_depth=template["goal_area_depth"],
        goal_area_width=template["goal_area_width"],
    )
    path = Path(draw_dimension_image(params))
    assert path.exists()


def test_edge_roll_area_uses_actual_width_in_construction_table() -> None:
    """边缘补卷面积按实际窄宽计算，不再强行按4m宽放大。"""
    params = FieldParams(
        project_name="边条面积测试",
        customer_name="客户",
        field_type="5人制足球场",
        length=19.3,
        width=14.7,
        include_buffer=True,
        buffer_left_right=1,
        buffer_top_bottom=1,
        main_color="绿色",
        line_color="白色",
        center_circle_radius=3,
        line_width=0.12,
        has_penalty_area=True,
        has_goal_area=True,
        has_halfway_line=True,
        has_center_circle=True,
        has_corner_arc=True,
        color_scheme="深浅绿条纹",
        stripe_width=2,
        waste_rate=5,
        roll_width=4,
        glue_per_sqm=0,
        seam_tape_extra_rate=5,
        penalty_area_depth=6,
        penalty_area_width=12,
        goal_area_depth=0.8,
        goal_area_width=2.6,
        edge_stripe_mode="自动合并窄边",
    )
    rows = _roll_plan_rows(params, line_area=8, seam_length=0, glue_kg=0)
    edge_row = next(row for row in rows if row[1] == "深色草坪")
    production_row = next(row for row in rows if row[1] == "实际生产面积")

    assert edge_row[2] == "10.855*2m"
    assert edge_row[3] == "1"
    assert edge_row[5] == "21.71"
    assert production_row[5] == "363.71"
