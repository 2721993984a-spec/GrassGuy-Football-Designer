from __future__ import annotations

import math
import os
from datetime import datetime
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / "logs" / "matplotlib"))

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Arc, Circle, Rectangle
from shapely.geometry import box

from .calculator import FieldParams, build_line_geometry, is_small_pitch, total_area, white_grass_area
from .standards import corner_arc_radius, five_a_side_template_metrics, is_five_a_side, penalty_arc_radius, penalty_mark_distance
from .utils import IMAGE_DIR, glue_bucket_count, round_to_nearest_hundred, safe_filename, unique_path


COLOR_MAP = {
    "绿色": "#2f9e44",
    "深绿色": "#116530",
    "浅绿色": "#56b947",
    "白色": "#ffffff",
    "黄色": "#ffd43b",
    "蓝色": "#228be6",
    "红色": "#fa5252",
}


def _setup_chinese_font() -> None:
    """设置中文字体，保证图纸文字能正常显示。"""
    for font_path in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc"]:
        if Path(font_path).exists():
            font_manager.fontManager.addfont(font_path)
            plt.rcParams["font.sans-serif"] = [font_manager.FontProperties(fname=font_path).get_name()]
            plt.rcParams["axes.unicode_minus"] = False
            return


_setup_chinese_font()


def _color(name: str) -> str:
    return COLOR_MAP.get(name, name or "#2f9e44")


def _fmt_dim(value: float) -> str:
    """统一尺寸标注格式。"""
    return f"{value:.2f}"


def _roll_layout(total_len: float, roll_width: float) -> tuple[int, float, bool]:
    """计算施工排卷：只在最边卷不足整卷宽时返回补卷。"""
    width = max(roll_width, 0.1)
    full_rolls = max(math.floor(total_len / width), 1)
    edge_width = max(total_len - full_rolls * width, 0)
    has_edge_roll = edge_width > 0.05
    return full_rolls, edge_width, has_edge_roll


def _is_small_pitch(params: FieldParams) -> bool:
    """五人制和笼式场地更接近小场半圆罚球区画法。"""
    return is_small_pitch(params)


def _center_circle_radius(params: FieldParams) -> float:
    """五人制按模板比例推导中圈半径，其他场地使用输入值。"""
    if is_five_a_side(params.field_type):
        return five_a_side_template_metrics(params.length, params.width)["center_circle_radius"]
    return params.center_circle_radius


def _small_pitch_metrics(params: FieldParams) -> dict[str, float]:
    """五人制按模板比例推导半圆罚球区和球门开口尺寸。"""
    if is_five_a_side(params.field_type):
        metrics = five_a_side_template_metrics(params.length, params.width)
        if params.include_buffer and min(params.buffer_left_right, params.buffer_top_bottom) <= 1.05:
            metrics["goal_area_depth"] = min(metrics["goal_area_depth"], 0.8)
        return metrics
    radius = max(params.penalty_area_depth, params.penalty_area_width / 2, 0.1)
    return {
        "penalty_arc_radius": radius,
        "penalty_area_depth": radius,
        "penalty_area_width": radius * 2,
        "penalty_mark_distance": penalty_mark_distance(params.field_type, params.length, radius) or radius * 1.65,
        "goal_area_depth": params.goal_area_depth,
        "goal_area_width": params.goal_area_width,
    }


def _is_seven_template(params: FieldParams) -> bool:
    """七人制按用户提供的模板做更克制的数字标注。"""
    return "7人制" in params.field_type


def _use_clean_dimension_template(params: FieldParams) -> bool:
    """尺寸图统一使用客户模板风格：少文字、少引线、关键数字分区标注。"""
    return True


def _new_sheet(title: str):
    """创建接近参考 PDF 的横版图纸画布。"""
    fig = plt.figure(figsize=(13.18, 9.92), dpi=150, facecolor="white")
    fig.add_artist(Rectangle((0.022, 0.025), 0.956, 0.95, fill=False, edgecolor="#333333", linewidth=0.8, transform=fig.transFigure))
    fig.text(0.06, 0.88, title, color="#00e31b", fontsize=42, ha="left", va="center")
    return fig


def _title_block(fig, params: FieldParams) -> None:
    """绘制右下角标题栏。"""
    x, y, w, h = 0.60, 0.09, 0.28, 0.11
    fig.add_artist(Rectangle((x, y), w, h, fill=False, edgecolor="#333333", linewidth=0.8, transform=fig.transFigure))
    for i in range(1, 4):
        yy = y + h * i / 4
        fig.add_artist(Line2D([x, x + w], [yy, yy], color="#333333", linewidth=0.6, transform=fig.transFigure))
    fig.add_artist(Line2D([x + w * 0.27, x + w * 0.27], [y, y + h], color="#333333", linewidth=0.6, transform=fig.transFigure))
    labels = ["工程名称", "图纸类型", "制图单位", "日期"]
    values = [params.project_name, f"{params.field_type}人造草坪施工图", "草皮哥", datetime.now().strftime("%Y.%m.%d")]
    for i, (label, value) in enumerate(zip(labels, values)):
        yy = y + h * (3.5 - i) / 4
        fig.text(x + 0.01, yy, label, fontsize=12, ha="left", va="center")
        fig.text(x + w * 0.31, yy, value, fontsize=12, ha="left", va="center")


