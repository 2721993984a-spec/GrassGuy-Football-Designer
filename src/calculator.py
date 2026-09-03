from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from .standards import corner_arc_radius, five_a_side_template_metrics, is_five_a_side, penalty_arc_radius, penalty_mark_distance
from .utils import glue_bucket_count, round_to_nearest_hundred


@dataclass
class FieldParams:
    project_name: str
    customer_name: str
    field_type: str
    length: float
    width: float
    include_buffer: bool
    buffer_left_right: float
    buffer_top_bottom: float
    main_color: str
    line_color: str
    center_circle_radius: float
    line_width: float
    has_penalty_area: bool
    has_goal_area: bool
    has_halfway_line: bool
    has_center_circle: bool
    has_corner_arc: bool
    color_scheme: str
    stripe_width: float
    waste_rate: float
    roll_width: float
    glue_per_sqm: float
    seam_tape_extra_rate: float
    penalty_area_depth: float = 0
    penalty_area_width: float = 0
    goal_area_depth: float = 0
    goal_area_width: float = 0
    buffer_left: float | None = None
    buffer_right: float | None = None
    buffer_top: float | None = None
    buffer_bottom: float | None = None
    edge_stripe_mode: str = "自动合并窄边"


def buffer_left(params: FieldParams) -> float:
    """读取左侧缓冲区，兼容旧的左右同值参数。"""
    return float(params.buffer_left if params.buffer_left is not None else params.buffer_left_right) if params.include_buffer else 0.0


def buffer_right(params: FieldParams) -> float:
    """读取右侧缓冲区，兼容旧的左右同值参数。"""
    return float(params.buffer_right if params.buffer_right is not None else params.buffer_left_right) if params.include_buffer else 0.0


def buffer_top(params: FieldParams) -> float:
    """读取上侧缓冲区，兼容旧的上下同值参数。"""
    return float(params.buffer_top if params.buffer_top is not None else params.buffer_top_bottom) if params.include_buffer else 0.0


def buffer_bottom(params: FieldParams) -> float:
    """读取下侧缓冲区，兼容旧的上下同值参数。"""
    return float(params.buffer_bottom if params.buffer_bottom is not None else params.buffer_top_bottom) if params.include_buffer else 0.0


def total_length(params: FieldParams) -> float:
    """计算包含左右缓冲区的总长度。"""
    return params.length + buffer_left(params) + buffer_right(params)


def total_width(params: FieldParams) -> float:
    """计算包含上下缓冲区的总宽度。"""
    return params.width + buffer_top(params) + buffer_bottom(params)


def white_grass_area(raw_area: float) -> int:
    """白草面积按生产采购口径向上取整，避免少算。"""
    return int(math.ceil(max(raw_area, 0)))


def is_small_pitch(params: FieldParams) -> bool:
    """五人制和笼式场地使用模板里的小场半圆罚球区画法。"""
    return "5人制" in params.field_type or "笼式" in params.field_type


def _center_circle_radius(params: FieldParams) -> float:
    """五人制中圈半径按模板比例自动推导。"""
    if is_five_a_side(params.field_type):
        return five_a_side_template_metrics(params.length, params.width)["center_circle_radius"]
    return params.center_circle_radius


def _small_pitch_metrics(params: FieldParams) -> dict[str, float]:
    """五人制半圆罚球区和球门开口按模板比例自动推导。"""
    if is_five_a_side(params.field_type):
        metrics = five_a_side_template_metrics(params.length, params.width)
        if params.include_buffer and min(params.buffer_left_right, params.buffer_top_bottom) <= 1.05:
            metrics["goal_area_depth"] = min(metrics["goal_area_depth"], 0.8)
        return metrics
    radius = max(params.penalty_area_depth, params.penalty_area_width / 2, 0.1)
    return {
        "penalty_arc_radius": radius,
        "penalty_mark_distance": penalty_mark_distance(params.field_type, params.length, radius) or radius * 1.65,
        "goal_area_depth": params.goal_area_depth,
        "goal_area_width": params.goal_area_width,
    }


def _arc_line(center_x: float, center_y: float, radius: float, start_deg: float, end_deg: float, steps: int = 72) -> LineString:
    """用点列生成圆弧线，供 Shapely 计算白线面积。"""
    points = []
    for i in range(steps + 1):
        angle = math.radians(start_deg + (end_deg - start_deg) * i / steps)
        points.append((center_x + math.cos(angle) * radius, center_y + math.sin(angle) * radius))
    return LineString(points)


