from __future__ import annotations

import logging
import math
import os
import re
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "output"
IMAGE_DIR = OUTPUT_DIR / "images"
FALLBACK_PDF_DIR = BASE_DIR / "PDF图纸"
PDF_DIR = Path.home() / "Desktop" / "草皮哥足球场图纸PDF" if os.name == "nt" else FALLBACK_PDF_DIR
EXCEL_DIR = OUTPUT_DIR / "excel"
LOG_DIR = BASE_DIR / "logs"


def ensure_dirs() -> None:
    """确保项目输出目录都存在。"""
    for path in [IMAGE_DIR, FALLBACK_PDF_DIR, EXCEL_DIR, LOG_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    try:
        PDF_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logging.warning("桌面 PDF 文件夹暂时不可写，将使用项目内备用目录：%s", exc)


def setup_logging() -> None:
    """初始化日志，错误会写入 logs/app.log。"""
    ensure_dirs()
    logging.basicConfig(
        filename=LOG_DIR / "app.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )


def safe_filename(name: str) -> str:
    """把项目名称转换成适合保存文件的名称。"""
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", name.strip())
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned or "未命名项目"


def unique_path(directory: Path, filename: str) -> Path:
    """如果文件已存在，自动追加时间戳，避免覆盖旧文件。"""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    if not path.exists():
        return path
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return directory / f"{path.stem}_{stamp}{path.suffix}"


def open_in_file_explorer(path: str | Path) -> bool:
    """在 Windows 文件管理器中打开导出文件所在文件夹，失败时只记录日志。"""
    if os.name != "nt":
        return False
    try:
        target = Path(path)
        folder = target if target.is_dir() else target.parent
        os.startfile(str(folder))
        return True
    except (OSError, AttributeError) as exc:
        logging.warning("自动打开导出文件夹失败：%s", exc)
        return False


def fmt(value: float, digits: int = 2) -> str:
    """统一格式化数字，方便页面和表格展示。"""
    return f"{value:.{digits}f}"


def round_to_nearest_hundred(value: float) -> int:
    """接缝布按模板习惯取整百，619m 显示为 600m。"""
    if value <= 0:
        return 0
    return int((value + 50) // 100 * 100)


def glue_bucket_count(area_sqm: float) -> int:
    """胶水按模板口径折算：约 700㎡ 使用 6 桶。"""
    if area_sqm <= 0:
        return 0
    return math.ceil(area_sqm * 6 / 700)
