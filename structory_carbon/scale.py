"""Modèle coût + carbone à l'échelle de N organisations (docs/MODELE_COUT_CARBONE.md).

Équations (par an, scénario s ∈ {bas, central, haut}) :

  SaaS  : C(N) = F_saas + N·c_données_saas + p_vcpu·8760·max(0, N·v − V0)
          avec v = org_share·V0 (vCPU permanents par organisation), V0 = vCPU du socle.
  BYOS  : C(N) = α·P_vps + N·c_données_byos(=0) + P_vps·ceil(max(0, N·h − H0) / H_vps)
          avec H_vps = vcpu_vps·8760·u_max, H0 = α·H_vps, α = RAM de production / RAM du VPS.
  Carbone : même structure, coûts remplacés par kgCO2e (énergie × PUE × CI + fabrication).
"""

from __future__ import annotations

import csv
import io
import math
from typing import Any

from .factors import FactorSet
from .model import HOURS_PER_YEAR, SCENARIOS, ProfileError, Resolver, _vcpu_power_w, compute_once

COST_POSTES = ("stockage", "replication_sauvegardes", "compute", "reseau_egress",
               "infrastructure", "exploitation")
DEFAULT_SIZES = [1, 1000, 10000, 100000]


def _optional(section: dict[str, Any], name: str, r: Resolver, path: str) -> float | None:
    raw = section.get(name)
    if raw is None:
        return None
    if isinstance(raw, dict) and all(raw.get(s) is None for s in SCENARIOS):
        return None
    return r(section, name, path)


