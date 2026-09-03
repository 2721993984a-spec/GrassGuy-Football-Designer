from __future__ import annotations

import pandas as pd

from .calculator import FieldParams
from .utils import EXCEL_DIR, safe_filename, unique_path


def export_excel(params: FieldParams, results: dict) -> str:
    """导出 Excel 用量表。"""
    path = unique_path(EXCEL_DIR, f"{safe_filename(params.project_name)}_草坪用量表.xlsx")
    params_df = pd.DataFrame(
        [
            ["项目名称", params.project_name],
            ["客户名称", params.customer_name],
            ["场地类型", params.field_type],
            ["场地长度m", params.length],
            ["场地宽度m", params.width],
            ["总长度m", results["总长度"]],
            ["总宽度m", results["总宽度"]],
            ["场地总面积㎡", results["场地总面积"]],
            ["白线面积㎡", results["白线面积"]],
            ["颜色方案", params.color_scheme],
        ],
        columns=["参数", "值"],
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        params_df.to_excel(writer, index=False, sheet_name="项目参数")
        results["草坪用量"].to_excel(writer, index=False, sheet_name="草坪用量")
        results["辅材用量"].to_excel(writer, index=False, sheet_name="辅材用量")

        for sheet in writer.book.worksheets:
            for column_cells in sheet.columns:
                max_len = max(len(str(cell.value or "")) for cell in column_cells)
                sheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_len + 3, 12), 36)

    return str(path)
