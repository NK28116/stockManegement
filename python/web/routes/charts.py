import csv
import io
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Response

from python.utils.gcs_client import gcs

router = APIRouter(prefix="/api/charts", tags=["charts"])


# Map local category names to GCS paths
# charts/indicators -> plots
# charts/signals -> chartImg
CATEGORY_MAP = {
    "plots": "charts/indicators",
    "chartImg": "charts/signals",
}


@router.get("/list")
async def list_charts() -> List[Dict[str, Any]]:
    """List available charts grouped by company"""
    charts_map = {}

    # Helper to clean code
    def extract_info(filename: str):
        # Patterns:
        # 7203.T_Toyota_indicators.png (Plots)
        # 7203_T_Toyota.png (ChartImg)
        # 7203_Toyota.png (Fallback)
        parts = filename.split("_")
        code = parts[0].replace(".T", "").replace(".", "")  # 7203

        # Name extraction is best effort
        name = "Unknown"
        if len(parts) > 1:
            name = parts[1]
            if name == "T" and len(parts) > 2:  # Handle 7203_T_Name
                name = parts[2]

        # Remove extension from name if picked up
        name = name.replace(".png", "").replace("_indicators", "")

        return code, name

    # Process Plots (MACD/BB) -> GCS: charts/indicators
    # gcs.list_files returns filenames relative to prefix
    plots_files = gcs.list_files(CATEGORY_MAP["plots"])
    for fname in plots_files:
        if not fname.endswith(".png"):
            continue

        code, name = extract_info(fname)
        if code not in charts_map:
            charts_map[code] = {
                "code": code,
                "name": name,
                "plots": None,
                "chartImg": None,
            }
        charts_map[code]["plots"] = fname
        if charts_map[code]["name"] == "Unknown" and name != "Unknown":
            charts_map[code]["name"] = name

    # Process ChartImg (Signals) -> GCS: charts/signals
    signals_files = gcs.list_files(CATEGORY_MAP["chartImg"])
    for fname in signals_files:
        if not fname.endswith(".png"):
            continue

        code, name = extract_info(fname)
        if code not in charts_map:
            charts_map[code] = {
                "code": code,
                "name": name,
                "plots": None,
                "chartImg": None,
            }
        charts_map[code]["chartImg"] = fname
        if charts_map[code]["name"] == "Unknown" and name != "Unknown":
            charts_map[code]["name"] = name

    # Read data/my_stock.csv for summary info
    # data/my_stock.csv is expected at the bucket root or data/ path.
    # We try reading "my_stock.csv" assuming it is placed where expected.

    csv_content = gcs.get_file_content("my_stock.csv")
    stock_data = {}

    if csv_content:
        try:
            # Decode bytes to string
            text_content = csv_content.decode("utf-8")
            f = io.StringIO(text_content)
            reader = csv.DictReader(f)
            for row in reader:
                # Normalized code: "7203.T" -> "7203"
                raw_code = row.get("code", "")
                code_key = raw_code.replace(".T", "").replace(".", "")

                if code_key:
                    # Safe conversion for numbers
                    try:
                        purchase_price = float(row.get("purchase_price", 0))
                        current_price = float(row.get("current_price", 0))

                        # Handle potentially broken profit_loss_percent (e.g. template string)
                        pl_pct_str = row.get("profit_loss_percent", "")
                        if "{" in pl_pct_str or not pl_pct_str:
                            if purchase_price != 0:
                                pl_pct = (
                                    (current_price - purchase_price)
                                    / purchase_price
                                    * 100
                                )
                            else:
                                pl_pct = 0.0
                        else:
                            try:
                                pl_pct = float(
                                    pl_pct_str.replace("%", "").replace("+", "")
                                )
                            except ValueError:
                                pl_pct = 0.0

                        # Calculate simple profit_loss if needed
                        pl_val_str = row.get("profit_loss", "")
                        if "{" in pl_val_str or not pl_val_str:
                            pl_val = (current_price - purchase_price) * float(
                                row.get("quantity", 1)
                            )
                        else:
                            try:
                                pl_val = float(pl_val_str)
                            except ValueError:
                                pl_val = 0.0

                        stock_data[code_key] = {
                            "status": row.get("status", ""),
                            "current_price": current_price,
                            "purchase_price": purchase_price,
                            "profit_loss": pl_val,
                            "profit_loss_percent": pl_pct,
                            "quantity": row.get("quantity", ""),
                            "purchase_date": row.get("purchase_date", ""),
                            "last_updated": row.get("last_updated", ""),
                            "purpose": row.get("purpose", ""),
                        }
                    except ValueError:
                        print(f"Warning: Could not parse numbers for {raw_code}")
                        continue
        except Exception as e:
            print(f"Error reading CSV: {e}")

    results = sorted(list(charts_map.values()), key=lambda x: x["code"])

    # Merge stock_data into results
    for item in results:
        code = item["code"]
        if code in stock_data:
            item.update(stock_data[code])

    print(f"DEBUG: Found {len(results)} companies")
    return results


@router.get("/image/{category}/{filename}")
async def get_chart_image(category: str, filename: str):
    """Serve a specific chart image from GCS"""
    if category not in CATEGORY_MAP:
        raise HTTPException(status_code=400, detail="Invalid category")

    gcs_dir = CATEGORY_MAP[category]
    path = f"{gcs_dir}/{filename}"

    content = gcs.get_file_content(path)

    if not content:
        raise HTTPException(status_code=404, detail="Image not found")

    return Response(content=content, media_type="image/png")
