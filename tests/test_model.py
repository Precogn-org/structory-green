import copy
import json
from pathlib import Path

import pytest
import yaml

from structory_green.cli import main
from structory_green.factors import MissingFactorError, load_factors
from structory_green.model import POSTES, ProfileError, compute, compute_once, sensitivity
from structory_green.report import build_report, to_markdown

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "org_exemple.yaml"


@pytest.fixture(scope="module")
def factors():
    return load_factors()


@pytest.fixture
def profile():
    with open(EXAMPLE, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ------------------------------------------------------------------ facteurs

def test_every_factor_is_sourced_or_explicitly_missing(factors):
    for key, f in factors.factors.items():
        if f.status == "A_SOURCER":
            assert f.value is None, key
        else:
            assert f.value is not None and f.url, key


def test_a_sourcer_list(factors):
    assert set(factors.a_sourcer()) == {
        "replication_google_drive", "hdd_capacity_datacenter", "network_end_user_energy"}


def test_derived_ssd_factor_matches_formula(factors):
    v = 1000 / factors.value("ssd_density") * factors.value("embodied_ssd_die") \
        + factors.value("embodied_ssd_base")
    assert factors.value("embodied_ssd_per_tb") == pytest.approx(v, abs=0.01)


def test_missing_factor_is_never_invented(factors):
    with pytest.raises(MissingFactorError):
        factors.value("replication_google_drive")


# ------------------------------------------------------------------ modèle

def test_range_is_ordered_and_positive(profile, factors):
    res = compute(profile, factors)
    lo, c, hi = (res[s]["evite_kgco2e"]["total"] for s in ("bas", "central", "haut"))
    assert lo <= c <= hi
    assert c > 0


def test_totals_are_sum_of_postes(profile, factors):
    r = compute_once(profile, factors, "central")
    for side in ("saas_kgco2e", "byos_kgco2e", "evite_kgco2e"):
        assert r[side]["total"] == pytest.approx(sum(r[side][p] for p in POSTES))


def test_storage_hand_calculation(profile, factors):
    """Vérifie le poste stockage BYOS à la main (METHODOLOGIE.md §4.1)."""
    r = compute_once(profile, factors, "central")
    vj = 2000 * 12 * 1500 / 1e9 * 3                        # Go
    kwh = vj / 1000 * 1.2 * 8760 / 1000 * 1.09               # SSD, PUE Google, R=1
    assert r["byos_kgco2e"]["stockage"] == pytest.approx(kwh * 0.20990)


def test_preexisting_attachments_not_charged_to_byos(profile, factors):
    base = compute_once(profile, factors, "central")
    p2 = copy.deepcopy(profile)
    p2["unite_fonctionnelle"]["attachments_gb"] = 500
    more = compute_once(profile=p2, factors=factors, scenario="central")
    assert more["byos_kgco2e"]["total"] == pytest.approx(base["byos_kgco2e"]["total"])
    assert more["saas_kgco2e"]["total"] > base["saas_kgco2e"]["total"]


def test_refuses_without_preexisting_storage(profile, factors):
    profile["byos"]["preexisting_storage"] = False
    with pytest.raises(ProfileError):
        compute_once(profile, factors, "central")


def test_referencing_a_sourcer_factor_fails(profile, factors):
    profile["byos"]["replication"] = "replication_google_drive"
    with pytest.raises(MissingFactorError):
        compute_once(profile, factors, "central")


def test_hdd_embodied_requires_missing_capacity(profile, factors):
    profile["saas"]["media"] = "hdd"
    with pytest.raises(MissingFactorError):
        compute_once(profile, factors, "central")


def test_bad_triplet_rejected(profile, factors):
    profile["saas"]["backup_copies"] = {"bas": 1, "haut": 2}
    with pytest.raises(ProfileError):
        compute_once(profile, factors, "central")


def test_sensitivity_monotonic_in_org_share(profile, factors):
    rows = sensitivity(profile, factors, "saas.org_share", [0.001, 0.01, 0.1, 1.0])
    vals = [row["evite_kgco2e"] for row in rows]
    assert vals == sorted(vals)
    assert all(row["byos_kgco2e"] == pytest.approx(rows[0]["byos_kgco2e"]) for row in rows)


def test_bounded_factor_used_for_range(profile, factors):
    res = compute(profile, factors)
    assert res["bas"]["bounds"]["embodied_vcpu_year_aws_t3_medium"] in ("min", "max")


# ------------------------------------------------------------------ rapport et CLI

def test_report_labels_hypotheses_and_warning(profile, factors):
    rep = build_report(profile, factors)
    md = to_markdown(rep)
    assert "HYPOTHESE" in md
    assert "Analyse de sensibilité" in md
    assert "très sensible" in md
    assert "saas.org_share" in rep["hypotheses"]
    assert rep["version_facteurs"] == factors.version


def test_cli_writes_reports(tmp_path, capsys):
    code = main([str(EXAMPLE), "--out", str(tmp_path)])
    assert code == 0
    data = json.loads((tmp_path / "org_exemple_rapport.json").read_text(encoding="utf-8"))
    assert set(data["fourchette_evite_kgco2e"]) == {"bas", "central", "haut"}
    assert (tmp_path / "org_exemple_rapport.md").read_text(encoding="utf-8").startswith("# Rapport")
    assert "CO2e évité" in capsys.readouterr().out


def test_cli_error_exit_code(tmp_path, profile):
    profile["byos"]["preexisting_storage"] = False
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(profile, allow_unicode=True), encoding="utf-8")
    assert main([str(p), "--out", str(tmp_path)]) == 2


def test_committed_example_report_is_up_to_date(factors, profile):
    committed = json.loads((ROOT / "examples" / "org_exemple_rapport.json").read_text(encoding="utf-8"))
    fresh = build_report(profile, factors)
    assert committed["fourchette_evite_kgco2e"] == pytest.approx(fresh["fourchette_evite_kgco2e"])
