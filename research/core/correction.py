"""Reusable selective confusion-aware CIELAB correction from NB03."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from kornia.filters import gaussian_blur2d

from .cielab import (
    bgr_to_rgb_tensor,
    delta_e76_map,
    lab_to_rgb,
    rgb_tensor_to_bgr,
    rgb_to_lab,
    smoothstep,
)
from .machado import get_machado_matrix, simulate_machado, validate_cvd_parameters


CANDIDATE_FACTORS = (-1.50, -1.00, -0.50, 0.00, 0.50, 1.00, 1.50)
CANDIDATE_BATCH_SIZE = 2
TRANSFER_B_MAX = {"protanopia": 28.0, "deuteranopia": 32.0}
LOST_A_SCALE = 16.0
LOSS_LOW = 0.50
LOSS_HIGH = 13.0
CHROMA_SOFT_SCALE = 9.0
SELECTION_PAIR_OFFSETS = ((0, 1), (1, 0), (1, 1), (1, -1))
CONFUSION_DISTANCE_SCALE = 3.0
OBJECTIVE_WEIGHTS = {
    "confusion": 0.68,
    "perceptual_recovery": 0.20,
    "naturalness": 0.12,
}
MIN_USEFUL_SCORE = 0.015
CONFUSION_RELEVANCE_LOW = 0.08
CONFUSION_RELEVANCE_HIGH = 0.30
SCORE_CONFIDENCE_FULL = 0.12
NATURALNESS_BASE = 1.5
NATURALNESS_ERROR_RATIO = 1.10
NATURALNESS_MAX_DELTA = 22.0
FINAL_SMOOTH_KSIZE = 5
FINAL_SMOOTH_SIGMA = 1.0
CORRECTED_DELTA_B_THRESHOLD = 1e-3
STRONG_CORRECTION_DELTA_B_THRESHOLD = 1.0


@dataclass(frozen=True)
class CorrectionResult:
    image_bgr: np.ndarray
    corrected_pixel_pct: float
    strongly_corrected_pixel_pct: float
    mean_abs_delta_b: float
    magnitude_map: np.ndarray


def default_device() -> torch.device:
    return torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


def _edge_slices(height: int, width: int, dy: int, dx: int) -> tuple[slice, ...]:
    y_a, y_b = (slice(0, height - dy), slice(dy, height)) if dy >= 0 else (slice(-dy, height), slice(0, height + dy))
    x_a, x_b = (slice(0, width - dx), slice(dx, width)) if dx >= 0 else (slice(-dx, width), slice(0, width + dx))
    return y_a, x_a, y_b, x_b


def _build_confusion_reference(
    original_lab: torch.Tensor,
    baseline_lab: torch.Tensor,
) -> tuple[list[dict[str, object]], torch.Tensor]:
    _, _, height, width = original_lab.shape
    original_a, original_b = original_lab[:, 1:2], original_lab[:, 2:3]
    baseline_a, baseline_b = baseline_lab[:, 1:2], baseline_lab[:, 2:3]
    references: list[dict[str, object]] = []
    density = torch.zeros((1, 1, height, width), device=original_lab.device)

    for dy, dx in SELECTION_PAIR_OFFSETS:
        slices = _edge_slices(height, width, dy, dx)
        y_a, x_a, y_b, x_b = slices
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
        collapse = torch.relu(original_distance - baseline_distance)
        relevance = original_distance / (original_distance + CONFUSION_DISTANCE_SCALE)
        weight = collapse / (original_distance + 1e-6) * relevance
        density[:, :, y_a, x_a] += 0.5 * weight
        density[:, :, y_b, x_b] += 0.5 * weight
        references.append({
            "slices": slices,
            "original_distance": original_distance,
            "baseline_distance": baseline_distance,
            "collapse": collapse,
            "weight": weight,
        })
    return references, density


def _candidate_confusion_score(
    candidate_lab: torch.Tensor,
    references: list[dict[str, object]],
) -> torch.Tensor:
    batch_size, _, height, width = candidate_lab.shape
    candidate_a, candidate_b = candidate_lab[:, 1:2], candidate_lab[:, 2:3]
    score_sum = torch.zeros((batch_size, 1, height, width), device=candidate_lab.device)
    weight_sum = torch.zeros_like(score_sum)

    for reference in references:
        y_a, x_a, y_b, x_b = reference["slices"]
        candidate_distance = torch.sqrt(
            (candidate_a[:, :, y_a, x_a] - candidate_a[:, :, y_b, x_b]) ** 2
            + (candidate_b[:, :, y_a, x_a] - candidate_b[:, :, y_b, x_b]) ** 2
            + 1e-8
        )
        recovered = torch.minimum(candidate_distance, reference["original_distance"])
        recovery = ((recovered - reference["baseline_distance"]) / (reference["collapse"] + 1e-6)).clamp(-1.0, 1.0)
        weight = reference["weight"]
        weighted = recovery * weight
        expanded = weight.expand(batch_size, -1, -1, -1)
        score_sum[:, :, y_a, x_a] += 0.5 * weighted
        score_sum[:, :, y_b, x_b] += 0.5 * weighted
        weight_sum[:, :, y_a, x_a] += 0.5 * expanded
        weight_sum[:, :, y_b, x_b] += 0.5 * expanded
    return torch.where(weight_sum > 1e-8, score_sum / (weight_sum + 1e-8), torch.zeros_like(score_sum))


@torch.inference_mode()
def apply_color_correction(
    original_bgr: np.ndarray,
    baseline_bgr: np.ndarray,
    cvd_type: str,
    severity: float,
    *,
    device: torch.device | str | None = None,
) -> CorrectionResult:
    """Apply the NB03 correction to an original image and its CVD baseline."""
    validate_cvd_parameters(cvd_type, severity)
    if original_bgr.shape != baseline_bgr.shape:
        raise ValueError("original_bgr and baseline_bgr must have identical shapes")
    if original_bgr.dtype != np.uint8 or original_bgr.ndim != 3 or original_bgr.shape[2] != 3:
        raise ValueError("images must be uint8 BGR arrays shaped (H, W, 3)")
    if float(severity) == 0.0:
        height, width = original_bgr.shape[:2]
        return CorrectionResult(
            original_bgr.copy(),
            0.0,
            0.0,
            0.0,
            np.zeros((height, width), dtype=np.float32),
        )

    active_device = torch.device(device) if device is not None else default_device()
    original_rgb = bgr_to_rgb_tensor(original_bgr, active_device)
    baseline_rgb = bgr_to_rgb_tensor(baseline_bgr, active_device)
    original_lab, baseline_lab = rgb_to_lab(original_rgb), rgb_to_lab(baseline_rgb)
    lightness, original_a, original_b = original_lab[:, 0:1], original_lab[:, 1:2], original_lab[:, 2:3]
    baseline_a, baseline_b = baseline_lab[:, 1:2], baseline_lab[:, 2:3]

    chromatic_loss = torch.sqrt((original_a - baseline_a) ** 2 + (original_b - baseline_b) ** 2 + 1e-8)
    loss_weight = smoothstep(LOSS_LOW, LOSS_HIGH, chromatic_loss)
    chroma = torch.sqrt(original_a ** 2 + original_b ** 2 + 1e-8)
    local_weight = (loss_weight * chroma / (chroma + CHROMA_SOFT_SCALE)).clamp(0.0, 1.0)
    lost_signal = torch.tanh((original_a - baseline_a) / LOST_A_SCALE)
    max_delta = (NATURALNESS_BASE + NATURALNESS_ERROR_RATIO * chromatic_loss).clamp(NATURALNESS_BASE, NATURALNESS_MAX_DELTA)
    baseline_error = delta_e76_map(original_lab, baseline_lab)
    references, density = _build_confusion_reference(original_lab, baseline_lab)
    positive_density = density[density > 0]
    density_scale = torch.quantile(positive_density, 0.95) if positive_density.numel() else torch.tensor(1.0, device=active_device)
    confusion_relevance = smoothstep(
        CONFUSION_RELEVANCE_LOW,
        CONFUSION_RELEVANCE_HIGH,
        (density / (density_scale + 1e-8)).clamp(0.0, 1.0),
    )

    _, _, height, width = original_lab.shape
    best_score = torch.zeros((1, 1, height, width), device=active_device)
    best_delta = torch.zeros_like(best_score)
    matrix = get_machado_matrix(cvd_type, severity, device=active_device)
    factors = torch.tensor([value for value in CANDIDATE_FACTORS if value != 0.0], device=active_device)

    for start in range(0, len(factors), CANDIDATE_BATCH_SIZE):
        batch_factors = factors[start : start + CANDIDATE_BATCH_SIZE]
        batch_size = batch_factors.numel()
        delta_b = batch_factors.view(batch_size, 1, 1, 1) * TRANSFER_B_MAX[cvd_type] * lost_signal * local_weight
        delta_b = torch.maximum(torch.minimum(delta_b, max_delta), -max_delta)
        candidate_lab = torch.cat([
            lightness.expand(batch_size, -1, -1, -1),
            original_a.expand(batch_size, -1, -1, -1),
            (original_b.expand(batch_size, -1, -1, -1) + delta_b).clamp(-127.0, 127.0),
        ], dim=1)
        candidate_seen_lab = rgb_to_lab(simulate_machado(lab_to_rgb(candidate_lab), matrix))
        confusion_score = _candidate_confusion_score(candidate_seen_lab, references)
        candidate_error = delta_e76_map(original_lab.expand(batch_size, -1, -1, -1), candidate_seen_lab)
        perceptual_recovery = ((baseline_error - candidate_error) / (baseline_error + 1e-6)).clamp(-1.0, 1.0)
        naturalness_cost = torch.abs(delta_b) / (max_delta + 1e-6)
        total_score = (
            OBJECTIVE_WEIGHTS["confusion"] * confusion_score
            + OBJECTIVE_WEIGHTS["perceptual_recovery"] * perceptual_recovery
            - OBJECTIVE_WEIGHTS["naturalness"] * naturalness_cost
        )
        batch_score, batch_index = total_score.max(dim=0, keepdim=True)
        batch_delta = torch.gather(delta_b, dim=0, index=batch_index)
        improved = batch_score > best_score
        best_score = torch.where(improved, batch_score, best_score)
        best_delta = torch.where(improved, batch_delta, best_delta)

    activation = confusion_relevance * smoothstep(MIN_USEFUL_SCORE, SCORE_CONFIDENCE_FULL, best_score)
    final_delta = best_delta * activation
    final_delta = gaussian_blur2d(final_delta, (FINAL_SMOOTH_KSIZE, FINAL_SMOOTH_KSIZE), (FINAL_SMOOTH_SIGMA, FINAL_SMOOTH_SIGMA))
    final_delta = torch.maximum(torch.minimum(final_delta, max_delta), -max_delta)
    corrected_lab = torch.cat([lightness, original_a, (original_b + final_delta).clamp(-127.0, 127.0)], dim=1)
    corrected_bgr = rgb_tensor_to_bgr(lab_to_rgb(corrected_lab))

    magnitude_map = torch.abs(final_delta)[0, 0].cpu().numpy()
    return CorrectionResult(
        image_bgr=corrected_bgr,
        corrected_pixel_pct=float((magnitude_map > CORRECTED_DELTA_B_THRESHOLD).mean() * 100.0),
        strongly_corrected_pixel_pct=float((magnitude_map > STRONG_CORRECTION_DELTA_B_THRESHOLD).mean() * 100.0),
        mean_abs_delta_b=float(magnitude_map.mean()),
        magnitude_map=magnitude_map,
    )
