import os
from pathlib import Path
from typing import List, Dict
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/charts", tags=["charts"])

# Helper to get data paths safely
def get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "data"

@router.get("/list")
async def list_charts() -> Dict[str, List[str]]:
    """List available charts in data/plots and data/chartImg"""
    data_dir = get_data_dir()
    charts = {"plots": [], "chartImg": []}
    
    plots_dir = data_dir / "plots"
    if plots_dir.exists():
        charts["plots"] = [f.name for f in plots_dir.glob("*.png")]
        
    chart_img_dir = data_dir / "chartImg"
    if chart_img_dir.exists():
        charts["chartImg"] = [f.name for f in chart_img_dir.glob("*.png")]
        
    return charts

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
