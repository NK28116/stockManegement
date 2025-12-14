import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/charts", tags=["charts"])


# Helper to get data paths safely
def get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "data"


@router.get("/list")
async def list_charts() -> List[Dict[str, Any]]:
    """List available charts grouped by company"""
    data_dir = get_data_dir()
    print(f"DEBUG: Looking for data in {data_dir}")

    charts_map = {}

    import re

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

    # Process Plots (MACD/BB)
    plots_dir = data_dir / "plots"
    print(f"DEBUG: Checking plots_dir {plots_dir} (Exists: {plots_dir.exists()})")
    if plots_dir.exists():
        for f in plots_dir.glob("*.png"):
            # print(f"DEBUG: Found plot {f.name}")
            code, name = extract_info(f.name)
            if code not in charts_map:
                charts_map[code] = {"code": code, "name": name, "plots": None, "chartImg": None}
            charts_map[code]["plots"] = f.name
            if charts_map[code]["name"] == "Unknown" and name != "Unknown":
                charts_map[code]["name"] = name

    # Process ChartImg (Signals)
    chart_img_dir = data_dir / "chartImg"
    if chart_img_dir.exists():
        for f in chart_img_dir.glob("*.png"):
            # print(f"DEBUG: Found chartImg {f.name}")
            code, name = extract_info(f.name)
            if code not in charts_map:
                charts_map[code] = {"code": code, "name": name, "plots": None, "chartImg": None}
            charts_map[code]["chartImg"] = f.name
            if charts_map[code]["name"] == "Unknown" and name != "Unknown":
                charts_map[code]["name"] = name

    results = sorted(list(charts_map.values()), key=lambda x: x["code"])
    print(f"DEBUG: Found {len(results)} companies")
    return results


@router.get("/image/{category}/{filename}")
async def get_chart_image(category: str, filename: str):
    """Serve a specific chart image"""
    if category not in ["plots", "chartImg"]:
        raise HTTPException(status_code=400, detail="Invalid category")

    data_dir = get_data_dir()
    file_path = data_dir / category / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(file_path)
