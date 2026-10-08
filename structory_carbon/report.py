"""Construction des rapports JSON et Markdown."""

from __future__ import annotations

from typing import Any

from . import __version__
from .factors import FactorSet
from .model import POSTES, SCENARIOS, compute, sensitivity

POSTE_LABELS = {
    "stockage": "Stockage (copie de base)",
    "replication_sauvegardes": "Réplication et sauvegardes",
    "environnements": "Environnements hors production",
    "compute": "Compute (usage)",
    "reseau": "Réseau inter-centres",
    "fabrication": "Fabrication (embodied)",
}

DEFAULT_SHARE_VALUES = [0.0001, 0.001, 0.005, 0.02, 0.1, 1.0]


def build_report(profile: dict[str, Any], factors: FactorSet) -> dict[str, Any]:
    results = compute(profile, factors)
    sens_values = (profile.get("sensibilite") or {}).get("org_share", DEFAULT_SHARE_VALUES)
    sens = sensitivity(profile, factors, "saas.org_share", sens_values)

    used_factors = sorted({p["factor"] for res in results.values()
                           for p in res["parametres"].values() if p["kind"] == "FACTEUR"})
    hypotheses: dict[str, dict[str, float]] = {}
    for scen in SCENARIOS:
        for name, p in results[scen]["parametres"].items():
            if p["kind"] == "HYPOTHESE":
                hypotheses.setdefault(name, {})[scen] = p["value"]

    return {
        "outil": "structory-carbon",
        "version_outil": __version__,
        "version_facteurs": factors.version,
        "organisation": profile.get("organisation", "(sans nom)"),
        "unite": "kgCO2e/an",
        "fourchette_evite_kgco2e": {s: results[s]["evite_kgco2e"]["total"] for s in SCENARIOS},
        "resultats": results,
        "sensibilite_org_share": sens,
        "hypotheses": hypotheses,
        "facteurs_utilises": {
            k: {"value": factors.get(k).value, "min": factors.get(k).min, "max": factors.get(k).max,
                "unit": factors.get(k).unit, "status": factors.get(k).status,
                "source": factors.get(k).source, "url": factors.get(k).url,
                "accessed": factors.get(k).accessed}
            for k in used_factors
        },
        "facteurs_a_sourcer": factors.a_sourcer(),
        "notes_profil": profile.get("notes", []),
    }


def _fmt(x: float) -> str:
    if x == 0:
        return "0"
    if abs(x) >= 100:
        return f"{x:,.0f}".replace(",", " ")
    if abs(x) >= 1:
        return f"{x:.4g}"
    return f"{x:.3g}"


