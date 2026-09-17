from pathlib import Path
import cv2
import numpy as np
from local_vector.io import load_image, ensure_output_dir


def test_load_image_round_trip(tmp_path: Path):
    src = np.full((16, 24, 3), 127, dtype=np.uint8)
    image_path = tmp_path / "sample.png"
    assert cv2.imwrite(str(image_path), src)

    loaded = load_image(image_path)
    assert loaded.shape == (16, 24, 3)
    assert loaded.dtype == np.uint8


def test_ensure_output_dir_creates_directory(tmp_path: Path):
    out = ensure_output_dir(tmp_path / "out")
    assert out.exists()
    assert out.is_dir()

from local_vector.pipeline import run_pipeline


def test_pipeline_emits_two_glyph_artifact_sets(tmp_path: Path):
    image = np.full((500, 700, 3), 160, dtype=np.uint8)
    color = (180, 120, 20)
    cv2.rectangle(image, (100, 80), (220, 430), color, -1)
    cv2.ellipse(image, (470, 250), (130, 180), 0, 0, 360, color, -1)
    cv2.ellipse(image, (470, 250), (60, 115), 0, 0, 360, (160, 160, 160), -1)

    result = run_pipeline(image, tmp_path)
    assert len(result) == 2
    assert any(tmp_path.rglob("vector.svg"))
    assert any(tmp_path.rglob("metrics.json"))
