from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def build_icon(size: int = 256) -> Image.Image:
    scale = 4
    canvas = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    s = scale
    draw.rounded_rectangle(
        (10 * s, 10 * s, (size - 10) * s, (size - 10) * s),
        radius=58 * s,
        fill=(18, 21, 26, 255),
        outline=(48, 53, 65, 255),
        width=4 * s,
    )
    ring = (56 * s, 56 * s, (size - 56) * s, (size - 56) * s)
    draw.arc(ring, 35, 325, fill=(52, 58, 70, 255), width=22 * s)
    draw.arc(ring, 35, 248, fill=(139, 140, 255, 255), width=22 * s)
    draw.ellipse(
        (171 * s, 168 * s, 203 * s, 200 * s),
        fill=(81, 216, 138, 255),
        outline=(18, 21, 26, 255),
        width=6 * s,
    )
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the project-owned Windows icon")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing icon: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    icon = build_icon()
    icon.save(
        output,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
