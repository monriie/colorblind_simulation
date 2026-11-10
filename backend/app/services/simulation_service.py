"""Orchestrate the Machado simulation used by the research notebooks."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.services.color_evaluation import delta_e00_map

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research.core.machado import (  # noqa: E402
    IMPLEMENTATION_VERSION,
    VALID_CVD_FAMILIES,
    get_machado_matrix,
    simulate_machado_bgr,
)

EXPERIMENT_SEVERITIES = (0.25, 0.5, 0.75, 1.0)


@dataclass(frozen=True)
class SimulationResult:
    """One simulated image and its descriptive diagnostics."""

    cvd_type: str
    severity: float
    image_bgr: np.ndarray
    delta_e00: np.ndarray
    mean_delta_e00: float
    mean_abs_rgb_change: float
    changed_pixel_ratio: float
    clip_low_ratio: float
    clip_high_ratio: float
    clip_any_ratio: float
    matrix: list[list[float]]


def simulate_experiment(image_bgr: np.ndarray) -> list[SimulationResult]:
    """Run the fixed NB02 experiment grid for one BGR image."""
    results: list[SimulationResult] = []
    for cvd_type in VALID_CVD_FAMILIES:
        for severity in EXPERIMENT_SEVERITIES:
            simulated, diagnostics = simulate_machado_bgr(
                image_bgr, cvd_type, severity
            )
            change = np.abs(
                simulated.astype(np.int16) - image_bgr.astype(np.int16)
            )
            differences = delta_e00_map(image_bgr, simulated)
            results.append(
                SimulationResult(
                    cvd_type=cvd_type,
                    severity=severity,
                    image_bgr=simulated,
                    delta_e00=differences,
                    mean_delta_e00=float(differences.mean()),
                    mean_abs_rgb_change=float(change.mean() / 255.0),
                    changed_pixel_ratio=float(
                        np.any(simulated != image_bgr, axis=2).mean()
                    ),
                    clip_low_ratio=diagnostics["clip_low_ratio"],
                    clip_high_ratio=diagnostics["clip_high_ratio"],
                    clip_any_ratio=diagnostics["clip_any_ratio"],
                    matrix=get_machado_matrix(cvd_type, severity)
                    .astype(float)
                    .tolist(),
                )
            )
    return results


def method_metadata() -> dict[str, object]:
    """Describe the runtime configuration without a clinical claim."""
    return {
        "engine": IMPLEMENTATION_VERSION,
        "cvdTypes": list(VALID_CVD_FAMILIES),
        "severities": list(EXPERIMENT_SEVERITIES),
        "pipeline": [
            "Normalisasi sRGB",
            "Inverse transfer sRGB",
            "Interpolasi matriks Machado",
            "Transformasi RGB linear",
            "Diagnostik dan clipping gamut",
            "Encoding sRGB dan kuantisasi uint8",
        ],
        "disclaimer": (
            "Keluaran adalah simulasi komputasional model Machado, bukan "
            "diagnosis atau representasi pasti persepsi setiap individu CVD."
        ),
    }

