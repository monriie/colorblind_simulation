"""Research-aligned CVD simulation endpoints."""
import base64

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.middleware.rate_limit import limiter
from app.services.color_evaluation import render_delta_e00_heatmap
from app.services.simulation_service import method_metadata, simulate_experiment
from app.utils.image_io import decode_upload, encode_png

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


def _data_url(image_bgr) -> str:
    encoded = base64.b64encode(encode_png(image_bgr)).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@router.get("/method")
async def get_method() -> dict[str, object]:
    """Return the exact experiment configuration used by the API."""
    return method_metadata()


@router.post("/analyze")
@limiter.limit("10/minute")
async def analyze_simulation(
    request: Request,
    image: UploadFile = File(
        ..., description="JPEG, PNG, or WebP image, maximum 10 MB"
    ),
) -> dict[str, object]:
    """Generate all NB02 CVD type and severity combinations."""
    try:
        image_bgr = await decode_upload(image)
        results = simulate_experiment(image_bgr)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    heatmap_max = max(float(item.delta_e00.max()) for item in results)
    return {
        "original": _data_url(image_bgr),
        "heatmapScale": {"min": 0.0, "max": heatmap_max, "colormap": "viridis"},
        "width": int(image_bgr.shape[1]),
        "height": int(image_bgr.shape[0]),
        "method": method_metadata(),
        "results": [
            {
                "cvdType": item.cvd_type,
                "severity": item.severity,
                "image": _data_url(item.image_bgr),
                "deltaE00Heatmap": _data_url(render_delta_e00_heatmap(item.delta_e00, heatmap_max)),
                "metrics": {
                    "meanDeltaE00": item.mean_delta_e00,
                    "meanAbsRgbChange": item.mean_abs_rgb_change,
                    "changedPixelRatio": item.changed_pixel_ratio,
                    "clipLowRatio": item.clip_low_ratio,
                    "clipHighRatio": item.clip_high_ratio,
                    "clipAnyRatio": item.clip_any_ratio,
                },
                "matrix": item.matrix,
            }
            for item in results
        ],
    }

