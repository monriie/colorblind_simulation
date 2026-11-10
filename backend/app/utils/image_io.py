"""Decode and encode helpers for image endpoints."""
from __future__ import annotations

import cv2
import numpy as np
from fastapi import UploadFile

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000


async def decode_upload(image: UploadFile) -> np.ndarray:
    contents = await image.read()
    if not contents:
        raise ValueError("File kosong")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise ValueError("Ukuran file melebihi 10 MB")
    image_bgr = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise ValueError("File bukan gambar JPG, PNG, atau WebP yang valid")
    if image_bgr.shape[0] * image_bgr.shape[1] > MAX_IMAGE_PIXELS:
        raise ValueError("Resolusi gambar terlalu besar; maksimum 16 megapiksel")
    return image_bgr


def encode_png(image_bgr: np.ndarray) -> bytes:
    """Preserve the evaluated pixel values in the displayed/downloaded image."""
    ok, buffer = cv2.imencode(".png", image_bgr)
    if not ok:
        raise ValueError("Gagal mengenkode gambar ke PNG")
    return buffer.tobytes()