def _notes(fig, params: FieldParams) -> None:
    """绘制左下角备注，风格参考用户提供的 PDF。"""
    note = (
        "备注：\n"
        f"1. 场地比赛区域尺寸{params.length:g}m*{params.width:g}m，白草宽度{params.line_width:g}m；\n"
        "2. 现场施工时，请按照设计图纸的草卷编号顺序摆放，\n"
        "   否则因此造成的铺装问题公司概不承担责任；\n"
        "3. 施工时请按照设计图纸的胶水用量以确保粘接效果。"
    )
    fig.text(0.125, 0.205, note, fontsize=14, ha="left", va="top", linespacing=1.28)


def _field_axis(fig, params: FieldParams, y0: float = 0.31, height: float = 0.50):
    ax = fig.add_axes([0.20, y0, 0.56, height])
    ax.set_aspect("equal")
    margin_x = max(params.length * 0.04, params.buffer_left_right if params.include_buffer else 0)
    margin_y = max(params.width * 0.08, params.buffer_top_bottom if params.include_buffer else 0)
    ax.set_xlim(-margin_x, params.length + margin_x)
    ax.set_ylim(-margin_y, params.width + margin_y)
    ax.axis("off")
    return ax


def _draw_pitch_lines(ax, params: FieldParams, color: str = "#333333", lw: float = 1.2, center_mark_color: str | None = "auto") -> None:
    """绘制足球场基础标线。"""
    length, width = params.length, params.width
    ax.add_patch(Rectangle((0, 0), length, width, fill=False, edgecolor=color, linewidth=lw))

    if params.has_halfway_line:
        ax.plot([length / 2, length / 2], [0, width], color=color, linewidth=lw)

    if params.has_center_circle:
        ax.add_patch(Circle((length / 2, width / 2), _center_circle_radius(params), fill=False, edgecolor=color, linewidth=lw))
        if center_mark_color:
            marker_color = color if center_mark_color == "auto" else center_mark_color
            ax.plot(length / 2, width / 2, marker=".", color=marker_color, markersize=5)

    if params.has_penalty_area:
        if _is_small_pitch(params):
            _draw_small_pitch_penalty_arcs(ax, params, color, lw)
        else:
            _draw_boxes(ax, params, params.penalty_area_depth, params.penalty_area_width, color, lw)
            _draw_penalty_arcs_for_boxes(ax, params, params.penalty_area_depth, color, lw)

    if params.has_goal_area:
        if _is_small_pitch(params):
            _draw_template_goal_boxes(ax, params, color, lw)
        else:
            _draw_boxes(ax, params, params.goal_area_depth, params.goal_area_width, color, lw)

    if params.has_corner_arc:
        r = corner_arc_radius(params.field_type, length, width)
        ax.add_patch(Arc((0, 0), r * 2, r * 2, theta1=0, theta2=90, edgecolor=color, linewidth=lw))
        ax.add_patch(Arc((0, width), r * 2, r * 2, theta1=270, theta2=360, edgecolor=color, linewidth=lw))
        ax.add_patch(Arc((length, 0), r * 2, r * 2, theta1=90, theta2=180, edgecolor=color, linewidth=lw))
        ax.add_patch(Arc((length, width), r * 2, r * 2, theta1=180, theta2=270, edgecolor=color, linewidth=lw))


def _draw_boxes(ax, params: FieldParams, depth: float, box_width: float, color: str, lw: float) -> None:
    """绘制罚球区或球门区。"""
    if depth <= 0 or box_width <= 0:
        return
    y = (params.width - box_width) / 2
    ax.add_patch(Rectangle((0, y), depth, box_width, fill=False, edgecolor=color, linewidth=lw))
    ax.add_patch(Rectangle((params.length - depth, y), depth, box_width, fill=False, edgecolor=color, linewidth=lw))


def _draw_penalty_arcs_for_boxes(ax, params: FieldParams, depth: float, color: str, lw: float) -> None:
    """绘制矩形罚球区外侧的 D 形罚球弧和点球点。"""
    spot_dist = penalty_mark_distance(params.field_type, params.length, depth)
    arc_r = penalty_arc_radius(params.field_type, depth)
    if not spot_dist or not arc_r or arc_r <= 0:
        return

    left_box_x = depth
    left_center_x = spot_dist
    if abs(left_box_x - left_center_x) < arc_r:
        angle = math.degrees(math.acos((left_box_x - left_center_x) / arc_r))
        if left_box_x >= left_center_x:
            theta1, theta2 = -angle, angle
        else:
            theta1, theta2 = angle, 360 - angle
        ax.add_patch(Arc((left_center_x, params.width / 2), arc_r * 2, arc_r * 2, theta1=theta1, theta2=theta2, edgecolor=color, linewidth=lw))

    right_box_x = params.length - depth
    right_center_x = params.length - spot_dist
    if abs(right_box_x - right_center_x) < arc_r:
        angle = math.degrees(math.acos((right_box_x - right_center_x) / arc_r))
        if right_box_x <= right_center_x:
            theta1, theta2 = angle, 360 - angle
        else:
            theta1, theta2 = -angle, angle
        ax.add_patch(Arc((right_center_x, params.width / 2), arc_r * 2, arc_r * 2, theta1=theta1, theta2=theta2, edgecolor=color, linewidth=lw))

    ax.plot([spot_dist, params.length - spot_dist], [params.width / 2, params.width / 2], linestyle="None", marker=".", color=color, markersize=3)