def scale_once(profile: dict[str, Any], factors: FactorSet, prices: FactorSet,
               scenario: str, n_orgs: int) -> dict[str, Any]:
    if n_orgs < 1:
        raise ProfileError("Le nombre d'organisations doit être ≥ 1")
    ech = profile.get("echelle")
    if not ech:
        raise ProfileError("Section `echelle` absente du profil")
    es, eb = ech["saas"], ech["byos"]
    saas = profile["saas"]

    per_org = compute_once(profile, factors, scenario)
    rf = Resolver(factors, scenario)          # facteurs d'impact + hypothèses
    rp = Resolver(prices, scenario)           # prix + hypothèses
    used: dict[str, Any] = {}

    # ------------------------------------------------------------------ SaaS
    envs = saas["environments"]
    price_keys = es["prix_instances"]
    if len(price_keys) != len(envs):
        raise ProfileError("echelle.saas.prix_instances : un prix par environnement de saas.environments")
    v0 = sum(float(e["vcpu"]) for e in envs)
    share = rf(saas, "org_share", "saas")
    v_org = share * v0
    extra_vcpu = max(0.0, n_orgs * v_org - v0)

    socle_eur = sum(prices.value(k) * HOURS_PER_YEAR for k in price_keys)
    lb_eur = rp(es, "load_balancers", "echelle.saas") * rp(es, "prix_load_balancer", "echelle.saas") * 12
    vol = per_org["volumes_cout_gb"]
    p_block = prices.value("ovh_block_high_speed_month") * 12
    p_backup = prices.value("ovh_volume_backup_hour") * HOURS_PER_YEAR
    p_obj = prices.value("ovh_object_standard_hour") * HOURS_PER_YEAR
    vd = vol["saas_bloc_base"]  # copie de base ; vol["saas_bloc"] = vd·R_db·(1+n_env)
    egress_gb = rp(es, "egress_gb_par_org", "echelle.saas")
    p_egress = rp(es, "prix_egress", "echelle.saas")
    expl_saas = _optional(es, "exploitation_eur_an", rp, "echelle.saas")

    saas_cost = {
        "stockage": n_orgs * (vd * p_block + vol["saas_objet"] * p_obj),
        "replication_sauvegardes": n_orgs * ((vol["saas_bloc"] - vd) * p_block
                                             + vol["saas_sauvegarde"] * p_backup),
        "compute": socle_eur + extra_vcpu * prices.value("ovh_vcpu_hour") * HOURS_PER_YEAR,
        "reseau_egress": n_orgs * egress_gb * p_egress,
        "infrastructure": lb_eur,
        "exploitation": expl_saas,
    }
    saas_fixed = socle_eur + lb_eur + (expl_saas or 0.0)

    # carbone SaaS : socle (environnements à leur utilisation) + capacité ajoutée + données
    s_ci = rf(saas, "grid", "saas")
    s_pue = rf(saas, "pue", "saas")
    mem_coef = rf.factor("memory_energy")
    ef_vcpu = rf.factor("embodied_vcpu_year_aws_t3_medium")
    socle_kwh = sum(
        float(e["vcpu"]) * _vcpu_power_w(rf, float(e["utilization"])) * HOURS_PER_YEAR / 1000
        + float(e["memory_gb"]) * mem_coef * HOURS_PER_YEAR for e in envs)
    u_add = rf(es, "utilisation_capacite_ajoutee", "echelle.saas")
    mem_vcpu = rf(es, "memoire_par_vcpu_gb", "echelle.saas")
    extra_kwh = extra_vcpu * (_vcpu_power_w(rf, u_add) * HOURS_PER_YEAR / 1000
                              + mem_vcpu * mem_coef * HOURS_PER_YEAR)
    saas_co2_fixed = socle_kwh * s_pue * s_ci + v0 * ef_vcpu
    saas_co2 = (saas_co2_fixed + extra_kwh * s_pue * s_ci + extra_vcpu * ef_vcpu
                + n_orgs * per_org["donnees_kgco2e"]["saas"])

    # ------------------------------------------------------------------ BYOS
    p_vps = rp(eb, "prix_vps", "echelle.byos") * 12
    vps_vcpu = rp(eb, "vps_vcpu", "echelle.byos")
    vps_ram = rp(eb, "vps_ram_gb", "echelle.byos")
    ram_prod = rp(eb, "ram_production_gb", "echelle.byos")
    alpha = min(1.0, ram_prod / vps_ram)
    u_max = rp(eb, "utilisation_max", "echelle.byos")
    h_org = rf(profile["byos"], "vcpu_hours_per_year", "byos")
    h_vps = vps_vcpu * HOURS_PER_YEAR * u_max
    need = n_orgs * h_org
    extra_vps = math.ceil(max(0.0, need - alpha * h_vps) / h_vps)
    expl_byos = _optional(eb, "exploitation_eur_an", rp, "echelle.byos")
    stockage_suffisant = bool(ech.get("organisation", {}).get("stockage_existant_suffisant", True))

    byos_cost = {
        "stockage": 0.0,                 # données dans le stockage de l'organisation
        "replication_sauvegardes": 0.0,  # celles du stockage de l'organisation, préexistantes
        "compute": alpha * p_vps + extra_vps * p_vps,
        "reseau_egress": 0.0,            # trafic VPS illimité inclus dans le prix (source prices.yaml)
        "infrastructure": 0.0,           # pas de load balancer : hypothèse documentée
        "exploitation": expl_byos,
    }
    byos_fixed = alpha * p_vps + (expl_byos or 0.0)
    org_marginal = 0.0 if stockage_suffisant else vol["byos_journal"] * p_obj

    b_ci = rf(eb, "grid", "echelle.byos")
    b_pue = rf(eb, "pue", "echelle.byos")
    alloc_vcpu = alpha * vps_vcpu + extra_vps * vps_vcpu
    alloc_ram = alpha * vps_ram + extra_vps * vps_ram
    u_load = min(u_max, need / (alloc_vcpu * HOURS_PER_YEAR))
    byos_kwh = (alloc_vcpu * _vcpu_power_w(rf, u_load) * HOURS_PER_YEAR / 1000
                + alloc_ram * mem_coef * HOURS_PER_YEAR)
    byos_co2_fixed_socle = (alpha * vps_vcpu * _vcpu_power_w(rf, 0.0) * HOURS_PER_YEAR / 1000
                            + alpha * vps_ram * mem_coef * HOURS_PER_YEAR) * b_pue * b_ci \
        + alpha * vps_vcpu * ef_vcpu
    byos_co2 = (byos_kwh * b_pue * b_ci + alloc_vcpu * ef_vcpu
                + n_orgs * per_org["donnees_kgco2e"]["byos"])

    def tot(d: dict[str, float | None]) -> float:
        return sum(v for v in d.values() if v is not None)

    used.update(rf.used)
    used.update(rp.used)
    saas_total, byos_total = tot(saas_cost), tot(byos_cost)
    return {
        "scenario": scenario,
        "n_orgs": n_orgs,
        "saas": {
            "cout_eur": {**saas_cost, "total": saas_total, "fixe": saas_fixed,
                         "variable": saas_total - saas_fixed, "par_org": saas_total / n_orgs},
            "kgco2e": {"total": saas_co2, "fixe_socle": saas_co2_fixed,
                       "par_org": saas_co2 / n_orgs},
            "vcpu_permanents": v0 + extra_vcpu,
        },
        "byos": {
            "cout_eur": {**byos_cost, "total": byos_total, "fixe": byos_fixed,
                         "variable": byos_total - byos_fixed, "par_org": byos_total / n_orgs},
            "kgco2e": {"total": byos_co2, "fixe_socle_au_repos": byos_co2_fixed_socle,
                       "par_org": byos_co2 / n_orgs},
            "vps_supplementaires": extra_vps,
            "part_vps_socle": alpha,
            "cout_marginal_organisation_eur": org_marginal,
        },
        "ecart_cout_eur": saas_total - byos_total,
        "evite_kgco2e": saas_co2 - byos_co2,
        "exploitation_chiffree": expl_saas is not None and expl_byos is not None,
        "parametres": used,
    }


