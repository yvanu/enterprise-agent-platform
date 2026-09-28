from app.api import data as data_api
from app.core.config import DataSourceConfig, Settings
from app.db.demo import initialize_demo_database
from app.db.engine import Database


def test_demo_database_query(tmp_path):
    db = Database(Settings(database_url=f"sqlite:///{tmp_path}/demo.db"))
    initialize_demo_database(db)

    result = db.execute_readonly(
        "SELECT main_type, COUNT(*) AS total FROM data_assets GROUP BY main_type"
    )

    assert result.row_count == 4
    assert {row["main_type"] for row in result.rows} == {
        "海洋环境",
        "雷达资料",
        "地质资料",
        "声学资料",
    }


def test_named_data_source(monkeypatch, tmp_path):
    name = "analytics_test"
    url = f"sqlite:///{tmp_path}/analytics.db"
    monkeypatch.setitem(
        data_api.settings.data_sources,
        name,
        DataSourceConfig(url=url, schema_name=None),
    )
    try:
        db = data_api.get_database(name)
        assert db.url == url
        assert db.schema is None
    finally:
        data_api._databases.pop(name, None)
