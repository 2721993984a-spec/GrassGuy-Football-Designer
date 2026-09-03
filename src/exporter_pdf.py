from __future__ import annotations

from io import BytesIO
import logging

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .calculator import FieldParams
from .utils import FALLBACK_PDF_DIR, PDF_DIR, safe_filename, unique_path


def _draw_pdf(pdf, image_paths: dict) -> None:
    """把三张图纸写入一个三页横版 PDF。"""
    page_width, page_height = landscape(A4)
    margin = 0.25 * cm
    usable_width = page_width - margin * 2
    usable_height = page_height - margin * 2
    for key in ["尺寸图", "效果图", "施工图"]:
        image = ImageReader(image_paths[key])
        img_width, img_height = image.getSize()
        scale = min(usable_width / img_width, usable_height / img_height)
        draw_width = img_width * scale
        draw_height = img_height * scale
        x = (page_width - draw_width) / 2
        y = (page_height - draw_height) / 2
        pdf.drawImage(image, x, y, width=draw_width, height=draw_height, preserveAspectRatio=True, mask="auto")
        pdf.showPage()
    pdf.save()


def _write_pdf(path, image_paths: dict) -> None:
    """把图纸写入磁盘文件。"""
    pdf = canvas.Canvas(str(path), pagesize=landscape(A4))
    _draw_pdf(pdf, image_paths)


def build_pdf_bytes(image_paths: dict) -> bytes:
    """生成浏览器下载用 PDF 内容，不在服务器上落盘保存。"""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
    _draw_pdf(pdf, image_paths)
    return buffer.getvalue()


def export_pdf(params: FieldParams, results: dict, image_paths: dict) -> str:
    """优先导出到桌面图纸文件夹；失败时自动保存到项目内备用目录。"""
    filename = f"{safe_filename(params.project_name)}_人造草坪施工图.pdf"
    try:
        path = unique_path(PDF_DIR, filename)
        _write_pdf(path, image_paths)
        return str(path)
    except OSError as exc:
        logging.warning("保存到桌面 PDF 文件夹失败，改用项目内备用目录：%s", exc)
        path = unique_path(FALLBACK_PDF_DIR, filename)
        _write_pdf(path, image_paths)
    return str(path)