def _mark_spot(x: float, y: float, line_width: float):
    """生成白草实心标记点，避免把点球点算成空心圆环。"""
    radius = max(line_width * 0.9, 0.08)
    return Point(x, y).buffer(radius, resolution=24)


def _five_a_side_penalty_lines(params: FieldParams) -> list[LineString]:
    """五人制模板罚球区：两个门柱点为圆心的四分之一圆弧加连接线。"""
    metrics = _small_pitch_metrics(params)
    radius = metrics["penalty_arc_radius"]
    goal_width = metrics["goal_area_width"]
    goal_y1 = (params.width - goal_width) / 2
    goal_y2 = goal_y1 + goal_width
    length = params.length
    return [
        _arc_line(0, goal_y2, radius, 0, 90),
        _arc_line(0, goal_y1, radius, 270, 360),
        LineString([(radius, goal_y1), (radius, goal_y2)]),
        _arc_line(length, goal_y2, radius, 90, 180),
        _arc_line(length, goal_y1, radius, 180, 270),
        LineString([(length - radius, goal_y1), (length - radius, goal_y2)]),
    ]


def _penalty_arc_lines(params: FieldParams, depth: float) -> list[LineString]:
    """生成矩形罚球区外侧的 D 形罚球弧。"""
    spot_dist = penalty_mark_distance(params.field_type, params.length, depth)
    arc_r = penalty_arc_radius(params.field_type, depth)
    if not spot_dist or not arc_r or arc_r <= 0:
        return []

    lines: list[LineString] = []
    left_box_x = depth
    left_center_x = spot_dist
    if abs(left_box_x - left_center_x) < arc_r:
        angle = math.degrees(math.acos((left_box_x - left_center_x) / arc_r))
        if left_box_x >= left_center_x:
            lines.append(_arc_line(left_center_x, params.width / 2, arc_r, -angle, angle))
        else:
            lines.append(_arc_line(left_center_x, params.width / 2, arc_r, angle, 360 - angle))

    right_box_x = params.length - depth
    right_center_x = params.length - spot_dist
    if abs(right_box_x - right_center_x) < arc_r:
        angle = math.degrees(math.acos((right_box_x - right_center_x) / arc_r))
        if right_box_x <= right_center_x:
            lines.append(_arc_line(right_center_x, params.width / 2, arc_r, angle, 360 - angle))
        else:
            lines.append(_arc_line(right_center_x, params.width / 2, arc_r, -angle, angle))
    return lines


def build_line_geometry(params: FieldParams):
    """用线条几何生成白线区域，便于计算白线草面积。"""
    lines = []
    spot_geoms = []
    length, width = params.length, params.width

    lines.append(LineString([(0, 0), (length, 0), (length, width), (0, width), (0, 0)]))

    if params.has_halfway_line:
        lines.append(LineString([(length / 2, 0), (length / 2, width)]))

    center_r = _center_circle_radius(params)
    if params.has_center_circle and center_r > 0:
        circle = Point(length / 2, width / 2).buffer(center_r, resolution=96).boundary
        lines.append(circle)
        spot_geoms.append(_mark_spot(length / 2, width / 2, params.line_width))

    if params.has_penalty_area and params.penalty_area_depth > 0 and params.penalty_area_width > 0:
        if is_small_pitch(params):
            metrics = _small_pitch_metrics(params)
            if is_five_a_side(params.field_type):
                lines.extend(_five_a_side_penalty_lines(params))
            else:
                radius = metrics["penalty_arc_radius"]
                lines.append(_arc_line(0, width / 2, radius, -90, 90))
                lines.append(_arc_line(length, width / 2, radius, 90, 270))
            spot_dist = metrics["penalty_mark_distance"]
            if spot_dist:
                spot_geoms.append(_mark_spot(spot_dist, width / 2, params.line_width))
                spot_geoms.append(_mark_spot(length - spot_dist, width / 2, params.line_width))
        else:
            y1 = (width - params.penalty_area_width) / 2
            y2 = y1 + params.penalty_area_width
            d = min(params.penalty_area_depth, length / 3)
            lines.append(LineString([(0, y1), (d, y1), (d, y2), (0, y2)]))
            lines.append(LineString([(length, y1), (length - d, y1), (length - d, y2), (length, y2)]))
            lines.extend(_penalty_arc_lines(params, d))
            spot_dist = penalty_mark_distance(params.field_type, length, d)
            if spot_dist:
                spot_geoms.append(_mark_spot(spot_dist, width / 2, params.line_width))
                spot_geoms.append(_mark_spot(length - spot_dist, width / 2, params.line_width))

    if params.has_goal_area and params.goal_area_depth > 0 and params.goal_area_width > 0:
        if is_small_pitch(params):
            metrics = _small_pitch_metrics(params)
            goal_depth = metrics["goal_area_depth"]
            goal_width = metrics["goal_area_width"]
        else:
            goal_depth = params.goal_area_depth
            goal_width = params.goal_area_width
        y1 = (width - goal_width) / 2
        y2 = y1 + goal_width
        d = min(goal_depth, length / 5)
        lines.append(LineString([(0, y1), (d, y1), (d, y2), (0, y2)]))
        lines.append(LineString([(length, y1), (length - d, y1), (length - d, y2), (length, y2)]))

    if params.has_corner_arc:
        r = corner_arc_radius(params.field_type, length, width)
        for x, y in [(0, 0), (0, width), (length, 0), (length, width)]:
            lines.append(Point(x, y).buffer(r, resolution=32).boundary)

    if not lines and not spot_geoms:
        return None
    line_surface = unary_union(lines).buffer(params.line_width / 2, cap_style=2, join_style=2) if lines else None
    geometries = [geom for geom in [line_surface, *spot_geoms] if geom is not None]
    return unary_union(geometries)


