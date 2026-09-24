from sqlalchemy import text

from app.db.engine import Database


def initialize_demo_database(db: Database) -> None:
    if db.engine.dialect.name != "sqlite":
        return

    ddl = [
        """
        CREATE TABLE IF NOT EXISTS data_assets (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            main_type TEXT NOT NULL,
            provider TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS import_jobs (
            id INTEGER PRIMARY KEY,
            asset_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            duration_seconds REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(asset_id) REFERENCES data_assets(id)
        )
        """,
    ]

    sample_assets = [
        (1, "海温数据-2026-01", "海洋环境", "第一研究所", 524288000, "2026-01-18"),
        (2, "盐度数据-2026-02", "海洋环境", "第一研究所", 734003200, "2026-02-08"),
        (3, "雷达回波-J001", "雷达资料", "第二研究所", 2147483648, "2026-03-12"),
        (4, "浅地层剖面-A12", "地质资料", "第三研究所", 1572864000, "2026-04-21"),
        (5, "声纳侧扫-B07", "声学资料", "第二研究所", 966367641, "2026-05-09"),
        (6, "海温数据-2025-11", "海洋环境", "第一研究所", 419430400, "2025-11-22"),
    ]

    sample_jobs = [
        (1, 1, "success", 18.2, "2026-01-18"),
        (2, 2, "success", 24.1, "2026-02-08"),
        (3, 3, "failed", 62.7, "2026-03-12"),
        (4, 3, "success", 55.4, "2026-03-13"),
        (5, 4, "success", 33.8, "2026-04-21"),
        (6, 5, "success", 20.5, "2026-05-09"),
    ]

    with db.engine.begin() as conn:
        for statement in ddl:
            conn.execute(text(statement))

        count = conn.execute(text("SELECT COUNT(*) FROM data_assets")).scalar_one()
        if count == 0:
            conn.execute(
                text(
                    """
                    INSERT INTO data_assets
                    (id, name, main_type, provider, size_bytes, created_at)
                    VALUES (:id, :name, :main_type, :provider, :size_bytes, :created_at)
                    """
                ),
                [
                    {
                        "id": r[0],
                        "name": r[1],
                        "main_type": r[2],
                        "provider": r[3],
                        "size_bytes": r[4],
                        "created_at": r[5],
                    }
                    for r in sample_assets
                ],
            )

        count = conn.execute(text("SELECT COUNT(*) FROM import_jobs")).scalar_one()
        if count == 0:
            conn.execute(
                text(
                    """
                    INSERT INTO import_jobs
                    (id, asset_id, status, duration_seconds, created_at)
                    VALUES (:id, :asset_id, :status, :duration_seconds, :created_at)
                    """
                ),
                [
                    {
                        "id": r[0],
                        "asset_id": r[1],
                        "status": r[2],
                        "duration_seconds": r[3],
                        "created_at": r[4],
                    }
                    for r in sample_jobs
                ],
            )
