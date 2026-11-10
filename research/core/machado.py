"""Machado severity-dependent CVD simulation for NB02 and NB03.

The tabulated matrices and interpolation rule follow Machado et al. (2009)
and the authors' public supplementary material. Input sRGB is linearized
before the matrix transform and encoded again after gamut clipping.
"""

from __future__ import annotations

import cv2
import numpy as np


IMPLEMENTATION_VERSION = "machado-2009-core-1.1"
VALID_CVD_FAMILIES = ("protan", "deutan")
_FAMILY_ALIASES = {
    "protan": "protanopia",
    "deutan": "deuteranopia",
    "protanopia": "protanopia",
    "deuteranopia": "deuteranopia",
}
MACHADO_MATRICES = {'protanopia': {0.0: [[1, 0, 0], [0, 1, 0], [0, 0, 1]], 0.1: [[0.856167, 0.182038, -0.038205], [0.029342, 0.955115, 0.015544], [-0.00288, -0.001563, 1.004443]], 0.2: [[0.734766, 0.334872, -0.069637], [0.05184, 0.919198, 0.028963], [-0.004928, -0.004209, 1.009137]], 0.3: [[0.630323, 0.465641, -0.095964], [0.069181, 0.890046, 0.040773], [-0.006308, -0.007724, 1.014032]], 0.4: [[0.539009, 0.579343, -0.118352], [0.082546, 0.866121, 0.051332], [-0.007136, -0.011959, 1.019095]], 0.5: [[0.458064, 0.679578, -0.137642], [0.092785, 0.846313, 0.060902], [-0.007494, -0.016807, 1.024301]], 0.6: [[0.38545, 0.769005, -0.154455], [0.100526, 0.829802, 0.069673], [-0.007442, -0.02219, 1.029632]], 0.7: [[0.319627, 0.849633, -0.169261], [0.106241, 0.815969, 0.07779], [-0.007025, -0.028051, 1.035076]], 0.8: [[0.259411, 0.923008, -0.18242], [0.110296, 0.80434, 0.085364], [-0.006276, -0.034346, 1.040622]], 0.9: [[0.203876, 0.990338, -0.194214], [0.112975, 0.794542, 0.092483], [-0.005222, -0.041043, 1.046265]], 1.0: [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]]}, 'deuteranopia': {0.0: [[1, 0, 0], [0, 1, 0], [0, 0, 1]], 0.1: [[0.866435, 0.177704, -0.044139], [0.049567, 0.939063, 0.01137], [-0.003453, 0.007233, 0.99622]], 0.2: [[0.760729, 0.319078, -0.079807], [0.090568, 0.889315, 0.020117], [-0.006027, 0.013325, 0.992702]], 0.3: [[0.675425, 0.43385, -0.109275], [0.125303, 0.847755, 0.026942], [-0.00795, 0.018572, 0.989378]], 0.4: [[0.605511, 0.52856, -0.134071], [0.155318, 0.812366, 0.032316], [-0.009376, 0.023176, 0.9862]], 0.5: [[0.547494, 0.607765, -0.155259], [0.181692, 0.781742, 0.036566], [-0.01041, 0.027275, 0.983136]], 0.6: [[0.498864, 0.674741, -0.173604], [0.205199, 0.754872, 0.039929], [-0.011131, 0.030969, 0.980162]], 0.7: [[0.457771, 0.731899, -0.18967], [0.226409, 0.731012, 0.042579], [-0.011595, 0.034333, 0.977261]], 0.8: [[0.422823, 0.781057, -0.203881], [0.245752, 0.709602, 0.044646], [-0.011843, 0.037423, 0.974421]], 0.9: [[0.392952, 0.82361, -0.216562], [0.263559, 0.69021, 0.046232], [-0.01191, 0.040281, 0.97163]], 1.0: [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.01182, 0.04294, 0.968881]]}}

# Store the published matrices as float32 arrays.
MACHADO_MATRICES = {
    cvd_type: {
        float(severity): np.asarray(matrix, dtype=np.float32)
        for severity, matrix in table.items()
    }
    for cvd_type, table in MACHADO_MATRICES.items()
}


