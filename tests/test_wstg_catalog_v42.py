from aotp.wstg.catalog import (
    EXPECTED_WSTG_V42_TEST_COUNT,
    WSTGAdapterFamily,
    WSTGAuthRequirement,
    WSTGSafetyTier,
    WSTG_V42_CATALOG,
)


def test_wstg_v42_catalog_contains_every_official_test_case():
    catalog = WSTG_V42_CATALOG

    assert len(catalog.cases()) == EXPECTED_WSTG_V42_TEST_COUNT == 97
    assert len(catalog.by_category("INFO")) == 10
    assert len(catalog.by_category("CONF")) == 11
    assert len(catalog.by_category("IDNT")) == 5
    assert len(catalog.by_category("ATHN")) == 10
    assert len(catalog.by_category("ATHZ")) == 4
    assert len(catalog.by_category("SESS")) == 9
    assert len(catalog.by_category("INPV")) == 19
    assert len(catalog.by_category("ERRH")) == 2
    assert len(catalog.by_category("CRYP")) == 4
    assert len(catalog.by_category("BUSL")) == 9
    assert len(catalog.by_category("CLNT")) == 13
    assert len(catalog.by_category("APIT")) == 1


def test_wstg_v42_catalog_preserves_official_ids_and_titles():
    catalog = WSTG_V42_CATALOG

    assert catalog.by_id("WSTG-v42-CLNT-01").title == "Testing for DOM-Based Cross Site Scripting"
    assert catalog.by_id("WSTG-v42-INPV-01").title == "Testing for Reflected Cross Site Scripting"
    assert catalog.by_id("WSTG-v42-INPV-05").title == "Testing for SQL Injection"
    assert catalog.by_id("WSTG-v42-ATHZ-02").title == "Testing for Bypassing Authorization Schema"
    assert catalog.by_id("WSTG-v42-APIT-01").title == "Testing GraphQL"


def test_wstg_catalog_has_engine_metadata_for_each_case():
    for test_case in WSTG_V42_CATALOG.cases():
        assert isinstance(test_case.safety_tier, WSTGSafetyTier)
        assert isinstance(test_case.auth_requirement, WSTGAuthRequirement)
        assert isinstance(test_case.adapter_family, WSTGAdapterFamily)
        assert test_case.evidence_required
        assert test_case.source_url.startswith("https://owasp.org/www-project-web-security-testing-guide/v42/")
