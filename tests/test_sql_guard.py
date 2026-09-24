import pytest

from app.db.sql_guard import UnsafeSqlError, guard_sql


def test_guard_allows_select_and_adds_limit():
    guarded = guard_sql("SELECT id, name FROM data_assets", max_rows=20, dialect="sqlite")
    assert "LIMIT 20" in guarded.executable


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM data_assets",
        "UPDATE data_assets SET name='x'",
        "DROP TABLE data_assets",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT * FROM data_assets; SELECT 1",
    ],
)
def test_guard_rejects_unsafe_sql(sql):
    with pytest.raises(UnsafeSqlError):
        guard_sql(sql, max_rows=20, dialect="postgres")