def _matrix_family(cvd_family: str) -> str:
    try:
        return _FAMILY_ALIASES[cvd_family]
    except KeyError as exc:
        raise ValueError(f"Unsupported CVD family: {cvd_family}") from exc


def validate_cvd_parameters(cvd_family: str, severity: float) -> None:
    """Validate the CVD family and severity interval."""
    _matrix_family(cvd_family)
    if not 0.0 <= float(severity) <= 1.0:
        raise ValueError(f"severity must be in [0, 1], received {severity}")


def get_machado_matrix(
    cvd_family: str,
    severity: float,
) -> np.ndarray:
    """Return a tabulated or linearly interpolated Machado matrix."""
    validate_cvd_parameters(cvd_family, severity)
    family = _matrix_family(cvd_family)

    severity = float(severity)
    lower = round(np.floor(severity * 10.0) / 10.0, 1)
    upper = round(np.ceil(severity * 10.0) / 10.0, 1)

    if lower == upper:
        matrix = MACHADO_MATRICES[family][lower].copy()
    else:
        weight = (severity - lower) / (upper - lower)
        matrix = (
            (1.0 - weight) * MACHADO_MATRICES[family][lower]
            + weight * MACHADO_MATRICES[family][upper]
        ).astype(np.float32)
    return matrix


def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    """Convert normalized sRGB to linear RGB (IEC 61966-2-1 transfer)."""
    rgb = np.clip(np.asarray(rgb, dtype=np.float32), 0.0, 1.0)
    return np.where(
        rgb <= 0.04045,
        rgb / 12.92,
        np.power((rgb + 0.055) / 1.055, 2.4),
    ).astype(np.float32)


def linear_to_srgb(rgb: np.ndarray) -> np.ndarray:
    """Convert clipped linear RGB to normalized sRGB."""
    rgb = np.clip(np.asarray(rgb, dtype=np.float32), 0.0, 1.0)
    return np.where(
        rgb <= 0.0031308,
        12.92 * rgb,
        1.055 * np.power(rgb, 1.0 / 2.4) - 0.055,
    ).astype(np.float32)


def simulate_machado_rgb(
    image_rgb: np.ndarray,
    cvd_family: str,
    severity: float,
) -> tuple[np.ndarray, dict[str, float]]:
    """Simulate a uint8 RGB image and return gamut-clipping diagnostics."""
    validate_cvd_parameters(cvd_family, severity)

    if (
        image_rgb.dtype != np.uint8
        or image_rgb.ndim != 3
        or image_rgb.shape[2] != 3
    ):
        raise ValueError("image_rgb must be uint8 with shape (H, W, 3)")

    if float(severity) == 0.0:
        diagnostics = {"clip_low_ratio": 0.0, "clip_high_ratio": 0.0, "clip_any_ratio": 0.0}
        return image_rgb.copy(), diagnostics

    linear_rgb = srgb_to_linear(image_rgb.astype(np.float32) / 255.0)
    transformed = cv2.transform(linear_rgb, get_machado_matrix(cvd_family, severity))
    low = np.any(transformed < 0.0, axis=2)
    high = np.any(transformed > 1.0, axis=2)
    diagnostics = {
        "clip_low_ratio": float(low.mean()),
        "clip_high_ratio": float(high.mean()),
        "clip_any_ratio": float(np.logical_or(low, high).mean()),
    }
    simulated = linear_to_srgb(transformed)
    output = np.rint(simulated * 255.0).clip(0, 255).astype(np.uint8)
    return output, diagnostics


def simulate_machado_bgr(
    image_bgr: np.ndarray,
    cvd_family: str,
    severity: float,
) -> tuple[np.ndarray, dict[str, float]]:
    """Simulate a uint8 BGR image and return diagnostics."""
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    simulated_rgb, diagnostics = simulate_machado_rgb(rgb, cvd_family, severity)
    return cv2.cvtColor(simulated_rgb, cv2.COLOR_RGB2BGR), diagnostics
