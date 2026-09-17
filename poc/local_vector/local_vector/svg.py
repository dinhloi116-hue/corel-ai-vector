from __future__ import annotations

from pathlib import Path

from .bezier import CubicBezier, LineSegment, PathGeometry, Point


def _f(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return "0" if text in {"-0", ""} else text


def _point(p: Point) -> str:
    return f"{_f(p.x)} {_f(p.y)}"


def path_to_svg_d(path: PathGeometry) -> str:
    if not path.segments:
        return ""
    commands = [f"M {_point(path.segments[0].p0)}"]
    for segment in path.segments:
        if isinstance(segment, LineSegment):
            commands.append(f"L {_point(segment.p1)}")
        elif isinstance(segment, CubicBezier):
            commands.append(
                f"C {_point(segment.c1)} {_point(segment.c2)} {_point(segment.p1)}"
            )
        else:
            raise TypeError(f"Unsupported segment: {type(segment)!r}")
    if path.closed:
        commands.append("Z")
    return " ".join(commands)


def write_svg(paths: list[PathGeometry], width: int, height: int, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    d_values = [path_to_svg_d(path) for path in paths if path.segments]
    body = "\n  ".join(f'<path d="{d}" />' for d in d_values)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        f'  <g fill="#000" stroke="none" fill-rule="evenodd">\n  {body}\n  </g>\n'
        f'</svg>\n'
    )
    output.write_text(svg, encoding="utf-8")
