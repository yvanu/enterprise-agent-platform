from app.agents.data.agent import _chart, _report
from app.agents.data.models import QueryResult


def test_chart_and_report_for_grouped_numeric_result():
    result = QueryResult(
        columns=["main_type", "total"],
        rows=[
            {"main_type": "海洋环境", "total": 3},
            {"main_type": "雷达资料", "total": 1},
        ],
        row_count=2,
    )

    chart = _chart(result)
    report = _report("统计分类", "海洋环境最多。", ["共两类"], "SELECT ...", result)

    assert chart is not None
    assert chart.labels == ["海洋环境", "雷达资料"]
    assert chart.values == [3.0, 1.0]
    assert "# 数据分析报告" in report
    assert "| 海洋环境 | 3 |" in report
