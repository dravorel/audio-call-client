import argparse

from PIL import Image


def convert_png_to_ico(png_path: str, ico_path: str, size: int):
    with Image.open(png_path) as img:
        img = img.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
        img.save(ico_path, format="ICO", sizes=[(size, size)])


def main():
    parser = argparse.ArgumentParser(
        description="Convert PNG image to ICO format.",
    )
    parser.add_argument("png", help="Path to source PNG file")
    parser.add_argument("ico", help="Path to output ICO file")
    parser.add_argument(
        "--size",
        default=256,
        help="Icon size in pixels (default: 256)",
    )
    args = parser.parse_args()

    convert_png_to_ico(args.png, args.ico, size=args.size)


if __name__ == "__main__":
    main()
