"""Behavior tests for the runtime implementation of NB02."""
from __future__ import annotations

import numpy as np
import pytest

from app.services.simulation_service import EXPERIMENT_SEVERITIES, method_metadata, simulate_experiment
from research.core.machado import simulate_machado_bgr


@pytest.fixture
def sample_image() -> np.ndarray:
    y, x = np.mgrid[0:16, 0:16]
    return np.stack(((x * 11 + y * 3) % 256, (x * 5 + y * 13) % 256, (x * 17 + y * 7) % 256), axis=-1).astype(np.uint8)


def test_severity_zero_is_identity(sample_image: np.ndarray) -> None:
    output, diagnostics = simulate_machado_bgr(sample_image, "protan", 0.0)
    assert np.array_equal(output, sample_image)
    assert diagnostics["clip_any_ratio"] == 0.0


def test_experiment_returns_complete_grid(sample_image: np.ndarray) -> None:
    results = simulate_experiment(sample_image)
    assert len(results) == 8
    assert [(item.cvd_type, item.severity) for item in results] == [
        (family, severity)
        for family in ("protan", "deutan")
        for severity in EXPERIMENT_SEVERITIES
    ]


def test_outputs_and_metrics_are_valid(sample_image: np.ndarray) -> None:
    for item in simulate_experiment(sample_image):
        assert item.image_bgr.shape == sample_image.shape
        assert item.image_bgr.dtype == np.uint8
        assert 0.0 <= item.mean_abs_rgb_change <= 1.0
        assert 0.0 <= item.changed_pixel_ratio <= 1.0
        assert 0.0 <= item.clip_any_ratio <= 1.0
        assert np.asarray(item.matrix).shape == (3, 3)


def test_metadata_matches_experiment() -> None:
    metadata = method_metadata()
    assert metadata["cvdTypes"] == ["protan", "deutan"]
    assert metadata["severities"] == list(EXPERIMENT_SEVERITIES)
    assert "diagnosis" in metadata["disclaimer"]

