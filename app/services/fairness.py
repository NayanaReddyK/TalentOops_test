"""Demographic k-anonymity fairness calculation module (k >= 5)."""
from __future__ import annotations

from typing import Any

DRIFT_THRESHOLD = 0.75


def calculate_k_anonymity(cohorts: dict[tuple[str, str], list[float]], k: int = 5) -> dict[str, Any]:
    """Calculate k-anonymity cells and drift alerts.
    
    Any cohort with fewer than k members (n < k) is suppressed to prevent PII exposure.
    """
    all_diffs: list[float] = []
    for diffs in cohorts.values():
        all_diffs.extend(diffs)
    overall = sum(all_diffs) / len(all_diffs) if all_diffs else 0.0

    cells: list[dict[str, Any]] = []
    drift_alerts: list[dict[str, Any]] = []

    for (dimension, value), diffs in sorted(cohorts.items()):
        n = len(diffs)
        if n < k:  # k-anonymity suppression rule
            cells.append({
                "dimension": dimension,
                "value": value,
                "n": None,
                "mean_difficulty": None,
                "suppressed": True,
            })
            continue

        mean = sum(diffs) / n
        cells.append({
            "dimension": dimension,
            "value": value,
            "n": n,
            "mean_difficulty": round(mean, 3),
            "suppressed": False,
        })
        if abs(mean - overall) > DRIFT_THRESHOLD:
            drift_alerts.append({
                "dimension": dimension,
                "value": value,
                "mean_difficulty": round(mean, 3),
                "overall_mean": round(overall, 3),
            })

    return {
        "overall_mean": round(overall, 3),
        "cells": cells,
        "drift_alerts": drift_alerts,
    }
