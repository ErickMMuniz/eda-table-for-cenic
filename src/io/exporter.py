"""Excel report exporter for EDA dataset results."""
import logging
from typing import List, Optional
import pandas as pd

from src.eda.pipeline import TableWithProcessDict

logger = logging.getLogger(__name__)


class ExcelReportExporter:
    """Exports processed table metadata and field metrics to an Excel workbook."""

    def __init__(self, output_file: str):
        self.output_file = output_file

    def export(
        self,
        tables_with_process: List[TableWithProcessDict],
        valid_table_names: Optional[List[str]] = None,
    ) -> str:
        """Writes table statistics and variable metadata to Excel with a summary sheet.

        Args:
            tables_with_process: Processed table objects containing metadata & metrics.
            valid_table_names: Optional filter list of table names.

        Returns:
            str: File path of the written Excel report.
        """
        merge_table_sum = []
        for item in tables_with_process:
            df_sum = item.metadata.get("table_page_table_sum")
            if df_sum is not None and not df_sum.empty:
                df_sum_copy = df_sum.copy()
                df_sum_copy["Tabla"] = item.table.name
                if df_sum_copy.get("Accesibilidad", [False])[0] is True:
                    df_col = item.metadata.get("table_page_columns_info")
                    if isinstance(df_col, pd.DataFrame) and "Valores faltantes" in df_col.columns:
                        sum_missing = df_col["Valores faltantes"].sum()
                        num_rows = item.table.stats.get("num_rows", 0) or 0
                        num_cols = item.table.stats.get("num_columns", 0) or 0
                        total_cells = num_rows * num_cols
                        if total_cells > 0:
                            df_sum_copy["Porcentaje de valores faltantes"] = round(sum_missing / float(total_cells), 4)
                merge_table_sum.append(df_sum_copy)

        if merge_table_sum:
            df_summary_all = pd.concat(merge_table_sum, ignore_index=True)
        else:
            df_summary_all = pd.DataFrame()

        if valid_table_names and not df_summary_all.empty:
            is_valid_fn = lambda x: any(name.lower() in str(x).lower() for name in valid_table_names)
            df_summary_all = df_summary_all[df_summary_all["Tabla"].apply(is_valid_fn)]

        if not df_summary_all.empty:
            df_summary_all.reset_index(drop=True, inplace=True)
            df_summary_all.index += 1
            df_summary_all.insert(0, "ID", df_summary_all.index)

            visual_cols = [
                c
                for c in [
                    "ID",
                    "Accesibilidad",
                    "Número de columnas",
                    "Número de filas",
                    "Porcentaje de valores faltantes",
                    "Fecha de creación",
                    "Tabla",
                ]
                if c in df_summary_all.columns
            ]
            df_summary_all = df_summary_all[visual_cols]

        with pd.ExcelWriter(self.output_file, engine="xlsxwriter") as writer:
            df_summary_all.to_excel(writer, sheet_name="Resumen", index=False)

            if valid_table_names:
                present_tables = df_summary_all["Tabla"].tolist() if not df_summary_all.empty else []
                missing_tables = [
                    name
                    for name in valid_table_names
                    if not any(name.lower() in str(pt).lower() for pt in present_tables)
                ]
                if missing_tables:
                    df_missing = pd.DataFrame({"Tabla": missing_tables})
                    start_row = len(df_summary_all) + 3 if not df_summary_all.empty else 3
                    df_missing.to_excel(
                        writer,
                        sheet_name="Resumen",
                        index=False,
                        startrow=start_row,
                        header=["Tablas faltantes en dataset"],
                    )

            for idx, item in enumerate(tables_with_process, start=1):
                sheet_name = f"Tabla {idx}"
                pd.Series([item.table.table_id]).to_excel(
                    writer, sheet_name=sheet_name, index=False, header=["Table Reference"], startrow=0
                )

                start_row_sum = 3
                pd.Series(["Resumen de la tabla"]).to_excel(
                    writer, sheet_name=sheet_name, index=False, header=False, startrow=start_row_sum
                )

                df_sum = item.metadata.get("table_page_table_sum")
                if isinstance(df_sum, pd.DataFrame):
                    df_sum.to_excel(writer, sheet_name=sheet_name, startrow=start_row_sum + 1)
                else:
                    pd.Series([str(df_sum)]).to_excel(
                        writer, sheet_name=sheet_name, index=False, header=False, startrow=start_row_sum + 1
                    )

                offset = len(df_sum) + 6 if isinstance(df_sum, pd.DataFrame) else 6
                pd.Series(["Descripción de las variables"]).to_excel(
                    writer, sheet_name=sheet_name, index=False, header=False, startrow=offset
                )

                df_col = item.metadata.get("table_page_columns_info")
                if isinstance(df_col, pd.DataFrame):
                    df_col.to_excel(writer, sheet_name=sheet_name, startrow=offset + 1)

                if item.table.error:
                    err_offset = (
                        offset + len(df_col) + 3 if isinstance(df_col, pd.DataFrame) else offset + 5
                    )
                    pd.Series(["Error de conexión"]).to_excel(
                        writer, sheet_name=sheet_name, index=False, header=False, startrow=err_offset
                    )
                    pd.Series([str(item.table.error)]).to_excel(
                        writer, sheet_name=sheet_name, index=False, header=False, startrow=err_offset + 1
                    )

        logger.info("Successfully generated EDA report at %s", self.output_file)
        return self.output_file
