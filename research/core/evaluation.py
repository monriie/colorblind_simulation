"""Lightweight per-image evaluation extracted from NB04."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from .cielab import bgr_to_rgb_tensor, delta_e76_map, rgb_tensor_to_bgr, rgb_to_lab
from .correction import default_device
from .machado import get_machado_matrix, simulate_machado, validate_cvd_parameters


VALIDATION_PAIR_OFFSETS = (
    (0, 2),
    (2, 0),
    (2, 2),
    (2, -2),
    (1, 2),
    (2, 1),
    (1, -2),
    (2, -1),
)
CONFUSION_DISTANCE_SCALE = 3.0
MEANINGFUL_IMPROVEMENT_THRESHOLD = 0.05


@dataclass(frozen=True)
class EvaluationResult:
    simulated_after_bgr: np.ndarray
    confusion_recovery: float
    perceptual_recovery: float
    naturalness_delta_e: float


def _edge_slices(height: int, width: int, dy: int, dx: int) -> tuple[slice, ...]:
    y_a, y_b = (slice(0, height - dy), slice(dy, height)) if dy >= 0 else (slice(-dy, height), slice(0, height + dy))
    x_a, x_b = (slice(0, width - dx), slice(dx, width)) if dx >= 0 else (slice(-dx, width), slice(0, width + dx))
    return y_a, x_a, y_b, x_b


def _independent_confusion_recovery(
    original_lab: torch.Tensor,
    baseline_lab: torch.Tensor,
    corrected_seen_lab: torch.Tensor,
) -> float:
    _, _, height, width = original_lab.shape
    original_a, original_b = original_lab[:, 1:2], original_lab[:, 2:3]
    baseline_a, baseline_b = baseline_lab[:, 1:2], baseline_lab[:, 2:3]
    after_a, after_b = corrected_seen_lab[:, 1:2], corrected_seen_lab[:, 2:3]
    weighted_sum = torch.zeros((), device=original_lab.device)
    weight_sum = torch.zeros((), device=original_lab.device)

    for dy, dx in VALIDATION_PAIR_OFFSETS:
        y_a, x_a, y_b, x_b = _edge_slices(height, width, dy, dx)
        original_distance = torch.sqrt(
            (original_a[:, :, y_a, x_a] - original_a[:, :, y_b, x_b]) ** 2
            + (original_b[:, :, y_a, x_a] - original_b[:, :, y_b, x_b]) ** 2
            + 1e-8
        )
        baseline_distance = torch.sqrt(
            (baseline_a[:, :, y_a, x_a] - baseline_a[:, :, y_b, x_b]) ** 2
            + (baseline_b[:, :, y_a, x_a] - baseline_b[:, :, y_b, x_b]) ** 2
            + 1e-8
        )
        after_distance = torch.sqrt(
            (after_a[:, :, y_a, x_a] - after_a[:, :, y_b, x_b]) ** 2
            + (after_b[:, :, y_a, x_a] - after_b[:, :, y_b, x_b]) ** 2
            + 1e-8
        )
        separation_loss = torch.relu(original_distance - baseline_distance)
        edge_relevance = original_distance / (original_distance + CONFUSION_DISTANCE_SCALE)
        confusion_weight = separation_loss / (original_distance + 1e-6) * edge_relevance
        recovered_distance = torch.minimum(after_distance, original_distance)
        recovery = ((recovered_distance - baseline_distance) / (separation_loss + 1e-6)).clamp(-1.0, 1.0)
        weighted_sum += torch.sum(recovery * confusion_weight)
        weight_sum += torch.sum(confusion_weight)

    return float("nan") if weight_sum.item() <= 1e-8 else float((weighted_sum / weight_sum).item())


@torch.inference_mode()
def evaluate_correction(
    original_bgr: np.ndarray,
    baseline_bgr: np.ndarray,
    corrected_bgr: np.ndarray,
    cvd_type: str,
    severity: float,
    *,
    device: torch.device | str | None = None,
) -> EvaluationResult:
    """Evaluate one corrected image using the three NB04 metrics."""
    validate_cvd_parameters(cvd_type, severity)
    if original_bgr.shape != baseline_bgr.shape or original_bgr.shape != corrected_bgr.shape:
        raise ValueError("original, baseline, and corrected images must have identical shapes")

    active_device = torch.device(device) if device is not None else default_device()
    original_rgb = bgr_to_rgb_tensor(original_bgr, active_device)
    baseline_rgb = bgr_to_rgb_tensor(baseline_bgr, active_device)
    corrected_rgb = bgr_to_rgb_tensor(corrected_bgr, active_device)
    matrix = get_machado_matrix(cvd_type, severity, device=active_device)
    corrected_seen_rgb = simulate_machado(corrected_rgb, matrix)

    original_lab = rgb_to_lab(original_rgb)
    baseline_lab = rgb_to_lab(baseline_rgb)
    corrected_lab = rgb_to_lab(corrected_rgb)
    corrected_seen_lab = rgb_to_lab(corrected_seen_rgb)
    confusion_recovery = _independent_confusion_recovery(original_lab, baseline_lab, corrected_seen_lab)
    error_before = delta_e76_map(original_lab, baseline_lab).mean()
    error_after = delta_e76_map(original_lab, corrected_seen_lab).mean()
    perceptual_recovery = float("nan") if error_before.item() <= 1e-8 else float((1.0 - error_after / error_before).item())
    naturalness = float(delta_e76_map(original_lab, corrected_lab).mean().item())

    return EvaluationResult(
        simulated_after_bgr=rgb_tensor_to_bgr(corrected_seen_rgb),
        confusion_recovery=confusion_recovery,
        perceptual_recovery=perceptual_recovery,
        naturalness_delta_e=naturalness,
    )


def improvement_status(confusion_recovery: float) -> str:
    if confusion_recovery > MEANINGFUL_IMPROVEMENT_THRESHOLD:
        return "meaningful_improvement"
    if confusion_recovery >= 0.0:
        return "small_improvement"
    return "decreased"
