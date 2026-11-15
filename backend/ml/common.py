"""Shared helpers: artifact persistence (cached by mtime) and evaluation metrics."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.metrics import precision_score, recall_score, roc_auc_score

from app.core.config import artifact_dir

_cache: dict[str, tuple[float, Any]] = {}


def artifact_path(name: str) -> Path:
    return artifact_dir() / f"{name}.joblib"


def save_bundle(name: str, bundle: dict) -> Path:
    path = artifact_path(name)
    joblib.dump(bundle, path)
    _cache.pop(name, None)
    return path


def load_bundle(name: str) -> dict | None:
    """Load a trained model bundle, re-reading it only when the file changes."""
    path = artifact_path(name)
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    cached = _cache.get(name)
    if cached and cached[0] == mtime:
        return cached[1]
    bundle = joblib.load(path)
    _cache[name] = (mtime, bundle)
    return bundle


def sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-z))


def threshold_metrics(y: np.ndarray, prob: np.ndarray, threshold: float) -> dict:
    pred = (prob >= threshold).astype(int)
    return {
        "threshold": threshold,
        "precision": round(float(precision_score(y, pred, zero_division=0)), 3),
        "recall": round(float(recall_score(y, pred, zero_division=0)), 3),
        "flagged": int(pred.sum()),
        "true_positives": int(((pred == 1) & (y == 1)).sum()),
    }


def auc(y: np.ndarray, prob: np.ndarray) -> float | None:
    return round(float(roc_auc_score(y, prob)), 3) if len(set(y.tolist())) == 2 else None
