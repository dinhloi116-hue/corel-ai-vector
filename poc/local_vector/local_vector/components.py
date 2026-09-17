from dataclasses import dataclass
import cv2
import numpy as np


@dataclass(frozen=True)
class Component:
    label: int
    x: int
    y: int
    w: int
    h: int
    area: int


def find_components(mask: np.ndarray, min_area_ratio: float = 0.002) -> list[Component]:
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    min_area = mask.shape[0] * mask.shape[1] * min_area_ratio
    result = []
    for label in range(1, count):
        x, y, w, h, area = stats[label]
        if area >= min_area:
            result.append(Component(label, int(x), int(y), int(w), int(h), int(area)))
    return result


def select_large_glyphs(components: list[Component], image_shape: tuple[int, int]) -> list[Component]:
    height, width = image_shape
    candidates = [
        c for c in components
        if c.h / height >= 0.35
        and c.w / width >= 0.05
        and c.x > 0
        and c.y > 0
        and c.x + c.w < width
        and c.y + c.h < height
        and c.w / width < 0.8
        and c.h / height < 0.8
    ]
    return sorted(candidates, key=lambda c: c.x)