def calculate_color_areas(params: FieldParams, line_area: float) -> pd.DataFrame:
    """根据分色方案计算不同颜色草坪面积。"""
    field_area = params.length * params.width
    total_sqm = total_area(params)
    playable_green_area = max(total_sqm - line_area, 0)
    rows = []

    def add(color: str, usage: str, net_area: float, note: str = "", integer_area: bool = False) -> None:
        suggested = net_area * (1 + params.waste_rate / 100)
        total_len = total_length(params)
        rolls = math.ceil(suggested / max(params.roll_width * total_len, 1))
        net_area_display = str(int(net_area)) if integer_area else f"{net_area:.2f}"
        rows.append(
            {
                "颜色": color,
                "用途": usage,
                "净面积㎡": net_area_display,
                "损耗率": f"{params.waste_rate:.1f}%",
                "损耗面积㎡": round(suggested - net_area, 2),
                "建议采购面积㎡": round(suggested, 2),
                "卷宽": params.roll_width,
                "建议卷数": max(rolls, 1) if net_area > 0 else 0,
                "备注": note,
            }
        )

    if params.color_scheme == "深浅绿条纹":
        dark_area, light_area = stripe_areas(params, playable_green_area)
        add("深绿色", "条纹主草", dark_area, f"按场地长度方向 {params.stripe_width:g}m 深浅交替")
        add("浅绿色", "条纹主草", light_area, f"按场地长度方向 {params.stripe_width:g}m 深浅交替")
    elif params.color_scheme == "中间深绿，两侧浅绿":
        add("深绿色", "中间区域主草", playable_green_area * 0.5, "中间约 50% 宽度")
        add("浅绿色", "两侧区域主草", playable_green_area * 0.5, "左右两侧合计")
    elif params.color_scheme == "外围深绿，内场浅绿":
        border_area = field_area * 0.18
        add("深绿色", "外围区域主草", min(border_area, playable_green_area), "外围装饰色")
        add("浅绿色", "内场区域主草", max(playable_green_area - border_area, 0), "内场主要铺装")
    elif params.color_scheme == "自定义颜色区域":
        add(params.main_color, "自定义主草区域", playable_green_area, "第一版按单一主草统计，可人工调整")
    else:
        add(params.main_color, "主草", playable_green_area, "全场主草")

    add(params.line_color, "足球场白线", line_area, "由 Shapely 线条缓冲几何计算，白草面积按整数㎡取整", integer_area=True)
    return pd.DataFrame(rows)


