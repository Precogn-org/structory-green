"""CLI : structory-green <profil.yaml> [--out DOSSIER] [--factors FICHIER]."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from .factors import DEFAULT_FACTORS_PATH, MissingFactorError, load_factors
from .model import ProfileError
from .report import build_report, to_markdown


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="structory-green",
        description="Estime le CO2e évité par BYOS + Structory face à un SaaS de référence.",
    )
    ap.add_argument("profile", type=Path, help="profil d'organisation (YAML)")
    ap.add_argument("--out", type=Path, default=Path("."), help="dossier de sortie (défaut : .)")
    ap.add_argument("--factors", type=Path, default=DEFAULT_FACTORS_PATH,
                    help="fichier de facteurs (défaut : factors/factors.yaml)")
    args = ap.parse_args(argv)

    try:
        with open(args.profile, encoding="utf-8") as fh:
            profile = yaml.safe_load(fh)
        factors = load_factors(args.factors)
        rep = build_report(profile, factors)
    except (ProfileError, MissingFactorError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    stem = args.profile.stem
    json_path = args.out / f"{stem}_rapport.json"
    md_path = args.out / f"{stem}_rapport.md"
    json_path.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(to_markdown(rep), encoding="utf-8")

    f = rep["fourchette_evite_kgco2e"]
    print(f"CO2e évité (kg/an) — bas {f['bas']:.3g} · central {f['central']:.3g} · "
          f"haut {f['haut']:.3g}")
    print(f"Rapports : {md_path} ; {json_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
