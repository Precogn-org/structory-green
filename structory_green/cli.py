"""CLI : structory-green <profil.yaml> [--out DOSSIER] [--factors FICHIER]."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from .factors import DEFAULT_FACTORS_PATH, DEFAULT_PRICES_PATH, MissingFactorError, load_factors, load_prices
from .model import ProfileError
from .report import build_report, to_markdown
from . import scale as scale_mod


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="structory-green",
        description="Estime le CO2e évité par BYOS + Structory face à un SaaS de référence.",
    )
    ap.add_argument("profile", type=Path, help="profil d'organisation (YAML)")
    ap.add_argument("--out", type=Path, default=Path("."), help="dossier de sortie (défaut : .)")
    ap.add_argument("--factors", type=Path, default=DEFAULT_FACTORS_PATH,
                    help="fichier de facteurs (défaut : factors/factors.yaml)")
    ap.add_argument("--prices", type=Path, default=DEFAULT_PRICES_PATH,
                    help="fichier de prix (défaut : factors/prices.yaml)")
    ap.add_argument("--scale", type=str, default=None,
                    help="tailles à extrapoler, ex. 1,1000,10000,100000 (coût + carbone)")
    args = ap.parse_args(argv)
    sizes = None
    if args.scale:
        try:
            sizes = [int(x) for x in args.scale.split(",") if x.strip()]
        except ValueError:
            ap.error("--scale attend des entiers séparés par des virgules")

    try:
        with open(args.profile, encoding="utf-8") as fh:
            profile = yaml.safe_load(fh)
        factors = load_factors(args.factors)
        rep = build_report(profile, factors)
        sc = None
        if sizes is not None:
            prices = load_prices(args.prices)
            sc = scale_mod.scale(profile, factors, prices, sizes)
    except (ProfileError, MissingFactorError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    stem = args.profile.stem
    json_path = args.out / f"{stem}_rapport.json"
    md_path = args.out / f"{stem}_rapport.md"
    json_path.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(to_markdown(rep), encoding="utf-8")

    if sc is not None:
        (args.out / f"{stem}_echelle.json").write_text(
            json.dumps({"version_facteurs": factors.version, "version_prix": prices.version,
                        "resultats": sc}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (args.out / f"{stem}_echelle.csv").write_text(scale_mod.to_csv(sc), encoding="utf-8")
        (args.out / f"{stem}_echelle.md").write_text(
            scale_mod.to_markdown(sc, factors, prices), encoding="utf-8")
        print(f"Échelle : {args.out / (stem + '_echelle.md')} ; .json ; .csv")

    f = rep["fourchette_evite_kgco2e"]
    print(f"CO2e évité (kg/an) — bas {f['bas']:.3g} · central {f['central']:.3g} · "
          f"haut {f['haut']:.3g}")
    print(f"Rapports : {md_path} ; {json_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