def stripe_areas(params: FieldParams, turf_area_after_lines: float) -> tuple[float, float]:
    """按中线居中浅色条纹的规则估算深浅草面积。"""
    total_len = total_length(params)
    total_wid = total_width(params)
    stripe_width = max(params.stripe_width, 0.1)
    dark = 0.0
    light = 0.0
    center = buffer_left(params) + params.length / 2
    cuts = {0.0, total_len}
    left = center - stripe_width / 2
    right = center + stripe_width / 2
    while left > 0:
        cuts.add(left)
        left -= stripe_width
    while right < total_len:
        cuts.add(right)
        right += stripe_width
    sorted_cuts = sorted(cuts)
    for start, end in zip(sorted_cuts, sorted_cuts[1:]):
        mid = (start + end) / 2
        dist = abs(mid - center)
        band = 0 if dist <= stripe_width / 2 else math.floor((dist - stripe_width / 2) / stripe_width) + 1
        area = (end - start) * total_wid
        if band % 2 == 0:
            light += area
        else:
            dark += area
    if len(sorted_cuts) > 2 and params.edge_stripe_mode == "自动合并窄边":
        edge_threshold = min(stripe_width * 0.30, 1.0)
        first_width = sorted_cuts[1] - sorted_cuts[0]
        if first_width < edge_threshold:
            first_mid = (sorted_cuts[0] + sorted_cuts[1]) / 2
            first_dist = abs(first_mid - center)
            first_band = 0 if first_dist <= stripe_width / 2 else math.floor((first_dist - stripe_width / 2) / stripe_width) + 1
            first_area = first_width * total_wid
            if first_band % 2 == 0:
                light -= first_area
                dark += first_area
            else:
                dark -= first_area
                light += first_area
        last_width = sorted_cuts[-1] - sorted_cuts[-2]
        if last_width < edge_threshold:
            last_mid = (sorted_cuts[-2] + sorted_cuts[-1]) / 2
            last_dist = abs(last_mid - center)
            last_band = 0 if last_dist <= stripe_width / 2 else math.floor((last_dist - stripe_width / 2) / stripe_width) + 1
            last_area = last_width * total_wid
            if last_band % 2 == 0:
                light -= last_area
                dark += last_area
            else:
                dark -= last_area
                light += last_area
    total = max(dark + light, 1)
    return turf_area_after_lines * dark / total, turf_area_after_lines * light / total


def total_area(params: FieldParams) -> float:
    """计算含缓冲区的总面积。"""
    return total_length(params) * total_width(params)


def calculate_accessories(params: FieldParams, total_sqm: float) -> pd.DataFrame:
    """用第一版经验参数估算辅材用量。"""
    total_len = total_length(params)
    total_wid = total_width(params)
    rolls_across_length = math.ceil(total_len / max(params.roll_width, 0.1))
    roll_seam_length = max(rolls_across_length - 1, 0) * total_wid
    line_geom = build_line_geometry(params)
    line_seam_length = line_geom.length if line_geom else 0
    seam_length = roll_seam_length + line_seam_length
    seam_length *= 1 + params.seam_tape_extra_rate / 100
    seam_length_rounded = round_to_nearest_hundred(seam_length)
    glue_buckets = glue_bucket_count(total_sqm)
    rows = [
        ["接缝布", "米", seam_length_rounded, "草卷接缝 + 白线安装接缝，再加余量后按整百取整", f"原始估算 {seam_length:.2f}m"],
        ["胶水", "桶", glue_buckets, "按模板 700㎡=6桶折算", f"场地面积 {total_sqm:.2f}㎡"],
    ]
    return pd.DataFrame(rows, columns=["材料名称", "单位", "估算用量", "计算依据", "备注"])


def calculate_all(params: FieldParams) -> dict:
    """汇总面积、草坪用量和辅材用量。"""
    line_geom = build_line_geometry(params)
    field = box(0, 0, params.length, params.width)
    raw_line_area = line_geom.intersection(field).area if line_geom else 0
    line_area = white_grass_area(raw_line_area)
    total_sqm = total_area(params)
    turf_df = calculate_color_areas(params, line_area)
    accessory_df = calculate_accessories(params, total_sqm)
    return {
        "总长度": total_length(params),
        "总宽度": total_width(params),
        "场地总面积": round(total_sqm, 2),
        "主场地面积": round(params.length * params.width, 2),
        "白线面积": line_area,
        "草坪用量": turf_df,
        "辅材用量": accessory_df,
        "line_geometry": line_geom,
    }
