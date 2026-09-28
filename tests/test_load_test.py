from scripts.load_test import percentile


def test_load_test_percentile():
    values = [10.0, 20.0, 30.0, 40.0]

    assert percentile(values, 0.50) == 30.0
    assert percentile(values, 0.95) == 40.0
