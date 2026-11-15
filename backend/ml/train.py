"""Train all Dental-IQ models, save artifacts and (optionally) write docs/ml-report.md.

    cd backend
    python -m ml.train            # train + write report
    python -m ml.train --no-report
"""
from __future__ import annotations

import argparse
from pathlib import Path

from sqlmodel import Session

from app.database import engine
from ml import oral_risk
from ml.report import write_report

REPORT_PATH = Path(__file__).resolve().parents[2] / "docs" / "ml-report.md"


def train_all(report: bool = True, verbose: bool = True) -> dict:
    say = print if verbose else (lambda *_a, **_k: None)
    results: dict = {}
    with Session(engine) as session:
        results["oral_risk"] = oral_risk.train(session)
        m = results["oral_risk"]["metrics"]["cv5"]
        say(f"  oral_risk: n={results['oral_risk']['n_train']} (PMD+ {results['oral_risk']['n_positive']}) "
            f"CV AUC={m['auc']}  P/R@high={m['at_high']['precision']}/{m['at_high']['recall']}")

        try:
            from ml import student_risk
        except ImportError:  # added in a later step
            student_risk = None
        if student_risk is not None:
            results["student_risk"] = student_risk.train(session)
            ev = results["student_risk"]["evaluation"]
            if ev:
                say(f"  student_risk vs seeded ground truth: High alerts P/R = "
                    f"{ev['hybrid_high']['precision']}/{ev['hybrid_high']['recall']}, "
                    f"High+Medium P/R = {ev['hybrid']['precision']}/{ev['hybrid']['recall']}")

    if report:
        write_report(results, REPORT_PATH)
        say(f"  report written to {REPORT_PATH}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Dental-IQ ML models")
    parser.add_argument("--no-report", action="store_true", help="do not rewrite docs/ml-report.md")
    args = parser.parse_args()
    print("Training models on the current database (SYNTHETIC data)...")
    train_all(report=not args.no_report)
