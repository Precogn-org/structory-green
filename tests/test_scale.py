import json
import math
from pathlib import Path

import pytest
import yaml

from structory_green.cli import main
from structory_green.factors import MissingFactorError, load_factors, load_prices
from structory_green.model import ProfileError
from structory_green.scale import CSV_COLUMNS, scale, scale_once, to_csv

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "org_exemple.yaml"
H = 8760


@pytest.fixture(scope="module")
def factors():
    return load_factors()


@pytest.fixture(scope="module")
def prices():
    return load_prices()


@pytest.fixture
def profile():
    with open(EXAMPLE, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_prices_are_sourced_or_explicitly_missing(prices):
    for key, p in prices.factors.items():
        assert p.status in ("SOURCE", "DERIVE", "A_SOURCER"), key
        if p.status == "A_SOURCER":
            assert p.value is None
        else:
            assert p.value is not None and p.url, key
    assert prices.a_sourcer() == ["exploitation_hour"]
    with pytest.raises(MissingFactorError):
        prices.value("exploitation_hour")


def test_derived_vcpu_price(prices):
    assert prices.value("ovh_vcpu_hour") == pytest.approx(prices.value("ovh_b3_8_hour") / 2)


def test_saas_fixed_cost_hand_calculation(profile, factors, prices):
    """N = 1 : le compute SaaS = socle (b3-32 + b3-16) à l'année, pas de capacité ajoutée."""
    r = scale_once(profile, factors, prices, "central", 1)
    socle = (0.2046 + 0.1023) * H
    assert r["saas"]["cout_eur"]["compute"] == pytest.approx(socle)
    assert r["saas"]["cout_eur"]["infrastructure"] == pytest.approx(6.0 * 12)
    assert r["saas"]["cout_eur"]["fixe"] == pytest.approx(socle + 72)


def test_saas_variable_compute_equation(profile, factors, prices):
    """C_compute(N) = socle + p_vcpu·8760·max(0, N·org_share·V0 − V0)."""
    n = 10000
    r = scale_once(profile, factors, prices, "central", n)
    v0, share = 12, 0.005
    extra = max(0, n * share * v0 - v0)
    expected = (0.2046 + 0.1023) * H + extra * 0.0256 * H
    assert r["saas"]["cout_eur"]["compute"] == pytest.approx(expected)
    assert r["saas"]["vcpu_permanents"] == pytest.approx(v0 + extra)


def test_byos_vps_count_equation(profile, factors, prices):
    """VPS supplémentaires = ceil(max(0, N·h − α·H_vps) / H_vps)."""
    n = 100000
    r = scale_once(profile, factors, prices, "central", n)
    alpha = 2.892 / 7.751
    h_vps = 4 * H * 0.5
    expected = math.ceil(max(0, n * 10 - alpha * h_vps) / h_vps)
    assert r["byos"]["vps_supplementaires"] == expected
    assert r["byos"]["cout_eur"]["compute"] == pytest.approx((alpha + expected) * 6.49 * 12)


def test_byos_editor_has_no_storage_cost(profile, factors, prices):
    r = scale_once(profile, factors, prices, "central", 1000)
    for poste in ("stockage", "replication_sauvegardes", "reseau_egress", "infrastructure"):
        assert r["byos"]["cout_eur"][poste] == 0
    assert r["byos"]["cout_marginal_organisation_eur"] == 0


def test_org_marginal_cost_when_quota_exceeded(profile, factors, prices):
    profile["echelle"]["organisation"]["stockage_existant_suffisant"] = False
    r = scale_once(profile, factors, prices, "central", 1)
    assert r["byos"]["cout_marginal_organisation_eur"] > 0


def test_exploitation_not_invented(profile, factors, prices):
    r = scale_once(profile, factors, prices, "central", 1000)
    assert r["saas"]["cout_eur"]["exploitation"] is None
    assert r["exploitation_chiffree"] is False
    profile["echelle"]["saas"]["exploitation_eur_an"] = 1000
    profile["echelle"]["byos"]["exploitation_eur_an"] = 500
    r2 = scale_once(profile, factors, prices, "central", 1000)
    assert r2["exploitation_chiffree"] is True
    assert r2["saas"]["cout_eur"]["total"] == pytest.approx(r["saas"]["cout_eur"]["total"] + 1000)


def test_economies_of_scale(profile, factors, prices):
    res = scale(profile, factors, prices, [1, 1000, 10000, 100000])
    for s in ("bas", "central", "haut"):
        saas = [r["saas"]["cout_eur"]["par_org"] for r in res[s]]
        byos = [r["byos"]["cout_eur"]["par_org"] for r in res[s]]
        assert saas == sorted(saas, reverse=True)      # le socle SaaS s'amortit
        assert byos[0] > byos[-1]                       # le socle BYOS s'amortit aussi
        assert all(r["ecart_cout_eur"] > 0 and r["evite_kgco2e"] > 0 for r in res[s])


def test_scenarios_ordered_at_scale(profile, factors, prices):
    res = scale(profile, factors, prices, [100000])
    ev = [res[s][0]["evite_kgco2e"] for s in ("bas", "central", "haut")]
    gap = [res[s][0]["ecart_cout_eur"] for s in ("bas", "central", "haut")]
    assert ev == sorted(ev) and gap == sorted(gap)


def test_invalid_size(profile, factors, prices):
    with pytest.raises(ProfileError):
        scale_once(profile, factors, prices, "central", 0)


def test_csv_format(profile, factors, prices):
    text = to_csv(scale(profile, factors, prices, [1, 1000]))
    lines = text.strip().split("\n")
    assert lines[0].split(";") == CSV_COLUMNS
    assert len(lines) == 1 + 3 * 2
    assert "," in lines[1] and "." not in lines[1]     # virgule décimale


def test_cli_scale(tmp_path):
    assert main([str(EXAMPLE), "--out", str(tmp_path), "--scale", "1,1000"]) == 0
    data = json.loads((tmp_path / "org_exemple_echelle.json").read_text(encoding="utf-8"))
    assert [r["n_orgs"] for r in data["resultats"]["central"]] == [1, 1000]
    assert (tmp_path / "org_exemple_echelle.csv").exists()
    assert (tmp_path / "org_exemple_echelle.md").read_text(encoding="utf-8").startswith("# Structory Green")


def test_committed_scale_csv_is_up_to_date(profile, factors, prices):
    committed = (ROOT / "examples" / "org_exemple_echelle.csv").read_text(encoding="utf-8")
    assert committed == to_csv(scale(profile, factors, prices, [1, 1000, 10000, 100000]))
