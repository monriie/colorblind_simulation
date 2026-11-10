import cv2
import numpy as np
import torch
import kornia.color as color


def bgr_to_rgb_tensor(image_bgr, device):
    """Convert uint8 BGR image to RGB tensor [1, 3, H, W] in [0, 1]."""
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(rgb).to(
        device=device,
        dtype=torch.float32,
        non_blocking=True,
    )
    return tensor.permute(2, 0, 1).unsqueeze(0) / 255.0


def rgb_tensor_to_bgr(rgb_tensor):
    """Convert RGB tensor [1, 3, H, W] in [0, 1] to uint8 BGR."""
    rgb = (
        rgb_tensor[0]
        .detach()
        .clamp(0.0, 1.0)
        .permute(1, 2, 0)
        .cpu()
        .numpy()
    )
    rgb = np.clip(np.rint(rgb * 255.0), 0, 255).astype(np.uint8)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def rgb_to_lab(rgb_tensor):
    """Convert RGB tensor [N, 3, H, W] in [0, 1] to CIELAB."""
    return color.rgb_to_lab(rgb_tensor.clamp(0.0, 1.0))


def lab_to_rgb(lab_tensor):
    """Convert CIELAB tensor [N, 3, H, W] to RGB in [0, 1]."""
    return color.lab_to_rgb(lab_tensor).clamp(0.0, 1.0)


def delta_e76_map(lab_a, lab_b):
    """Return CIE76 distance map [N, 1, H, W]."""
    return torch.sqrt(
        torch.sum((lab_a - lab_b) ** 2, dim=1, keepdim=True) + 1e-8
    )


def smoothstep(edge_low, edge_high, values):
    """Smooth transition from 0 to 1."""
    scaled = (
        (values - edge_low) / (edge_high - edge_low + 1e-8)
    ).clamp(0.0, 1.0)
    return scaled * scaled * (3.0 - 2.0 * scaled)