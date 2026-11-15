"""Light, explainable ML for Dental-IQ (Phase 2).

- oral_risk:   logistic-regression oral-cancer / PMD risk screening per patient
- student_risk: hybrid rules + logistic regression at-risk student alerts
- train:       CLI that trains both, saves artifacts and writes docs/ml-report.md

All models are trained on SYNTHETIC data and are for demonstration only.
"""

import warnings

# scikit-learn 1.6 passes a deprecated `iprint` option to newer SciPy's L-BFGS; harmless noise.
warnings.filterwarnings("ignore", message="Unknown solver options: iprint")
