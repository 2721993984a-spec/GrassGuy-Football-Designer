from __future__ import annotations

import hmac
import logging
import os
from datetime import datetime

import streamlit as st

from src.calculator import FieldParams, calculate_all
from src.drawing import generate_all_images
from src.exporter_pdf import build_pdf_bytes
from src.standards import five_a_side_template_metrics, is_five_a_side, recommended_template, rule_source_summary, validate_pitch_size
from src.templates import get_template, load_field_templates
from src.utils import setup_logging


DRAWING_STYLE_VERSION = "clean-dimension-template-v44-cloud-ready-pdf-prepared"


setup_logging()

st.set_page_config(
    page_title="草皮哥足球场智能设计方案平台",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="auto",
)


def inject_style() -> None:
    """统一页面样式，让内部工具界面更清爽。"""
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2.5rem;
            max-width: 1480px;
        }
        [data-testid="stSidebar"] {
            background: #f6f8f5;
            border-right: 1px solid #e2e8df;
        }
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #1f5130;
            letter-spacing: 0;
        }
        .gg-hero {
            border: 1px solid #dce7d9;
            border-radius: 8px;
            padding: 18px 22px;
            background: #fbfdf9;
            margin-bottom: 16px;
        }
        .gg-title {
            margin: 0;
            font-size: 30px;
            font-weight: 760;
            color: #173d26;
            letter-spacing: 0;
        }
        .gg-subtitle {
            margin: 6px 0 0 0;
            color: #5d6b60;
            font-size: 14px;
        }
        .gg-section {
            font-size: 18px;
            font-weight: 700;
            color: #173d26;
            margin: 18px 0 8px 0;
        }
        .gg-note {
            border-left: 4px solid #2f9e44;
            background: #f2faf0;
            padding: 10px 12px;
            color: #405047;
            font-size: 14px;
            margin: 8px 0 14px 0;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #dde7da;
            border-radius: 8px;
            padding: 12px 14px;
        }
        div[data-testid="stMetricValue"] {
            color: #173d26;
            font-size: 24px;
        }
        .stButton > button {
            border-radius: 8px;
            height: 44px;
            font-weight: 700;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid #e0e7dd;
            border-radius: 8px;
            overflow: hidden;
        }
        @media (max-width: 768px) {
            .block-container {
                padding-top: 0.8rem;
                padding-left: 0.8rem;
                padding-right: 0.8rem;
            }
            .gg-hero {
                padding: 14px 16px;
            }
            .gg-title {
                font-size: 24px;
                line-height: 1.25;
            }
            .gg-subtitle {
                font-size: 13px;
            }
            div[data-testid="stMetric"] {
                padding: 10px 12px;
            }
            div[data-testid="stMetricValue"] {
                font-size: 20px;
            }
            .stButton > button {
                height: 48px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def configured_password() -> str:
    """读取可选访问密码；未配置时保持免登录，方便本地调试。"""
    env_password = os.environ.get("GRASSGUY_APP_PASSWORD") or os.environ.get("APP_PASSWORD")
    if env_password:
        return env_password.strip()
    try:
        secret_password = st.secrets.get("GRASSGUY_APP_PASSWORD") or st.secrets.get("APP_PASSWORD")
    except Exception:
        secret_password = None
    return str(secret_password or "").strip()


def require_access_password() -> None:
    """上线分享时用一个简单密码挡住外部访问。"""
    password = configured_password()
    if not password or st.session_state.get("grassguy_authenticated"):
        return

    st.markdown(
        """
        <div class="gg-hero">
            <h1 class="gg-title">草皮哥足球场设计平台</h1>
            <p class="gg-subtitle">请输入公司内部访问密码</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    input_password = st.text_input("访问密码", type="password")
    if st.button("进入平台", type="primary", use_container_width=True):
        if hmac.compare_digest(input_password.strip(), password):
            st.session_state["grassguy_authenticated"] = True
            st.rerun()
        else:
            st.error("密码不正确")
    st.stop()


def result_value(results: dict, key: str, default: float = 0) -> float:
    """安全读取计算结果，避免界面因为单个字段缺失中断。"""
    return float(results.get(key, default) or default)


def pdf_download_name(params: FieldParams) -> str:
    """按项目名称、场地类型和日期生成下载文件名。"""
    from src.utils import safe_filename

    today = datetime.now().strftime("%Y%m%d")
    return f"{safe_filename(params.project_name)}_{safe_filename(params.field_type)}_{today}.pdf"


def build_params() -> FieldParams:
    """从侧边栏收集项目和球场参数。"""
    templates = load_field_templates()
    field_types = list(templates.keys())

    with st.sidebar:
        st.markdown("## 项目参数")
        project_name = st.text_input("项目名称", value="草皮哥足球场项目")
        customer_name = st.text_input("客户名称", value="客户")
        field_type = st.selectbox("场地类型", field_types)
        template = recommended_template(field_type, get_template(field_type))
        template_key = f"{field_type}_buffer_in_total_v1"

        st.markdown("## 场地尺寸")
        size_col1, size_col2 = st.columns(2)
        with size_col1:
            total_length = st.number_input("场地总长度 m", min_value=5.0, max_value=130.0, value=float(template["length"]), step=0.1, key=f"length_{template_key}")
        with size_col2:
            total_width = st.number_input("场地总宽度 m", min_value=5.0, max_value=90.0, value=float(template["width"]), step=0.1, key=f"width_{template_key}")

        include_buffer = st.checkbox("包含缓冲区", value=True)
        default_lr_buffer = float(template.get("buffer_left_right", 1.0))
        default_tb_buffer = float(template.get("buffer_top_bottom", 1.0))
        buffer_col1, buffer_col2 = st.columns(2)
        with buffer_col1:
            buffer_left_right = st.number_input(
                "左右缓冲区 m",
                min_value=0.0,
                max_value=20.0,
                value=default_lr_buffer,
                step=0.5,
                disabled=not include_buffer,
                key=f"buffer_lr_{template_key}",
            )
        with buffer_col2:
            buffer_top_bottom = st.number_input(
                "上下缓冲区 m",
                min_value=0.0,
                max_value=20.0,
                value=default_tb_buffer,
                step=0.5,
                disabled=not include_buffer,
                key=f"buffer_tb_{template_key}",
            )
        if not include_buffer:
            buffer_left_right = 0.0
            buffer_top_bottom = 0.0
        length = max(total_length - buffer_left_right * 2, 1.0)
        width = max(total_width - buffer_top_bottom * 2, 1.0)
        st.caption(f"比赛区自动换算：{length:.2f}m × {width:.2f}m；总尺寸包含缓冲区。")

        st.markdown("## 草坪排版")
        line_color = "白色"
        st.caption("球场标线固定为白色")
        if is_five_a_side(field_type):
            stripe_choice = st.radio(
                "深浅条纹宽度",
                ["2米深浅", "4米深浅"],
                index=0,
                horizontal=True,
            )
            stripe_width = 2.0 if stripe_choice == "2米深浅" else 4.0
        else:
            stripe_width = 4.0
            st.caption("7人制、11人制固定使用4米深浅分色排版。")
        edge_stripe_mode = st.radio(
            "边缘颜色处理",
            ["自动合并窄边", "始终深浅交替"],
            index=0,
            horizontal=True,
            key=f"edge_stripe_mode_{DRAWING_STYLE_VERSION}",
            help="边上剩料较窄时，可选择并入旁边颜色；如果想边上也一深一浅，选择始终深浅交替。",
        )

        st.markdown("## 球场标线")
        line_col1, line_col2 = st.columns(2)
        with line_col1:
            center_circle_radius = st.number_input(
                "中圈半径 m",
                min_value=0.0,
                max_value=15.0,
                value=float(template["center_circle_radius"]),
                step=0.1,
                key=f"center_radius_{template_key}",
            )
        with line_col2:
            line_width = st.number_input("线宽 m", min_value=0.05, max_value=0.30, value=float(template.get("line_width", 0.12)), step=0.01)

        mark_col1, mark_col2 = st.columns(2)
        with mark_col1:
            has_halfway_line = st.checkbox("中线", value=True)
            has_center_circle = st.checkbox("中圈", value=True)
            has_corner_arc = st.checkbox("角球弧", value=True)
        with mark_col2:
            has_penalty_area = st.checkbox("罚球区", value=True)
            has_goal_area = st.checkbox("球门区", value=True)

        with st.expander("标线细节尺寸"):
            penalty_area_depth = st.number_input("罚球区深度/半径 m", min_value=0.0, max_value=30.0, value=float(template["penalty_area_depth"]), step=0.1, key=f"penalty_depth_{template_key}")
            penalty_area_width = st.number_input("罚球区宽度 m", min_value=0.0, max_value=60.0, value=float(template["penalty_area_width"]), step=0.1, key=f"penalty_width_{template_key}")
            goal_area_depth = st.number_input("球门区深度 m", min_value=0.0, max_value=20.0, value=float(template["goal_area_depth"]), step=0.1, key=f"goal_depth_{template_key}")
            goal_area_width = st.number_input("球门区宽度 m", min_value=0.0, max_value=30.0, value=float(template["goal_area_width"]), step=0.1, key=f"goal_width_{template_key}")

        if is_five_a_side(field_type):
            five_metrics = five_a_side_template_metrics(length, width)
            if include_buffer and min(buffer_left_right, buffer_top_bottom) <= 1.05:
                five_metrics["goal_area_depth"] = min(five_metrics["goal_area_depth"], 0.8)
            center_circle_radius = five_metrics["center_circle_radius"]
            penalty_area_depth = five_metrics["penalty_area_depth"]
            penalty_area_width = five_metrics["penalty_area_width"]
            goal_area_depth = five_metrics["goal_area_depth"]
            goal_area_width = five_metrics["goal_area_width"]
            st.caption(
                f"五人制按模板比例套用：罚球弧R{penalty_area_depth:.2f}m，中圈R{center_circle_radius:.2f}m，点球点{five_metrics['penalty_mark_distance']:.2f}m，球门开口{goal_area_width:.2f}m。"
            )

        st.markdown("## 用量参数")
        qty_col1, qty_col2 = st.columns(2)
        with qty_col1:
            waste_rate = st.number_input("损耗率 %", min_value=0.0, max_value=30.0, value=5.0, step=0.5)
            glue_per_sqm = 0.0
            st.caption("胶水按模板自动计算：700㎡ = 6桶")
        with qty_col2:
            roll_width = st.number_input("草坪卷宽 m", min_value=1.0, max_value=5.0, value=4.0, step=0.5)
            seam_tape_extra_rate = st.number_input("接缝布余量 %", min_value=0.0, max_value=30.0, value=5.0, step=0.5)

    return FieldParams(
        project_name=project_name,
        customer_name=customer_name,
        field_type=field_type,
        length=length,
        width=width,
        include_buffer=include_buffer,
        buffer_left_right=buffer_left_right,
        buffer_top_bottom=buffer_top_bottom,
        main_color="绿色",
        line_color=line_color,
        center_circle_radius=center_circle_radius,
        line_width=line_width,
        has_penalty_area=has_penalty_area,
        has_goal_area=has_goal_area,
        has_halfway_line=has_halfway_line,
        has_center_circle=has_center_circle,
        has_corner_arc=has_corner_arc,
        color_scheme="深浅绿条纹",
        stripe_width=stripe_width,
        waste_rate=waste_rate,
        roll_width=roll_width,
        glue_per_sqm=glue_per_sqm,
        seam_tape_extra_rate=seam_tape_extra_rate,
        penalty_area_depth=penalty_area_depth,
        penalty_area_width=penalty_area_width,
        goal_area_depth=goal_area_depth,
        goal_area_width=goal_area_width,
        edge_stripe_mode=edge_stripe_mode,
    )


def show_project_summary(params: FieldParams, results: dict) -> None:
    """展示核心项目参数和面积指标。"""
    st.markdown(
        f"""
        <div class="gg-hero">
            <h1 class="gg-title">草皮哥足球场智能设计方案平台</h1>
            <p class="gg-subtitle">{params.project_name} · {params.field_type} · 深浅绿条纹 {params.stripe_width:g}m · {params.edge_stripe_mode} · {rule_source_summary(params.field_type)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("总长度", f"{result_value(results, '总长度'):.2f} m")
    metric_col2.metric("总宽度", f"{result_value(results, '总宽度'):.2f} m")
    metric_col3.metric("总面积", f"{result_value(results, '场地总面积'):.2f} ㎡")
    metric_col4.metric("白线面积", f"{result_value(results, '白线面积'):.0f} ㎡")

    info_col1, info_col2, info_col3 = st.columns(3)
    info_col1.write({"项目名称": params.project_name, "客户名称": params.customer_name})
    info_col2.write({"比赛区": f"{params.length:g}m × {params.width:g}m", "缓冲区": "包含" if params.include_buffer else "不包含"})
    info_col3.write({"条纹规则": "中线居中浅色，向两侧深浅交替", "卷宽": f"{params.roll_width:g}m"})
    size_warnings = validate_pitch_size(params.field_type, params.length, params.width)
    if size_warnings:
        for message in size_warnings:
            st.warning(message)
    else:
        st.success("当前比赛区长宽符合标准库范围。")


def show_results(results: dict) -> None:
    """展示草坪和辅材用量表。"""
    st.markdown('<div class="gg-section">用量统计</div>', unsafe_allow_html=True)
    tab_turf, tab_accessory = st.tabs(["草坪用量", "辅材用量"])
    with tab_turf:
        st.dataframe(results["草坪用量"], use_container_width=True, hide_index=True)
    with tab_accessory:
        st.dataframe(results["辅材用量"], use_container_width=True, hide_index=True)


def show_exports(params: FieldParams, results: dict) -> None:
    """先生成图纸预览，确认后再由浏览器下载 PDF。"""
    st.markdown('<div class="gg-section">图纸与导出</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="gg-note">施工图按模板输出：2米深浅双色按一卷两色标 A 编号，边缘剩余单色补条标 B1；4米深浅按浅色 A、深色 B 编号；白草用 AW。</div>',
        unsafe_allow_html=True,
    )

    if st.button("生成图纸预览", type="primary", use_container_width=True):
        with st.spinner("正在生成三张图纸预览..."):
            image_paths = generate_all_images(params)
        with st.spinner("正在准备 PDF 下载文件..."):
            pdf_bytes = build_pdf_bytes(image_paths)
        st.session_state["last_outputs"] = {
            "images": image_paths,
            "pdf_bytes": pdf_bytes,
            "pdf_name": pdf_download_name(params),
            "style_version": DRAWING_STYLE_VERSION,
        }
        st.success("图纸预览已生成。确认无误后，再点击下方下载 PDF。")

    outputs = st.session_state.get("last_outputs")
    if outputs and outputs.get("style_version") != DRAWING_STYLE_VERSION:
        st.session_state.pop("last_outputs", None)
        st.info("图纸规则已更新，请重新生成后查看最新图纸。")
        return
    if not outputs:
        st.info("请先生成图纸预览，确认无误后再下载 PDF。")
        return

    image_paths = outputs["images"]
    tab_dimension, tab_effect, tab_construction = st.tabs(["尺寸图", "效果图", "施工图"])
    with tab_dimension:
        st.image(image_paths["尺寸图"], use_container_width=True)
    with tab_effect:
        st.image(image_paths["效果图"], use_container_width=True)
    with tab_construction:
        st.image(image_paths["施工图"], use_container_width=True)

    pdf_bytes = outputs.get("pdf_bytes")
    if not pdf_bytes:
        with st.spinner("正在重新准备 PDF 下载文件..."):
            pdf_bytes = build_pdf_bytes(image_paths)
        outputs["pdf_bytes"] = pdf_bytes
        outputs["pdf_name"] = pdf_download_name(params)
    st.download_button(
        "下载 PDF 图纸",
        data=pdf_bytes,
        file_name=outputs.get("pdf_name", pdf_download_name(params)),
        mime="application/pdf",
        use_container_width=True,
        key=f"download_pdf_{DRAWING_STYLE_VERSION}",
    )
    st.caption(f"PDF 已准备好，大小约 {len(pdf_bytes) / 1024:.1f} KB；点击下载后由浏览器保存。")


inject_style()
require_access_password()
params = build_params()

try:
    results = calculate_all(params)
    show_project_summary(params, results)
    show_results(results)
    show_exports(params, results)
except Exception as exc:
    logging.exception("页面运行错误")
    st.error(f"程序出错：{exc}")
    st.info("错误详情已写入 logs/app.log。")
