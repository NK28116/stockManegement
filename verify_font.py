import matplotlib
import matplotlib.pyplot as plt
import japanize_matplotlib


def verify_font():
    font_family = matplotlib.rcParams["font.family"]
    print(f"Current font family: {font_family}")

    # Check if IPAexGothic is in the font family list
    # japanize_matplotlib typically sets it as the first item or the main item
    if "IPAexGothic" in font_family or (isinstance(font_family, list) and "IPAexGothic" in font_family):
        print("SUCCESS: IPAexGothic is configured.")
    else:
        print("FAILURE: IPAexGothic is NOT configured.")


if __name__ == "__main__":
    verify_font()
