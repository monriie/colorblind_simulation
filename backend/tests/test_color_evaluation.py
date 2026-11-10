"""Check NB03 equivalence and the data supplied to the evaluation UI."""
import asyncio
import ast
import base64
import io
import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi import UploadFile
from skimage.color import deltaE_ciede2000
from starlette.requests import Request

from app.api.simulation import analyze_simulation
from app.services.color_evaluation import delta_e00_map, render_delta_e00_heatmap
from app.services.simulation_service import simulate_experiment
from app.utils.image_io import encode_png


def test_map_matches_nb03_across_strip_boundary():
    # Execute only the reference map function, without running notebook cells.
    notebook_path = Path(__file__).resolve().parents[2] / (
        "research/notebooks/tanpa_segmentasi/03/NB03_simulation_validation.ipynb"
    )
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    functions = [
        node
        for cell in notebook["cells"] if cell["cell_type"] == "code"
        if "def calculate_delta_e00_map(" in "".join(cell["source"])
        for node in ast.parse("".join(cell["source"])).body
        if isinstance(node, ast.FunctionDef) and node.name == "calculate_delta_e00_map"
    ]
    assert len(functions) == 1
    reference = {"np": np, "cv2": cv2, "deltaE_ciede2000": deltaE_ciede2000}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(notebook_path), "exec"), reference)
    rng = np.random.default_rng(42)
    original = rng.integers(0, 256, (131, 9, 3), dtype=np.uint8)
    simulated = rng.integers(0, 256, original.shape, dtype=np.uint8)
    expected = reference["calculate_delta_e00_map"](original, simulated)
    actual = delta_e00_map(original, simulated)
    assert actual.dtype == np.float64
    np.testing.assert_array_equal(actual, expected)
    assert float(actual.mean()) == float(expected.mean())


def test_float_inputs_are_rejected_before_opencv_lab_conversion():
    image = np.zeros((2, 2, 3), dtype=np.float32)
    with pytest.raises(ValueError, match="uint8"):
        delta_e00_map(image, image)


def test_identity_and_zero_scale_are_finite():
    original = np.zeros((4, 5, 3), dtype=np.uint8)
    differences = delta_e00_map(original, original)
    assert not differences.any()
    heatmap = render_delta_e00_heatmap(differences, 0)
    assert heatmap.shape == original.shape
    assert heatmap.dtype == np.uint8
    assert np.isfinite(heatmap).all()
    for item in simulate_experiment(original):
        assert item.mean_delta_e00 == 0


def test_shared_scale_preserves_equal_value_colors():
    first = render_delta_e00_heatmap(np.array([[0, 5, 10]], np.float32), 10)
    second = render_delta_e00_heatmap(np.array([[5]], np.float32), 10)
    np.testing.assert_array_equal(first[0, 1], second[0, 0])


def test_shape_mismatch_is_rejected():
    with pytest.raises(ValueError, match="Dimensi"):
        delta_e00_map(np.zeros((2, 2, 3), np.uint8), np.zeros((3, 2, 3), np.uint8))


def decode_data_url(url):
    assert url.startswith("data:image/png;base64,")
    return cv2.imdecode(np.frombuffer(base64.b64decode(url.split(',', 1)[1]), np.uint8), cv2.IMREAD_COLOR)


def test_api_payload_contains_lossless_images_metrics_and_shared_heatmaps():
    original = np.array([[[0, 0, 255], [0, 255, 0], [255, 0, 0]]], np.uint8)
    upload = UploadFile(filename="colors.png", file=io.BytesIO(encode_png(original)))
    request = Request({"type": "http", "method": "POST", "path": "/api/simulation/analyze", "headers": []})
    # Exercise the endpoint contract without the unrelated rate-limit wrapper.
    response = asyncio.run(analyze_simulation.__wrapped__(request=request, image=upload))
    np.testing.assert_array_equal(decode_data_url(response['original']), original)
    assert len(response['results']) == 8
    scale = response['heatmapScale']['max']
    maxima = []
    for result in response['results']:
        simulated = decode_data_url(result['image'])
        differences = delta_e00_map(original, simulated)
        assert result['metrics']['meanDeltaE00'] == pytest.approx(float(differences.mean()))
        maxima.append(float(differences.max()))
        np.testing.assert_array_equal(
            decode_data_url(result['deltaE00Heatmap']),
            render_delta_e00_heatmap(differences, scale),
        )
    assert scale == max(maxima)