def to_markdown(rep: dict[str, Any]) -> str:
    f = rep["fourchette_evite_kgco2e"]
    res = rep["resultats"]
    L: list[str] = []
    L.append(f"# Rapport Structory Carbon — {rep['organisation']}")
    L.append("")
    L.append(f"Outil `structory-carbon` {rep['version_outil']} · facteurs version "
             f"`{rep['version_facteurs']}` · méthode : METHODOLOGIE.md (V0.1)")
    L.append("")
    L.append("## Résultat")
    L.append("")
    L.append("| CO2e évité par an | bas | central | haut |")
    L.append("|---|---:|---:|---:|")
    L.append(f"| kg CO2e / an | {_fmt(f['bas'])} | **{_fmt(f['central'])}** | {_fmt(f['haut'])} |")
    L.append("")
    sens = rep["sensibilite_org_share"]
    lo = min(r["evite_kgco2e"] for r in sens)
    hi = max(r["evite_kgco2e"] for r in sens)
    L.append("> **À lire avant de citer ce chiffre.** Le résultat par organisation est **petit** "
             f"(central : {_fmt(f['central'])} kg CO2e/an) et **très sensible** à une hypothèse non "
             f"observable (de {_fmt(lo)} à {_fmt(hi)} kg/an dans l'analyse ci-dessous) : la part des serveurs SaaS "
             "attribuée à l'organisation (`saas.org_share`). Voir l'analyse de sensibilité "
             "ci-dessous. La fourchette est un encadrement par scénarios, pas un intervalle de "
             "confiance (METHODOLOGIE.md §7).")
    L.append("")
    L.append("## Détail par poste (kg CO2e / an, scénario central)")
    L.append("")
    L.append("| Poste | SaaS | BYOS (marginal) | Évité |")
    L.append("|---|---:|---:|---:|")
    c = res["central"]
    for p in POSTES:
        L.append(f"| {POSTE_LABELS[p]} | {_fmt(c['saas_kgco2e'][p])} | "
                 f"{_fmt(c['byos_kgco2e'][p])} | {_fmt(c['evite_kgco2e'][p])} |")
    L.append(f"| **Total** | **{_fmt(c['saas_kgco2e']['total'])}** | "
             f"**{_fmt(c['byos_kgco2e']['total'])}** | **{_fmt(c['evite_kgco2e']['total'])}** |")
    L.append("")
    v = c["volumes_gb"]
    L.append(f"Volumes (central) : journal {_fmt(v['journal_annuel'])} Go/an, "
             f"{_fmt(v['journal_total'])} Go au total ; stockage physique SaaS "
             f"{_fmt(v['saas_physique'])} Go ; stockage marginal BYOS {_fmt(v['byos_physique_marginal'])} Go. "
             "Les pièces jointes déjà présentes dans le stockage de l'organisation ne sont pas "
             "imputées au BYOS (METHODOLOGIE.md §3.1).")
    L.append("")
    L.append("## Analyse de sensibilité : part des serveurs SaaS attribuée à l'organisation")
    L.append("")
    L.append("Scénario central, seul `saas.org_share` varie.")
    L.append("")
    L.append("| org_share | SaaS (kg/an) | BYOS (kg/an) | Évité (kg/an) |")
    L.append("|---:|---:|---:|---:|")
    for row in rep["sensibilite_org_share"]:
        L.append(f"| {row['valeur']:g} | {_fmt(row['saas_kgco2e'])} | {_fmt(row['byos_kgco2e'])} | "
                 f"{_fmt(row['evite_kgco2e'])} |")
    L.append("")
    L.append("Lecture : `1` = instance SaaS dédiée à l'organisation ; `0.001` = une instance "
             "partagée par 1 000 organisations. Seuls le compute SaaS permanent et la fabrication "
             "des serveurs qui le portent varient avec ce paramètre ; le stockage n'en dépend pas.")
    L.append("")
    L.append("## Hypothèses (HYPOTHESE = valeur du profil, non sourcée)")
    L.append("")
    L.append("Convention : `bas` = valeur qui donne le moins d'émissions évitées.")
    L.append("")
    L.append("| Paramètre | bas | central | haut |")
    L.append("|---|---:|---:|---:|")
    for name, vals in sorted(rep["hypotheses"].items()):
        cells = " | ".join(f"{vals[s]:g}" if s in vals else "" for s in SCENARIOS)
        L.append(f"| `{name}` | {cells} |")
    L.append("")
    if rep["notes_profil"]:
        L.append("Notes du profil :")
        L.append("")
        for n in rep["notes_profil"]:
            L.append(f"- {n}")
        L.append("")
    L.append("## Facteurs utilisés")
    L.append("")
    L.append("| Facteur | Valeur | Unité | Statut | Source |")
    L.append("|---|---:|---|---|---|")
    for k, fa in rep["facteurs_utilises"].items():
        val = _fmt(fa["value"])
        if fa["min"] is not None:
            val += f" ({_fmt(fa['min'])}–{_fmt(fa['max'])})"
        src = fa["source"].split("\n")[0]
        if len(src) > 90:
            src = src[:87] + "…"
        link = f"[lien]({fa['url']})" if fa["url"] else ""
        L.append(f"| `{k}` | {val} | {fa['unit']} | {fa['status']} | {src} {link} |")
    L.append("")
    L.append("## Facteurs À SOURCER (non utilisés tels quels)")
    L.append("")
    for k in rep["facteurs_a_sourcer"]:
        L.append(f"- `{k}`")
    L.append("")
    L.append("## Ce que ce rapport ne mesure pas")
    L.append("")
    L.append("Terminaux et réseau d'accès des utilisateurs, développement logiciel, fin de vie "
             "des équipements, autres impacts que le climat, effets rebond. Détail : "
             "METHODOLOGIE.md §3 et §8.")
    L.append("")
    return "\n".join(L)
