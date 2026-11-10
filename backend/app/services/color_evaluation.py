"""Pixel-wise CIEDE2000 evaluation matching NB03, without plotting state."""
import cv2
import numpy as np
from skimage.color import deltaE_ciede2000


def _bgr_to_lab(bgr: np.ndarray) -> np.ndarray:
    """Restore CIELAB coordinates from OpenCV's uint8 Lab encoding, as in NB03."""
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float64)
    lab[:, :, 0] *= 100.0 / 255.0
    lab[:, :, 1:] -= 128.0
    return lab


def delta_e00_map(original_bgr: np.ndarray, simulated_bgr: np.ndarray) -> np.ndarray:
    """Compare uint8 BGR pairs in CIELAB; process strips to bound working memory."""
    if original_bgr.shape != simulated_bgr.shape:
        raise ValueError("Dimensi citra evaluasi harus sama")
    if original_bgr.dtype != np.uint8 or simulated_bgr.dtype != np.uint8:
        raise ValueError("Citra evaluasi harus menggunakan BGR uint8")
    differences = np.empty(original_bgr.shape[:2], dtype=np.float64)
    for start in range(0, original_bgr.shape[0], 128):
        stop = start + 128
        original = _bgr_to_lab(original_bgr[start:stop])
        simulated = _bgr_to_lab(simulated_bgr[start:stop])
        differences[start:stop] = deltaE_ciede2000(original, simulated)
    return differences


def render_delta_e00_heatmap(differences: np.ndarray, scale_max: float) -> np.ndarray:
    """Render a BGR Viridis map with a shared, zero-based experiment scale."""
    normalized = differences / scale_max if scale_max > 0 else np.zeros_like(differences)
    levels = np.rint(np.clip(normalized, 0, 1) * 255).astype(np.uint8)
    return cv2.applyColorMap(levels, cv2.COLORMAP_VIRIDIS)
