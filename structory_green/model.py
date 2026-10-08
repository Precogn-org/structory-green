"""Modèle de calcul : CO2e évité = Σ_postes [E_SaaS − E_BYOS] (voir METHODOLOGIE.md §4)."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

from .factors import FactorSet

HOURS_PER_YEAR = 8760
SCENARIOS = ("bas", "central", "haut")
POSTES = ("stockage", "replication_sauvegardes", "environnements", "compute", "reseau", "fabrication")


class ProfileError(ValueError):
    """Profil d'organisation invalide ou hors du domaine de validité de la méthode."""


@dataclass
class Resolver:
    """Résout un paramètre du profil pour un scénario donné.

    Un paramètre peut être : un nombre (hypothèse), une chaîne (identifiant de facteur),
    ou un triplet {bas, central, haut} de nombres ou d'identifiants.
    """

    factors: FactorSet
    scenario: str
    bounds: dict[str, str] = field(default_factory=dict)
    overrides: dict[str, Any] = field(default_factory=dict)
    used: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __call__(self, section: dict[str, Any], name: str, path: str) -> float:
        full = f"{path}.{name}"
        if full in self.overrides:
            raw = self.overrides[full]
        elif name in section:
            raw = section[name]
        else:
            raise ProfileError(f"Paramètre manquant dans le profil : {full}")
        if isinstance(raw, dict):
            if set(raw) != set(SCENARIOS):
                raise ProfileError(f"{full} : un triplet doit avoir exactement les clés {SCENARIOS}")
            raw = raw[self.scenario]
        if isinstance(raw, bool):
            raise ProfileError(f"{full} : valeur booléenne inattendue")
        if isinstance(raw, (int, float)):
            self.used[full] = {"value": float(raw), "kind": "HYPOTHESE"}
            return float(raw)
        if isinstance(raw, str):
            bound = self.bounds.get(raw)
            v = self.factors.value(raw, bound)
            self.used[full] = {"value": v, "kind": "FACTEUR", "factor": raw, "bound": bound}
            return v
        raise ProfileError(f"{full} : type non pris en charge ({type(raw).__name__})")

    def factor(self, key: str) -> float:
        """Facteur utilisé directement par le modèle (pas un paramètre du profil)."""
        v = self.factors.value(key, self.bounds.get(key))
        self.used[f"facteur.{key}"] = {"value": v, "kind": "FACTEUR", "factor": key,
                                       "bound": self.bounds.get(key)}
        return v


def _storage_energy_key(media: str) -> str:
    if media == "ssd":
        return "storage_ssd_energy"
    if media == "hdd":
        return "storage_hdd_energy"
    raise ProfileError(f"Support de stockage inconnu : {media!r} (ssd | hdd)")


def _embodied_per_tb(r: Resolver, media: str) -> float:
    if media == "ssd":
        return r.factor("embodied_ssd_per_tb")
    # HDD : fabrication par disque / capacité moyenne — capacité A_SOURCER en V0.1.
    return r.factor("embodied_hdd_unit") / r.factor("hdd_capacity_datacenter")


def _vcpu_power_w(r: Resolver, utilization: float) -> float:
    wmin = r.factor("cpu_min_watts_aws")
    wmax = r.factor("cpu_max_watts_aws")
    if not 0 <= utilization <= 1:
        raise ProfileError("utilization doit être entre 0 et 1")
    return wmin + utilization * (wmax - wmin)


