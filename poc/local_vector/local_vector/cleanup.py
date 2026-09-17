import cv2
import numpy as np


def clean_glyph_mask(mask: np.ndarray, small_hole_area_ratio: float = 0.015) -> np.ndarray:
    cleaned = mask.copy()
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return cleaned

    foreground_area = max(int(cv2.countNonZero(mask)), 1)
    hierarchy = hierarchy[0]
    for idx, contour in enumerate(contours):
        parent = hierarchy[idx][3]
        if parent < 0:
            continue
        hole_area = abs(cv2.contourArea(contour))
        if hole_area / foreground_area < small_hole_area_ratio:
            cv2.drawContours(cleaned, [contour], -1, 255, thickness=-1)
    return cleaned
