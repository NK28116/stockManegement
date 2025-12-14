from pathlib import Path
import os
import sys

# Mimic the logic in python/web/routes/charts.py


def list_charts_debug():
    # Construct path relative to this script (assuming script is in root)
    root_dir = Path(os.getcwd())
    data_dir = root_dir / "data"

    print(f"Root: {root_dir}")
    print(f"Data: {data_dir}")

    charts_map = {}

    def extract_info(filename: str):
        parts = filename.split("_")
        code = parts[0].replace(".T", "").replace(".", "")
        name = "Unknown"
        if len(parts) > 1:
            name = parts[1]
            if name == "T" and len(parts) > 2:
                name = parts[2]
        name = name.replace(".png", "").replace("_indicators", "")
        return code, name

    plots_dir = data_dir / "plots"
    print(f"Plots Dir Exists? {plots_dir.exists()}")
    count_plots = 0
    if plots_dir.exists():
        for f in plots_dir.glob("*.png"):
            count_plots += 1
            code, name = extract_info(f.name)
            print(f"  Found Plot: {f.name} -> Code: {code}, Name: {name}")
            if code not in charts_map:
                charts_map[code] = {"code": code, "name": name, "plots": None, "chartImg": None}
            charts_map[code]["plots"] = f.name

    chart_img_dir = data_dir / "chartImg"
    print(f"ChartImg Dir Exists? {chart_img_dir.exists()}")
    count_img = 0
    if chart_img_dir.exists():
        for f in chart_img_dir.glob("*.png"):
            count_img += 1
            code, name = extract_info(f.name)
            print(f"  Found Img: {f.name} -> Code: {code}, Name: {name}")
            if code not in charts_map:
                charts_map[code] = {"code": code, "name": name, "plots": None, "chartImg": None}
            charts_map[code]["chartImg"] = f.name

    print(f"Total Companies Found: {len(charts_map)}")
    return sorted(list(charts_map.values()), key=lambda x: x["code"])


if __name__ == "__main__":
    results = list_charts_debug()
    for r in results:
        print(r)
