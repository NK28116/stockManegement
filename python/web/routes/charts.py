import csv
import io
import json
import logging
import os
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Response

from python.utils.gcs_client import gcs

router = APIRouter(prefix="/api/charts", tags=["charts"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Map category names to paths (GCS vs Local)
if gcs.use_gcs:
    CATEGORY_MAP = {
        "plots": "charts/indicators",
        "chartImg": "charts/signals",
    }
else:
    # Local structure is slightly different (based on data/ listing)
    CATEGORY_MAP = {
        "plots": "plots",
        "chartImg": "chartImg",
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

    # Load latest_indicators.json
    latest_indicators = {}
    json_filename = "latest_indicators.json"
    json_content = gcs.get_file_content(json_filename)

    if not gcs.use_gcs and not json_content:
        # For local dev, try direct file read from the expected local path
        local_json_path = os.path.join("data", json_filename)
        if os.path.exists(local_json_path):
            try:
                with open(local_json_path, "rb") as f:
                    json_content = f.read()
            except Exception as e:
                logger.warning(
                    f"Error reading local JSON fallback '{local_json_path}': {e}"
                )
        else:
            logger.info(f"Local JSON file '{local_json_path}' not found.")

    if json_content:
        try:
            latest_indicators = json.loads(json_content.decode("utf-8"))
            logger.info(f"Loaded {len(latest_indicators)} entries from {json_filename}")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding {json_filename}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading {json_filename}: {e}")
    else:
        logger.info(
            f"Could not load {json_filename}. Proceeding without specific indicators."
        )

    # Normalize keys in latest_indicators (remove .T) to match chart keys
    normalized_indicators = {}
    for k, v in latest_indicators.items():
        # "7203.T" -> "7203"
        norm_k = k.replace(".T", "").replace(".", "")
        normalized_indicators[norm_k] = v
    latest_indicators = normalized_indicators

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
    # For local dev, use my_stock_local.csv
    csv_filename = "my_stock.csv" if gcs.use_gcs else "data/my_stock_local.csv"
    csv_content = gcs.get_file_content(csv_filename)

    # Fallback logic for GCS: If GCS file is missing, try local data/my_stock.csv
    if gcs.use_gcs and not csv_content:
        logger.warning(
            "GCS my_stock.csv not found. Falling back to local data/my_stock.csv"
        )
        try:
            with open("data/my_stock.csv", "rb") as f:
                csv_content = f.read()
        except Exception as e:
            logger.error(f"Error reading local fallback 'data/my_stock.csv': {e}")

    # Fallback logic for Local Dev: If gcs_client failed (shouldn't happen for local but as safety)
    if not gcs.use_gcs and not csv_content:
        # If gcs_client failed to load local file via get_file_content,
        # try direct file read for local dev safety net
        try:
            with open(csv_filename, "rb") as f:
                csv_content = f.read()
        except Exception as e:
            logger.error(f"Error reading local CSV fallback '{csv_filename}': {e}")

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