def _draw_small_pitch_penalty_arcs(ax, params: FieldParams, color: str, lw: float) -> None:
    """绘制小场罚球区：五人制模板按两个门柱点为圆心画两段圆弧。"""
    metrics = _small_pitch_metrics(params)
    radius = metrics["penalty_arc_radius"]
    if is_five_a_side(params.field_type):
        goal_width = metrics["goal_area_width"]
        goal_y1 = (params.width - goal_width) / 2
        goal_y2 = goal_y1 + goal_width
        ax.add_patch(Arc((0, goal_y2), radius * 2, radius * 2, theta1=0, theta2=90, edgecolor=color, linewidth=lw))
        ax.add_patch(Arc((0, goal_y1), radius * 2, radius * 2, theta1=270, theta2=360, edgecolor=color, linewidth=lw))
        ax.plot([radius, radius], [goal_y1, goal_y2], color=color, linewidth=lw)
        ax.add_patch(Arc((params.length, goal_y2), radius * 2, radius * 2, theta1=90, theta2=180, edgecolor=color, linewidth=lw))
        ax.add_patch(Arc((params.length, goal_y1), radius * 2, radius * 2, theta1=180, theta2=270, edgecolor=color, linewidth=lw))
        ax.plot([params.length - radius, params.length - radius], [goal_y1, goal_y2], color=color, linewidth=lw)
    else:
        ax.add_patch(Arc((0, params.width / 2), radius * 2, radius * 2, theta1=-90, theta2=90, edgecolor=color, linewidth=lw))
        ax.add_patch(Arc((params.length, params.width / 2), radius * 2, radius * 2, theta1=90, theta2=270, edgecolor=color, linewidth=lw))
    spot_dist = metrics["penalty_mark_distance"]
    if spot_dist:
        ax.plot([spot_dist, params.length - spot_dist], [params.width / 2, params.width / 2], linestyle="None", marker=".", color=color, markersize=3)


def _draw_template_goal_boxes(ax, params: FieldParams, color: str, lw: float) -> None:
    """绘制模板里的小球门矩形，贴边居中。"""
    metrics = _small_pitch_metrics(params)
    goal_depth = metrics["goal_area_depth"]
    goal_width = metrics["goal_area_width"]
    if not params.has_goal_area or goal_depth <= 0 or goal_width <= 0:
        return
    y = (params.width - goal_width) / 2
    d = min(goal_depth, params.length * 0.08)
    ax.add_patch(Rectangle((-d, y), d, goal_width, fill=False, edgecolor=color, linewidth=lw))
    ax.add_patch(Rectangle((params.length, y), d, goal_width, fill=False, edgecolor=color, linewidth=lw))


def _draw_buffer(ax, params: FieldParams, facecolor: str | None = None, edgecolor: str = "#333333") -> None:
    if not params.include_buffer:
        return
    x = -params.buffer_left_right
    y = -params.buffer_top_bottom
    w = params.length + params.buffer_left_right * 2
    h = params.width + params.buffer_top_bottom * 2
    ax.add_patch(Rectangle((x, y), w, h, facecolor=facecolor or "none", fill=facecolor is not None, edgecolor=edgecolor, linewidth=0.9))


def _dim_line(ax, start, end, text: str, offset=(0, 0), rotation=0) -> None:
    color = "#ff00ff"
    sx, sy = start
    ex, ey = end
    ox, oy = offset
    dim_start = (sx + ox, sy + oy)
    dim_end = (ex + ox, ey + oy)
    ax.plot([dim_start[0], dim_end[0]], [dim_start[1], dim_end[1]], color=color, lw=1.05, alpha=0.95, zorder=5, clip_on=False)
    ax.annotate(
        "",
        xy=dim_end,
        xytext=dim_start,
        arrowprops=dict(arrowstyle="<->", color=color, lw=1.25, shrinkA=0, shrinkB=0, mutation_scale=16),
        annotation_clip=False,
        zorder=6,
    )
    if ox:
        ax.plot([sx, sx + ox], [sy, sy + oy], color=color, lw=0.65, alpha=0.7, clip_on=False)
        ax.plot([ex, ex + ox], [ey, ey + oy], color=color, lw=0.65, alpha=0.7, clip_on=False)
    if oy:
        ax.plot([sx, sx + ox], [sy, sy + oy], color=color, lw=0.65, alpha=0.7, clip_on=False)
        ax.plot([ex, ex + ox], [ey, ey + oy], color=color, lw=0.65, alpha=0.7, clip_on=False)
    dx = ex - sx
    dy = ey - sy
    length = math.hypot(dx, dy) or 1.0
    tick = max(length * 0.025, 0.25)
    nx = -dy / length * tick
    ny = dx / length * tick
    for tx, ty in [(sx + ox, sy + oy), (ex + ox, ey + oy)]:
        ax.plot([tx - nx, tx + nx], [ty - ny, ty + ny], color=color, lw=1.05, alpha=0.95, clip_on=False)
    text_gap = max(min(length * 0.035, 0.65), 0.28)
    text_x = (sx + ex) / 2 + ox
    text_y = (sy + ey) / 2 + oy
    if abs(dx) >= abs(dy):
        text_y += (1 if oy >= 0 else -1) * text_gap
    else:
        text_x += (1 if ox >= 0 else -1) * text_gap
    ax.text(
        text_x,
        text_y,
        text,
        color=color,
        fontsize=12,
        rotation=rotation,
        ha="center",
        va="center",
        bbox=dict(facecolor="white", edgecolor="none", pad=0.4, alpha=0.92),
        clip_on=False,
        zorder=7,
    )


