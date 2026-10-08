"""Chargement des facteurs d'impact sourcés (factors/factors.yaml)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_FACTORS_PATH = Path(__file__).resolve().parent.parent / "factors" / "factors.yaml"

REQUIRED_FIELDS = ("value", "unit", "status", "source", "url", "accessed", "source_version")
STATUSES = ("SOURCE", "DERIVE", "A_SOURCER")


class MissingFactorError(ValueError):
    """Un facteur nécessaire au calcul est à `null` (statut A_SOURCER)."""


@dataclass(frozen=True)
class Factor:
    key: str
    value: float | None
    unit: str
    status: str
    source: str
    url: str | None
    accessed: str
    source_version: str | None
    min: float | None = None
    max: float | None = None

    @property
    def has_bounds(self) -> bool:
        return self.min is not None and self.max is not None


class FactorSet:
    def __init__(self, version: str, factors: dict[str, Factor]):
        self.version = version
        self.factors = factors

    def __contains__(self, key: str) -> bool:
        return key in self.factors

    def get(self, key: str) -> Factor:
        if key not in self.factors:
            raise KeyError(f"Facteur inconnu : {key!r}")
        return self.factors[key]

    def value(self, key: str, bound: str | None = None) -> float:
        """Valeur d'un facteur ; `bound` = 'min' | 'max' pour les facteurs bornés par leur source."""
        f = self.get(key)
        if f.value is None:
            raise MissingFactorError(
                f"Le facteur {key!r} est A_SOURCER (valeur null) : fournissez une hypothèse "
                f"explicite dans le profil au lieu de le référencer."
            )
        if bound == "min" and f.min is not None:
            return f.min
        if bound == "max" and f.max is not None:
            return f.max
        return f.value

    def a_sourcer(self) -> list[str]:
        return [k for k, f in self.factors.items() if f.status == "A_SOURCER"]


def load_factors(path: str | Path = DEFAULT_FACTORS_PATH) -> FactorSet:
    with open(path, encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh)
    factors: dict[str, Factor] = {}
    for key, d in raw["factors"].items():
        missing = [f for f in REQUIRED_FIELDS if f not in d]
        if missing:
            raise ValueError(f"Facteur {key!r} : champs manquants {missing}")
        if d["status"] not in STATUSES:
            raise ValueError(f"Facteur {key!r} : statut inconnu {d['status']!r}")
        if d["status"] == "A_SOURCER" and d["value"] is not None:
            raise ValueError(f"Facteur {key!r} : A_SOURCER doit avoir value: null")
        if d["status"] != "A_SOURCER" and d["value"] is None:
            raise ValueError(f"Facteur {key!r} : valeur null sans statut A_SOURCER")
        if d["status"] == "SOURCE" and not d.get("url"):
            raise ValueError(f"Facteur {key!r} : un facteur SOURCE doit avoir une URL")
        factors[key] = Factor(
            key=key,
            value=None if d["value"] is None else float(d["value"]),
            unit=d["unit"],
            status=d["status"],
            source=str(d["source"]).strip(),
            url=d.get("url"),
            accessed=str(d["accessed"]),
            source_version=d.get("source_version"),
            min=None if d.get("min") is None else float(d["min"]),
            max=None if d.get("max") is None else float(d["max"]),
        )
    return FactorSet(version=str(raw["version"]), factors=factors)
