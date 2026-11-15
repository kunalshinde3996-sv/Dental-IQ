"""Single source of truth for turning free-text diagnoses + tooth findings into disease categories.

Every analytics number (population dashboard, insights, risk-model labels) uses these
definitions, so figures are consistent across pages.
"""
import re
from collections.abc import Iterable

from app.models.enums import ToothCondition

# Category -> (diagnosis regex, tooth-finding conditions that also imply it)
_CATEGORY_RULES: dict[str, tuple[re.Pattern[str] | None, frozenset[ToothCondition]]] = {
    "caries": (re.compile(r"caries|carious|pulpitis|decayed", re.I), frozenset({ToothCondition.caries})),
    "periodontal": (re.compile(r"gingivitis|periodontitis", re.I), frozenset()),
    "osmf": (re.compile(r"submucous fibrosis|\bOSMF\b", re.I), frozenset()),
    "leukoplakia": (re.compile(r"leukoplakia", re.I), frozenset()),
    "suspicious_malignancy": (re.compile(r"suspicious for malignancy|malignan", re.I), frozenset()),
    "edentulism": (re.compile(r"edentulous", re.I), frozenset({ToothCondition.missing})),
    "malocclusion": (re.compile(r"malocclusion", re.I), frozenset()),
    "soft_tissue_lesion": (re.compile(r"oral lesion|ulcer", re.I), frozenset({ToothCondition.lesion})),
}

#: Potentially malignant disorders (incl. lesions suspicious for malignancy).
PMD_PARTS = ("osmf", "leukoplakia", "suspicious_malignancy")

CATEGORY_LABELS: dict[str, str] = {
    "caries": "Dental caries",
    "periodontal": "Periodontal disease",
    "pmd": "Potentially malignant disorder (OSMF / leukoplakia / suspicious lesion)",
    "osmf": "Oral submucous fibrosis",
    "leukoplakia": "Leukoplakia",
    "oral_lesion": "Any oral mucosal lesion",
    "edentulism": "Edentulism / missing teeth",
    "malocclusion": "Malocclusion",
}


def categorize(diagnosis: str | None, conditions: Iterable[ToothCondition]) -> set[str]:
    """Return the set of disease categories implied by one case."""
    conds = set(conditions)
    text = diagnosis or ""
    found = {
        cat
        for cat, (pattern, implied) in _CATEGORY_RULES.items()
        if (pattern is not None and pattern.search(text)) or (conds & implied)
    }
    if found & set(PMD_PARTS):
        found.add("pmd")
    if "pmd" in found or "soft_tissue_lesion" in found:
        found.add("oral_lesion")
    found.discard("soft_tissue_lesion")
    return found


def is_pmd_diagnosis(diagnosis: str | None) -> bool:
    return "pmd" in categorize(diagnosis, ())
