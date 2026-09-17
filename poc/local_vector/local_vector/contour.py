import cv2
import numpy as np


def extract_primary_contours(mask: np.ndarray) -> list[np.ndarray]:
    contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    contours = [c[:, 0, :].astype(np.float64) for c in contours if abs(cv2.contourArea(c)) > 4.0]
    return sorted(
        contours,
        key=lambda c: abs(cv2.contourArea(c.astype(np.float32))),
        reverse=True,
    )