def _leader_label(ax, xy, text_xy, text: str) -> None:
    """绘制半径和局部尺寸的紫色引线标注。"""
    ax.annotate(
        text,
        xy=xy,
        xytext=text_xy,
        color="#ff00ff",
        fontsize=12,
        ha="center",
        va="center",
        arrowprops=dict(arrowstyle="-|>", color="#ff00ff", lw=1.05, shrinkA=0, shrinkB=0, mutation_scale=13),
        bbox=dict(facecolor="white", edgecolor="none", pad=0.25, alpha=0.92),
    )


def _draw_goal_area_dimension_labels(ax, params: FieldParams) -> None:
    """给球门区/小禁区做尺寸标注，七人制短框用引线避免文字重叠。"""
    if not params.has_goal_area or params.goal_area_depth <= 0 or params.goal_area_width <= 0:
        return

    if is_five_a_side(params.field_type):
        metrics = _small_pitch_metrics(params)
        goal_depth = metrics["goal_area_depth"]
        goal_width = metrics["goal_area_width"]
        gy1 = (params.width - goal_width) / 2
        _dim_line(
            ax,
            (0, params.width / 2 + goal_width / 2),
            (-goal_depth, params.width / 2 + goal_width / 2),
            _fmt_dim(goal_depth),
            offset=(-params.length * 0.035, params.width * 0.135),
        )
        _dim_line(
            ax,
            (-goal_depth, gy1),
            (-goal_depth, gy1 + goal_width),
            _fmt_dim(goal_width),
            offset=(-params.length * 0.065, 0),
            rotation=90,
        )
        return

    gy1 = (params.width - params.goal_area_width) / 2
    if _use_clean_dimension_template(params):
        horizontal_y = gy1 + params.goal_area_width
        _dim_line(
            ax,
            (0, horizontal_y),
            (params.goal_area_depth, horizontal_y),
            _fmt_dim(params.goal_area_depth),
            offset=(0, params.width * 0.09),
        )
        return

    is_compact_goal_area = params.goal_area_width < params.penalty_area_width * 0.45 if params.penalty_area_width else False
    if is_compact_goal_area:
        horizontal_y = gy1
        _dim_line(
            ax,
            (0, horizontal_y),
            (params.goal_area_depth, horizontal_y),
            _fmt_dim(params.goal_area_depth),
            offset=(0, -params.width * 0.075),
        )
        return

    _dim_line(ax, (0, gy1), (params.goal_area_depth, gy1), _fmt_dim(params.goal_area_depth), offset=(0, -params.width * 0.035))
    _dim_line(
        ax,
        (params.goal_area_depth, gy1),
        (params.goal_area_depth, gy1 + params.goal_area_width),
        _fmt_dim(params.goal_area_width),
        offset=(params.length * 0.03, 0),
        rotation=90,
    )


def _color_rect(params: FieldParams) -> tuple[float, float, float, float]:
    """返回需要铺色的区域，包含缓冲区。"""
    if not params.include_buffer:
        return 0.0, 0.0, params.length, params.width
    return (
        -params.buffer_left_right,
        -params.buffer_top_bottom,
        params.length + params.buffer_left_right * 2,
        params.width + params.buffer_top_bottom * 2,
    )


def _centered_stripe_segments(params: FieldParams) -> list[tuple[float, float, str]]:
    """以中线为浅色中心，向两侧镜像生成深浅条纹。"""
    start_x, _start_y, length, _width = _color_rect(params)
    end_x = start_x + length
    center = params.length / 2
    stripe_w = max(params.stripe_width, 0.1)
    cuts = {start_x, end_x}
    left = center - stripe_w / 2
    right = center + stripe_w / 2
    while left > start_x:
        cuts.add(left)
        left -= stripe_w
    while right < end_x:
        cuts.add(right)
        right += stripe_w
    segments = []
    sorted_cuts = sorted(cuts)
    for x1, x2 in zip(sorted_cuts, sorted_cuts[1:]):
        mid = (x1 + x2) / 2
        dist = abs(mid - center)
        band = 0 if dist <= stripe_w / 2 else math.floor((dist - stripe_w / 2) / stripe_w) + 1
        color = "#56b947" if band % 2 == 0 else "#116530"
        segments.append((x1, x2, color))
    if len(segments) > 1 and params.edge_stripe_mode == "自动合并窄边":
        # 边上只剩很窄一条时才并入相邻色；剩得较多时仍按深浅交替。
        edge_threshold = min(stripe_w * 0.30, 1.0)
        first_x1, first_x2, _first_color = segments[0]
        if first_x2 - first_x1 < edge_threshold:
            segments[0] = (first_x1, first_x2, segments[1][2])
        last_x1, last_x2, _last_color = segments[-1]
        if last_x2 - last_x1 < edge_threshold:
            segments[-1] = (last_x1, last_x2, segments[-2][2])
    return segments


def _is_two_meter_dual_roll(params: FieldParams) -> bool:
    """2m 深浅双色草卷：整卷按 A 编号，边缘单色补条按 B1。"""
    return params.stripe_width <= 2.01


def _production_width_for_edge(actual_width: float, params: FieldParams) -> float:
    """边上不足整卷的补卷，施工图面积按实际窄宽计算。"""
    if actual_width <= 0.05:
        return 0
    return actual_width