def scale(profile: dict[str, Any], factors: FactorSet, prices: FactorSet,
          sizes: list[int] | None = None) -> dict[str, list[dict[str, Any]]]:
    sizes = sizes or profile.get("echelle", {}).get("tailles") or DEFAULT_SIZES
    return {s: [scale_once(profile, factors, prices, s, n) for n in sizes] for s in SCENARIOS}


CSV_COLUMNS = [
    "scenario", "organisations",
    "saas_cout_eur_an", "byos_cout_eur_an", "ecart_cout_eur_an",
    "saas_cout_par_org_eur_an", "byos_cout_par_org_eur_an",
    "saas_tco2e_an", "byos_tco2e_an", "evite_tco2e_an",
    "byos_cout_marginal_org_eur_an", "exploitation_chiffree",
]


def to_csv(results: dict[str, list[dict[str, Any]]]) -> str:
    """CSV « ; » avec virgule décimale (collage direct dans un tableur réglé en français)."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\n")
    w.writerow(CSV_COLUMNS)
    for s in SCENARIOS:
        for r in results[s]:
            w.writerow([str(c).replace(".", ",") for c in [
                s, r["n_orgs"],
                f"{r['saas']['cout_eur']['total']:.2f}", f"{r['byos']['cout_eur']['total']:.2f}",
                f"{r['ecart_cout_eur']:.2f}",
                f"{r['saas']['cout_eur']['par_org']:.4f}", f"{r['byos']['cout_eur']['par_org']:.4f}",
                f"{r['saas']['kgco2e']['total'] / 1000:.6f}", f"{r['byos']['kgco2e']['total'] / 1000:.6f}",
                f"{r['evite_kgco2e'] / 1000:.6f}",
                f"{r['byos']['cout_marginal_organisation_eur']:.4f}",
                "oui" if r["exploitation_chiffree"] else "non",
            ]])
    return buf.getvalue()


def _f(x: float, nd: int = 0) -> str:
    s = f"{x:,.{nd}f}".replace(",", " ")
    return s.replace(".", ",")


def to_markdown(results: dict[str, list[dict[str, Any]]], factors: FactorSet,
                prices: FactorSet) -> str:
    L = ["# Coût et carbone à l'échelle — BYOS + Structory face à un SaaS de référence", "",
         f"Facteurs `{factors.version}` · prix `{prices.version}` (EUR HT, catalogue public "
         "OVHcloud FR) · équations : docs/MODELE_COUT_CARBONE.md", "",
         "> Coût vu de l'**éditeur**. Le poste **exploitation** (personnes) n'est pas chiffré "
         "(prix À SOURCER) : les totaux ne couvrent que l'infrastructure. Le coût marginal pour "
         "l'organisation BYOS est donné à part.", ""]
    for s in SCENARIOS:
        L += [f"## Scénario {s}", "",
              "| Organisations | Coût SaaS (€/an) | Coût BYOS (€/an) | SaaS €/org | BYOS €/org "
              "| tCO2e SaaS | tCO2e BYOS | tCO2e évitées |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in results[s]:
            L.append(
                f"| {_f(r['n_orgs'])} | {_f(r['saas']['cout_eur']['total'])} | "
                f"{_f(r['byos']['cout_eur']['total'])} | {_f(r['saas']['cout_eur']['par_org'], 2)} | "
                f"{_f(r['byos']['cout_eur']['par_org'], 4)} | "
                f"{_f(r['saas']['kgco2e']['total'] / 1000, 3)} | "
                f"{_f(r['byos']['kgco2e']['total'] / 1000, 3)} | {_f(r['evite_kgco2e'] / 1000, 3)} |")
        last = results[s][-1]
        L += ["", f"À {_f(last['n_orgs'])} organisations : {_f(last['saas']['vcpu_permanents'])} "
              f"vCPU permanents côté SaaS ; côté BYOS, part du VPS socle "
              f"{_f(last['byos']['part_vps_socle'], 2)} + {last['byos']['vps_supplementaires']} VPS "
              "supplémentaire(s). Coût marginal pour une organisation BYOS : "
              f"{_f(last['byos']['cout_marginal_organisation_eur'], 2)} €/an.", ""]
    return "\n".join(L)