def compute_once(profile: dict[str, Any], factors: FactorSet, scenario: str,
                 bounds: dict[str, str] | None = None,
                 overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Un calcul complet pour un scénario et un choix de bornes de facteurs."""
    if scenario not in SCENARIOS:
        raise ValueError(scenario)
    r = Resolver(factors, scenario, bounds or {}, overrides or {})
    uf, saas, byos = profile["unite_fonctionnelle"], profile["saas"], profile["byos"]

    if byos.get("preexisting_storage") is not True:
        raise ProfileError(
            "byos.preexisting_storage doit valoir true : la méthode V0.1 n'impute que l'impact "
            "marginal sur un stockage préexistant (METHODOLOGIE.md §3.1 et §8.3)."
        )

    # --- unité fonctionnelle (Go)
    n = r(uf, "entries_per_month", "unite_fonctionnelle")
    b = r(uf, "bytes_per_entry", "unite_fonctionnelle")
    h = r(uf, "history_years", "unite_fonctionnelle")
    a = r(uf, "attachments_gb", "unite_fonctionnelle")
    a_new = r(uf, "attachments_new_gb_per_year", "unite_fonctionnelle")
    vj_year = n * 12 * b / 1e9
    vj = vj_year * h

    # --- SaaS
    s_ci = r(saas, "grid", "saas")
    s_pue = r(saas, "pue", "saas")
    s_media = saas.get("media", "ssd")
    k_d = r(saas, "derived_overhead", "saas")
    r_db = r(saas, "replication_db", "saas")
    r_bkp = r(saas, "replication_backup", "saas")
    r_obj = r(saas, "replication_objects", "saas")
    bcp = r(saas, "backup_copies", "saas")
    n_env = r(saas, "non_prod_env_copies", "saas")
    share = r(saas, "org_share", "saas")
    s_life = r(saas, "storage_lifetime_years", "saas")

    vd = vj * (1 + k_d)
    s_gb = {
        "stockage": vd + a,
        "replication_sauvegardes": vd * (r_db - 1) + vd * bcp * r_bkp + a * (r_obj - 1),
        "environnements": vd * r_db * n_env,
    }

    # --- BYOS
    b_ci = r(byos, "grid", "byos")
    b_pue = r(byos, "pue", "byos")
    b_media = byos.get("media", "ssd")
    r_byos = r(byos, "replication", "byos")
    b_life = r(byos, "storage_lifetime_years", "byos")
    b_gb = {
        "stockage": vj,  # pièces jointes préexistantes : non imputées
        "replication_sauvegardes": vj * (r_byos - 1),
        "environnements": 0.0,
    }

    def storage_use(gb: float, media: str, pue: float, ci: float) -> float:
        kwh = gb / 1000 * r.factor(_storage_energy_key(media)) * HOURS_PER_YEAR / 1000 * pue
        return kwh * ci

    saas_res = {k: storage_use(v, s_media, s_pue, s_ci) for k, v in s_gb.items()}
    byos_res = {k: storage_use(v, b_media, b_pue, b_ci) for k, v in b_gb.items()}

    # --- compute SaaS (permanent, mutualisé)
    mem_coef = r.factor("memory_energy")
    envs = saas.get("environments") or []
    if not envs:
        raise ProfileError("saas.environments : au moins un environnement est requis")
    s_kwh_compute, s_vcpu_years = 0.0, 0.0
    for i, env in enumerate(envs):
        p = f"saas.environments[{i}]"
        vcpu, mem, u = r(env, "vcpu", p), r(env, "memory_gb", p), r(env, "utilization", p)
        s_kwh_compute += (vcpu * _vcpu_power_w(r, u) * HOURS_PER_YEAR / 1000
                          + mem * mem_coef * HOURS_PER_YEAR)
        s_vcpu_years += vcpu
    saas_res["compute"] = s_kwh_compute * share * s_pue * s_ci
    s_vcpu_years *= share

    # --- compute BYOS (à la demande)
    hv = r(byos, "vcpu_hours_per_year", "byos")
    mpv = r(byos, "memory_gb_per_vcpu", "byos")
    bu = r(byos, "utilization", "byos")
    b_kwh_compute = hv * _vcpu_power_w(r, bu) / 1000 + hv * mpv * mem_coef
    byos_res["compute"] = b_kwh_compute * b_pue * b_ci
    b_vcpu_years = hv / HOURS_PER_YEAR

    # --- réseau inter-centres
    c_net = r.factor("network_inter_dc_energy")
    ingest = vj_year * (1 + k_d) + a_new
    saas_res["reseau"] = (ingest * (r_db - 1) + ingest * bcp) * c_net * s_ci
    byos_res["reseau"] = vj_year * (r_byos - 1) * c_net * b_ci

    # --- fabrication
    ef_vcpu = r.factor("embodied_vcpu_year_aws_t3_medium")
    s_tb = sum(s_gb.values()) / 1000
    b_tb = sum(b_gb.values()) / 1000
    saas_res["fabrication"] = s_tb * _embodied_per_tb(r, s_media) / s_life + s_vcpu_years * ef_vcpu
    byos_res["fabrication"] = b_tb * _embodied_per_tb(r, b_media) / b_life + b_vcpu_years * ef_vcpu

    saas_total = sum(saas_res[p] for p in POSTES)
    byos_total = sum(byos_res[p] for p in POSTES)
    return {
        "scenario": scenario,
        "bounds": dict(bounds or {}),
        "volumes_gb": {
            "journal_annuel": vj_year, "journal_total": vj,
            "saas_physique": sum(s_gb.values()), "byos_physique_marginal": sum(b_gb.values()),
        },
        "saas_kgco2e": {**saas_res, "total": saas_total},
        "byos_kgco2e": {**byos_res, "total": byos_total},
        "evite_kgco2e": {**{p: saas_res[p] - byos_res[p] for p in POSTES},
                         "total": saas_total - byos_total},
        "parametres": r.used,
    }


def _bounded_factor_keys(factors: FactorSet) -> list[str]:
    return [k for k, f in factors.factors.items() if f.has_bounds]


def compute(profile: dict[str, Any], factors: FactorSet,
            overrides: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Fourchette basse / centrale / haute (METHODOLOGIE.md §7)."""
    keys = _bounded_factor_keys(factors)
    if len(keys) > 8:
        raise ValueError("Trop de facteurs bornés pour l'énumération des combinaisons")
    out: dict[str, dict[str, Any]] = {}
    out["central"] = compute_once(profile, factors, "central", {}, overrides)
    for scen, pick in (("bas", min), ("haut", max)):
        runs = [compute_once(profile, factors, scen, dict(zip(keys, combo)), overrides)
                for combo in itertools.product(("min", "max"), repeat=len(keys))]
        out[scen] = pick(runs, key=lambda res: res["evite_kgco2e"]["total"])
    return out


def sensitivity(profile: dict[str, Any], factors: FactorSet, param: str,
                values: list[float]) -> list[dict[str, float]]:
    """Fait varier un paramètre (chemin complet, ex. 'saas.org_share') en scénario central."""
    rows = []
    for v in values:
        res = compute_once(profile, factors, "central", {}, {param: v})
        rows.append({"valeur": v, "evite_kgco2e": res["evite_kgco2e"]["total"],
                     "saas_kgco2e": res["saas_kgco2e"]["total"],
                     "byos_kgco2e": res["byos_kgco2e"]["total"]})
    return rows