def _roll_plan_items(params: FieldParams) -> list[dict]:
    """按模板生成草卷编号：浅色 A，深色 B，白草 AW。"""
    start_x, _start_y, total_len, total_wid = _color_rect(params)
    if _is_two_meter_dual_roll(params):
        roll_w = max(params.roll_width, 0.1)
        full_count = max(math.floor(total_len / roll_w), 1)
        edge_w = max((total_len - full_count * roll_w) / 2, 0)
        items = []
        if edge_w > 0.05:
            production_w = _production_width_for_edge(edge_w, params)
            items.append(
                {
                    "code": "B1",
                    "color": "单色补条",
                    "length": total_wid,
                    "width": edge_w,
                    "area": total_wid * edge_w,
                    "production_width": production_w,
                    "production_area": total_wid * production_w,
                    "x1": start_x,
                    "x2": start_x + edge_w,
                    "fill": "#56b947",
                }
            )
        for index in range(full_count):
            x1 = start_x + edge_w + index * roll_w
            x2 = min(x1 + roll_w, start_x + total_len)
            if x2 - x1 <= 0.05:
                continue
            items.append(
                {
                    "code": f"A{index + 1}",
                    "color": "深浅双色",
                    "length": total_wid,
                    "width": x2 - x1,
                    "area": total_wid * (x2 - x1),
                    "production_width": x2 - x1,
                    "production_area": total_wid * (x2 - x1),
                    "x1": x1,
                    "x2": x2,
                    "fill": "#2f9e44",
                }
            )
        if edge_w > 0.05:
            production_w = _production_width_for_edge(edge_w, params)
            items.append(
                {
                    "code": "B1",
                    "color": "单色补条",
                    "length": total_wid,
                    "width": edge_w,
                    "area": total_wid * edge_w,
                    "production_width": production_w,
                    "production_area": total_wid * production_w,
                    "x1": start_x + total_len - edge_w,
                    "x2": start_x + total_len,
                    "fill": "#56b947",
                }
            )
        return items

    counters = {"#56b947": 0, "#116530": 0}
    prefixes = {"#56b947": "A", "#116530": "B"}
    names = {"#56b947": "浅色", "#116530": "深色"}
    items = []
    for x1, x2, color in _centered_stripe_segments(params):
        width = max(x2 - x1, 0)
        if width <= 0.05:
            continue
        counters[color] = counters.get(color, 0) + 1
        code = f"{prefixes.get(color, 'C')}{counters[color]}"
        is_edge_piece = x1 <= start_x + 0.05 or x2 >= start_x + total_len - 0.05
        production_w = _production_width_for_edge(width, params) if is_edge_piece and width < 4.0 else width
        items.append(
            {
                "code": code,
                "color": names.get(color, "草坪"),
                "length": total_wid,
                "width": width,
                "area": total_wid * width,
                "production_width": production_w,
                "production_area": total_wid * production_w,
                "x1": x1,
                "x2": x2,
                "fill": color,
            }
        )
    return items


def _range_codes(codes: list[str]) -> str:
    """把 A1,A2,A3 压缩成 A1-A3；不连续时用顿号连接。"""
    if not codes:
        return ""
    codes = list(dict.fromkeys(codes))
    prefix = "".join(ch for ch in codes[0] if not ch.isdigit())
    nums = [int("".join(ch for ch in code if ch.isdigit()) or "0") for code in codes]
    if all(code.startswith(prefix) for code in codes) and nums == list(range(nums[0], nums[-1] + 1)):
        return f"{codes[0]}-{codes[-1]}" if len(codes) > 1 else codes[0]
    return "、".join(codes)


def _roll_plan_rows(params: FieldParams, line_area: float, seam_length: float, glue_kg: float) -> list[list[str]]:
    """按模板生成施工图左下角生产明细表。"""
    items = _roll_plan_items(params)
    green_production_area = sum(item.get("production_area", item["area"]) for item in items)
    actual_production_area = green_production_area + int(line_area)
    rows = [["序号", "颜色", "规格", "卷数", "单位", "数量", "编号"]]
    seq = 1
    grouped: dict[tuple[str, float, float], list[dict]] = {}
    for item in items:
        key = (item["color"], round(item["length"], 2), round(item.get("production_width", item["width"]), 2))
        grouped.setdefault(key, []).append(item)
    for (color, length, width), group_items in grouped.items():
        codes = [item["code"] for item in group_items]
        rows.append(
            [
                str(seq),
                color,
                f"{length:g}*{width:g}m",
                str(len(group_items)),
                "㎡",
                f"{sum(item.get('production_area', item['area']) for item in group_items):.2f}",
                _range_codes(codes),
            ]
        )
        seq += 1
    white_area = int(line_area)
    white_roll_width = 2.0
    white_roll_length = white_area / white_roll_width if white_area > 0 else 0
    rows.append([str(seq), "白草", f"{white_roll_length:g}*{white_roll_width:g}m", "1", "㎡", str(white_area), "AW1"])
    seq += 1
    glue_buckets = glue_bucket_count(total_area(params))
    rows.append([str(seq), "胶水", "", "", "桶", str(glue_buckets), ""])
    seq += 1
    rows.append([str(seq), "接缝布", "", "", "米", str(round_to_nearest_hundred(seam_length)), ""])
    seq += 1
    rows.append([str(seq), "实际生产面积", "", "", "㎡", f"{actual_production_area:.2f}", "绿草+白草"])
    return rows


