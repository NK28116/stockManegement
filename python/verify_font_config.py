import matplotlib.pyplot as plt

from python.visualization.stock_chart_visualizer import StockChartVisualizer


def verify():
    # Helper to check font config
    # This initializes the visualizer which sets the font via imports/init
    StockChartVisualizer(is_test_mode=True)

    current_font = plt.rcParams["font.family"]
    print(f"Current font.family: {current_font}")

    # Common Japanese fonts on macOS
    expected_fonts = [
        "Hiragino Sans",
        "Hiragino Kaku Gothic ProN",
        "Hiragino Kaku Gothic Pro",
    ]

    # Matplotlib might return a list or string
    current_font_str = str(current_font)

    is_valid = False
    for font in expected_fonts:
        if font in current_font_str:
            is_valid = True
            break

    if is_valid:
        print("SUCCESS: specific Japanese font is configured.")
    else:
        print(f"WARNING: Font {current_font} may not support Japanese correctly.")


if __name__ == "__main__":
    verify()
