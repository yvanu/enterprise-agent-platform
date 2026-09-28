from app.platform.regression import run_regression_suite


def test_regression_suite_passes():
    report = run_regression_suite()

    assert report.passed is True
    assert report.passed_cases == report.total_cases == 4
    assert {case.id for case in report.cases} == {
        "data-category-counts",
        "data-failed-imports",
        "knowledge-radar-retrieval",
        "knowledge-ocean-retrieval",
    }