def _apply_color_scheme(ax, params: FieldParams) -> None:
    """按分色方案铺底色。"""
    start_x, start_y, length, width = _color_rect(params)
    if params.color_scheme == "深浅绿条纹":
        for x1, x2, color in _centered_stripe_segments(params):
            ax.add_patch(Rectangle((x1, start_y), x2 - x1, width, facecolor=color, edgecolor="none"))
    elif params.color_scheme == "中间深绿，两侧浅绿":
        ax.add_patch(Rectangle((start_x, start_y), length, width, facecolor="#56b947", edgecolor="none"))
        ax.add_patch(Rectangle((start_x, start_y + width * 0.25), length, width * 0.5, facecolor="#116530", edgecolor="none"))
    elif params.color_scheme == "外围深绿，内场浅绿":
        ax.add_patch(Rectangle((start_x, start_y), length, width, facecolor="#116530", edgecolor="none"))
        inset = min(length, width) * 0.08
        ax.add_patch(Rectangle((start_x + inset, start_y + inset), length - inset * 2, width - inset * 2, facecolor="#56b947", edgecolor="none"))
    else:
        ax.add_patch(Rectangle((start_x, start_y), length, width, facecolor=_color(params.main_color), edgecolor="none"))


def _draw_clean_template_spot_label(ax, params: FieldParams) -> None:
    """点球点按模板用数字尺寸线表达，避免中文说明挤在禁区里。"""
    spot_dist = penalty_mark_distance(params.field_type, params.length, params.penalty_area_depth)
    if not spot_dist:
        return
    label_y = params.width / 2 - params.goal_area_width / 2
    _dim_line(
        ax,
        (0, label_y),
        (spot_dist, label_y),
        _fmt_dim(spot_dist),
        offset=(0, -params.width * 0.07),
    )


def _draw_clean_template_right_labels(ax, params: FieldParams) -> None:
    """按模板把宽度类尺寸放到右侧，避免左侧标注过密。"""
    if not params.has_penalty_area:
        return
    px = params.length - params.penalty_area_depth
    py1 = (params.width - params.penalty_area_width) / 2
    py2 = (params.width + params.penalty_area_width) / 2
    _dim_line(ax, (px, py1), (px, py2), _fmt_dim(params.penalty_area_width), offset=(-params.length * 0.06, 0), rotation=90)

    if params.has_goal_area and params.goal_area_width > 0:
        gx = params.length - params.goal_area_depth
        gy1 = (params.width - params.goal_area_width) / 2
        gy2 = (params.width + params.goal_area_width) / 2
        _dim_line(ax, (gx, gy1), (gx, gy2), _fmt_dim(params.goal_area_width), offset=(-params.length * 0.085, 0), rotation=90)


def _should_label_penalty_arc(params: FieldParams) -> bool:
    """七人制和十一人制需要在尺寸图上明确标出罚球弧半径。"""
    return "7人制" in params.field_type or "11人制" in params.field_type


def _draw_penalty_arc_radius_label(ax, params: FieldParams) -> None:
    """给左侧罚球弧增加半径箭头标注，位置避开禁区尺寸线。"""
    if not params.has_penalty_area or _is_small_pitch(params) or not _should_label_penalty_arc(params):
        return
    arc_r = penalty_arc_radius(params.field_type, params.penalty_area_depth)
    spot_dist = penalty_mark_distance(params.field_type, params.length, params.penalty_area_depth)
    if not arc_r or not spot_dist:
        return
    anchor_x = params.penalty_area_depth + arc_r * 0.25
    anchor_y = params.width / 2 - arc_r * 0.42
    text_x = params.penalty_area_depth + arc_r * 0.95
    text_y = params.width / 2 - arc_r * 0.95
    _leader_label(ax, (anchor_x, anchor_y), (text_x, text_y), f"R{arc_r:.2f}")


def _draw_corner_arc_radius_label(ax, params: FieldParams) -> None:
    """在尺寸图上标出角球弧半径，四角同半径，只标一处避免图面杂乱。"""
    if not params.has_corner_arc:
        return
    corner_r = corner_arc_radius(params.field_type, params.length, params.width)
    if corner_r <= 0:
        return
    anchor = (corner_r * 0.70, params.width - corner_r * 0.30)
    text_x = max(corner_r * 2.25, params.length * 0.055)
    text_y = params.width - max(corner_r * 1.55, params.width * 0.055)
    _leader_label(ax, anchor, (text_x, text_y), f"R{corner_r:.2f}")


