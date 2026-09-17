import cv2
import numpy as np
from local_vector.segmentation import segment_colored_artwork


def test_segment_colored_artwork_ignores_gray_background():
    image = np.full((120, 160, 3), 180, dtype=np.uint8)
    cv2.rectangle(image, (40, 30), (120, 95), (180, 120, 20), thickness=-1)

    mask = segment_colored_artwork(image)

    assert mask[60, 80] == 255
    assert mask[10, 10] == 0
    assert set(np.unique(mask)).issubset({0, 255})


def test_segment_mask_contract():
    image = np.zeros((30, 40, 3), dtype=np.uint8)
    mask = segment_colored_artwork(image)
    assert mask.shape == image.shape[:2]
    assert mask.dtype == np.uint8
