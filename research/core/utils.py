"""Shared audit helpers for the CVD simulation notebooks."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


def find_research_root(required_relative_path: str | Path) -> Path:
    """Resolve the project root from CVD_RESEARCH_ROOT or parent folders."""
    configured = os.getenv("CVD_RESEARCH_ROOT")
    candidates = [Path(configured)] if configured else []
    candidates.extend([Path.cwd(), *Path.cwd().parents])
    required = Path(required_relative_path)
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if (resolved / required).exists():
            return resolved
    raise FileNotFoundError(
        f"Project root containing '{required}' was not found. "
        "Set CVD_RESEARCH_ROOT before running the notebook."
    )


def ensure_directories(paths: Iterable[Path]) -> None:
    """Create required output directories."""
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def utc_timestamp() -> str:
    """Return an ISO-8601 timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(payload: dict, path: Path) -> None:
    """Write an auditable UTF-8 JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, allow_nan=False)


def validate_frame(
    frame: pd.DataFrame,
    composite_key: Sequence[str],
    *,
    allow_empty: bool = False,
) -> None:
    """Validate CSV contract: schema, unique key, non-null and finite values."""
    missing_columns = [column for column in composite_key if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"Missing composite-key columns: {missing_columns}")
    if frame.empty:
        if allow_empty:
            return
        raise ValueError("The report is empty.")
    if frame.isnull().any().any():
        columns = frame.columns[frame.isnull().any()].tolist()
        raise ValueError(f"Null values found in columns: {columns}")
    if frame.duplicated(list(composite_key)).any():
        raise ValueError(f"Duplicate composite key: {list(composite_key)}")
    numeric = frame.select_dtypes(include=[np.number])
    if not numeric.empty and not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("Non-finite numeric values found in the report.")


def write_csv(
    frame: pd.DataFrame,
    path: Path,
    composite_key: Sequence[str],
    *,
    allow_empty: bool = False,
) -> None:
    """Validate and write a CSV using a stable column order."""
    validate_frame(frame, composite_key, allow_empty=allow_empty)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    """Compute a reproducible file checksum."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