def draw_dimension_image(params: FieldParams) -> str:
    """生成参考 PDF 风格的尺寸图。"""
    fig = _new_sheet("尺寸图")
    ax = _field_axis(fig, params)
    _draw_buffer(ax, params)
    _draw_pitch_lines(ax, params, color="#333333", lw=1.0)

    outer_len = params.length + (params.buffer_left_right * 2 if params.include_buffer else 0)
    outer_wid = params.width + (params.buffer_top_bottom * 2 if params.include_buffer else 0)
    _dim_line(ax, (0, params.width), (params.length, params.width), _fmt_dim(params.length), offset=(0, params.width * 0.15))
    if not _use_clean_dimension_template(params):
        _dim_line(ax, (0, 0), (params.length, 0), _fmt_dim(params.length), offset=(0, -params.width * 0.08))
    _dim_line(ax, (params.length, 0), (params.length, params.width), _fmt_dim(params.width), offset=(params.length * 0.07, 0), rotation=90)
    if params.include_buffer:
        _dim_line(ax, (-params.buffer_left_right, -params.buffer_top_bottom), (params.length + params.buffer_left_right, -params.buffer_top_bottom), _fmt_dim(outer_len), offset=(0, -params.width * 0.12))
        if _use_clean_dimension_template(params):
            _dim_line(ax, (params.length + params.buffer_left_right, -params.buffer_top_bottom), (params.length + params.buffer_left_right, params.width + params.buffer_top_bottom), _fmt_dim(outer_wid), offset=(params.length * 0.08, 0), rotation=90)
        else:
            _dim_line(ax, (-params.buffer_left_right, -params.buffer_top_bottom), (-params.buffer_left_right, params.width + params.buffer_top_bottom), _fmt_dim(outer_wid), offset=(-params.length * 0.08, 0), rotation=90)
        if params.buffer_left_right > 0 and not _use_clean_dimension_template(params):
            _dim_line(ax, (-params.buffer_left_right, params.width), (0, params.width), _fmt_dim(params.buffer_left_right), offset=(0, params.width * 0.075))
            _dim_line(ax, (params.length, params.width), (params.length + params.buffer_left_right, params.width), _fmt_dim(params.buffer_left_right), offset=(0, params.width * 0.075))
        if params.buffer_top_bottom > 0 and not _use_clean_dimension_template(params):
            _dim_line(ax, (params.length, params.width), (params.length, params.width + params.buffer_top_bottom), _fmt_dim(params.buffer_top_bottom), offset=(params.length * 0.035, 0), rotation=90)
            _dim_line(ax, (params.length, -params.buffer_top_bottom), (params.length, 0), _fmt_dim(params.buffer_top_bottom), offset=(params.length * 0.035, 0), rotation=90)
    center_r = _center_circle_radius(params)
    _leader_label(
        ax,
        (params.length / 2 + center_r * 0.7, params.width / 2 + center_r * 0.7),
        (params.length * 0.58, params.width * 0.62),
        f"R{center_r:.2f}",
    )
    if params.has_penalty_area:
        if _is_small_pitch(params):
            penalty_r = _small_pitch_metrics(params)["penalty_arc_radius"]
            _leader_label(ax, (penalty_r * 0.72, params.width / 2 + penalty_r * 0.72), (penalty_r * 1.25, params.width * 0.70), f"R{penalty_r:.2f}")
            if not _use_clean_dimension_template(params):
                _leader_label(ax, (params.length - penalty_r * 0.72, params.width / 2 + penalty_r * 0.72), (params.length - penalty_r * 1.25, params.width * 0.70), f"R{penalty_r:.2f}")
        else:
            if _use_clean_dimension_template(params):
                penalty_top = (params.width + params.penalty_area_width) / 2
                _dim_line(ax, (0, penalty_top), (params.penalty_area_depth, penalty_top), _fmt_dim(params.penalty_area_depth), offset=(0, params.width * 0.045))
                _draw_clean_template_right_labels(ax, params)
            else:
                _dim_line(ax, (0, params.width * 0.16), (params.penalty_area_depth, params.width * 0.16), _fmt_dim(params.penalty_area_depth), offset=(0, -params.width * 0.045))
                _dim_line(ax, (0, (params.width - params.penalty_area_width) / 2), (0, (params.width + params.penalty_area_width) / 2), _fmt_dim(params.penalty_area_width), offset=(-params.length * 0.035, 0), rotation=90)
            arc_r = penalty_arc_radius(params.field_type, params.penalty_area_depth)
            spot_dist_for_arc = penalty_mark_distance(params.field_type, params.length, params.penalty_area_depth)
            if arc_r and spot_dist_for_arc and not _use_clean_dimension_template(params):
                _leader_label(
                    ax,
                    (params.penalty_area_depth + arc_r * 0.45, params.width / 2 + arc_r * 0.55),
                    (params.penalty_area_depth + arc_r * 1.35, params.width / 2 + arc_r * 1.10),
                    f"R{arc_r:.2f}",
                )
        spot_dist = penalty_mark_distance(params.field_type, params.length, params.penalty_area_depth)
        if spot_dist and not _use_clean_dimension_template(params):
            _leader_label(ax, (spot_dist, params.width / 2), (spot_dist + params.length * 0.06, params.width * 0.54), f"点球点{spot_dist:.2f}m")
    _draw_goal_area_dimension_labels(ax, params)
    if _use_clean_dimension_template(params):
        _draw_clean_template_spot_label(ax, params)
        _draw_penalty_arc_radius_label(ax, params)
        _draw_corner_arc_radius_label(ax, params)
    if not _use_clean_dimension_template(params):
        _leader_label(ax, (params.length * 0.08, params.width), (params.length * 0.18, params.width * 1.02), f"线宽{params.line_width:g}m")
    if params.has_corner_arc and not _use_clean_dimension_template(params):
        corner_r = corner_arc_radius(params.field_type, params.length, params.width)
        _leader_label(ax, (corner_r * 0.7, params.width - corner_r * 0.3), (corner_r * 2.2, params.width - corner_r * 1.5), f"R{corner_r:.2f}")
    _notes(fig, params)
    _title_block(fig, params)
    path = unique_path(IMAGE_DIR, f"{safe_filename(params.project_name)}_尺寸图.png")
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def draw_effect_image(params: FieldParams) -> str:
    """生成参考 PDF 风格的彩色效果图。"""
    fig = _new_sheet("效果图")
    ax = _field_axis(fig, params)
    _apply_color_scheme(ax, params)
    _draw_buffer(ax, params, edgecolor="#ffffff")
    _draw_pitch_lines(ax, params, color="#ffffff", lw=1.15)
    ax.add_patch(Rectangle((0, 0), params.length, params.width, fill=False, edgecolor="#ffffff", linewidth=0.8))
    _notes(fig, params)
    _title_block(fig, params)
    path = unique_path(IMAGE_DIR, f"{safe_filename(params.project_name)}_效果图.png")
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def _draw_material_table(fig, params: FieldParams) -> None:
    """绘制施工页左下角生产明细表。"""
    line_geom = build_line_geometry(params)
    field = box(0, 0, params.length, params.width)
    raw_line_area = line_geom.intersection(field).area if line_geom else 0
    line_area = white_grass_area(raw_line_area)
    total_sqm = total_area(params)
    total_len = params.length + (params.buffer_left_right * 2 if params.include_buffer else 0)
    total_wid = params.width + (params.buffer_top_bottom * 2 if params.include_buffer else 0)
    roll_seams = max(math.ceil(total_len / max(params.roll_width, 0.1)) - 1, 0) * total_wid
    line_seams = line_geom.length if line_geom else 0
    seam_length = (roll_seams + line_seams) * (1 + params.seam_tape_extra_rate / 100)
    rows = _roll_plan_rows(params, line_area, seam_length, total_sqm * params.glue_per_sqm)
    green_production_area = sum(item.get("production_area", item["area"]) for item in _roll_plan_items(params))
    actual_production_area = green_production_area + line_area
    ax = fig.add_axes([0.10, 0.085, 0.44, 0.18])
    ax.axis("off")
    table = ax.table(cellText=rows, cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.25)
    ax.text(0.5, 1.02, "草坪生产方案明细表", color="#2f9e44", fontsize=10, ha="center", va="bottom", transform=ax.transAxes)
    ax.text(
        0.0,
        -0.18,
        f"实际生产面积：{actual_production_area:.2f}㎡（绿草{green_production_area:.2f}㎡ + 白草{line_area}㎡）",
        color="#333333",
        fontsize=9,
        ha="left",
        va="top",
        transform=ax.transAxes,
        clip_on=False,
    )


