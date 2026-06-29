import pytest

from aotp.report_quality import ReportQuality


def test_quality_score_has_ten_independent_dimensions():
    assert ReportQuality(*([10] * 10)).score() == 100
    with pytest.raises(ValueError):
        ReportQuality(scope_proof=11).score()