def draw_construction_image(params: FieldParams) -> str:
    """生成参考 PDF 风格的施工图。"""
    fig = _new_sheet("施工图")
    ax = _field_axis(fig, params, y0=0.31, height=0.50)
    total_x0 = -params.buffer_left_right if params.include_buffer else 0
    total_y0 = -params.buffer_top_bottom if params.include_buffer else 0
    total_len = params.length + (params.buffer_left_right * 2 if params.include_buffer else 0)
    total_wid = params.width + (params.buffer_top_bottom * 2 if params.include_buffer else 0)

    ax.add_patch(Rectangle((total_x0, total_y0), total_len, total_wid, facecolor="white", edgecolor="#333333", linewidth=0.9))
    ax.add_patch(Rectangle((0, 0), params.length, params.width, facecolor="white", edgecolor="#333333", linewidth=0.8))

    # 施工模板：绿色线绑定到深浅条纹真实边界，和中线居中的分色规则保持一致。
    stripe_edges = {total_x0, total_x0 + total_len}
    for x1, x2, _color_value in _centered_stripe_segments(params):
        stripe_edges.add(x1)
        stripe_edges.add(x2)
    for guide_x in sorted(stripe_edges):
        if total_x0 - 0.001 <= guide_x <= total_x0 + total_len + 0.001:
            ax.plot([guide_x, guide_x], [total_y0, total_y0 + total_wid], color="#26a269", lw=0.55, alpha=0.95)

    band_h = params.width * 0.24
    band_y = (params.width - band_h) / 2
    for x1, x2, color in _centered_stripe_segments(params):
        ax.add_patch(Rectangle((x1, band_y), x2 - x1, band_h, facecolor=color, edgecolor="none", alpha=0.96))
    for item in _roll_plan_items(params):
        width = item["x2"] - item["x1"]
        label_x = (item["x1"] + item["x2"]) / 2
        if _is_two_meter_dual_roll(params):
            is_narrow = item["code"].startswith("B") or width < params.roll_width * 0.5
            fontsize = 30 if not is_narrow else 16
            label_color = "#ff00ff" if is_narrow or item["code"].startswith("B") else "white"
            if not is_narrow and item["code"].startswith("A"):
                label_x += min(width * 0.08, 0.35)
        else:
            is_narrow = width < params.roll_width * 0.5
            if "11人制" in params.field_type:
                fontsize = 10 if width >= params.roll_width * 0.75 else 8
            elif "7人制" in params.field_type:
                fontsize = 14 if width >= params.roll_width * 0.75 else 8
            else:
                fontsize = 16 if width >= params.roll_width * 0.75 else 9
            label_color = "#ff00ff" if is_narrow or item["code"].startswith("B") else "white"
        label_y = band_y + band_h * 1.18 if is_narrow else params.width / 2
        ax.text(
            label_x,
            label_y,
            item["code"],
            color=label_color,
            fontsize=fontsize,
            ha="center",
            va="center",
            weight="normal" if "11人制" in params.field_type else "bold",
            clip_on=False,
        )

    _draw_pitch_lines(ax, params, color="#333333", lw=0.9, center_mark_color=None)

    _draw_material_table(fig, params)
    _title_block(fig, params)
    path = unique_path(IMAGE_DIR, f"{safe_filename(params.project_name)}_施工图.png")
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def generate_all_images(params: FieldParams) -> dict:
    """一次生成三张完整图纸页。"""
    return {
        "尺寸图": draw_dimension_image(params),
        "效果图": draw_effect_image(params),
        "施工图": draw_construction_image(params),
    }
