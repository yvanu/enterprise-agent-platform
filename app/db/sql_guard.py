import re
from dataclasses import dataclass

import sqlglot
from sqlglot import exp


class UnsafeSqlError(ValueError):
    pass


@dataclass(frozen=True)
class GuardedSql:
    original: str
    executable: str


_DENIED_KEYWORDS = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|UPSERT|MERGE|REPLACE|"
    r"CREATE|ALTER|DROP|TRUNCATE|COMMENT|GRANT|REVOKE|"
    r"COPY|CALL|EXECUTE|DO|VACUUM|ANALYZE|ATTACH|DETACH|PRAGMA"
    r")\b",
    re.IGNORECASE,
)

_DENIED_PATTERNS = [
    re.compile(r"\bFOR\s+(UPDATE|SHARE|NO\s+KEY\s+UPDATE|KEY\s+SHARE)\b", re.IGNORECASE),
    re.compile(r"\bINTO\s+(OUTFILE|DUMPFILE)\b", re.IGNORECASE),
]

_DENIED_FUNCTIONS = {
    "pg_read_file",
    "pg_read_binary_file",
    "pg_ls_dir",
    "pg_stat_file",
    "lo_import",
    "lo_export",
    "dblink_connect",
    "dblink_exec",
    "pg_sleep",
}


def _function_name(node: exp.Expression) -> str | None:
    if isinstance(node, exp.Anonymous):
        return node.name.lower()
    if isinstance(node, exp.Func):
        try:
            return node.sql_name().lower()
        except Exception:
            return None
    return None


def guard_sql(sql: str, *, max_rows: int, dialect: str | None = None) -> GuardedSql:
    raw = sql.strip().rstrip(";").strip()
    if not raw:
        raise UnsafeSqlError("SQL 不能为空")

    if _DENIED_KEYWORDS.search(raw):
        raise UnsafeSqlError("只允许只读查询，SQL 中包含写入或管理类关键字")

    for pattern in _DENIED_PATTERNS:
        if pattern.search(raw):
            raise UnsafeSqlError("SQL 中包含不允许的锁定或文件操作")

    try:
        statements = sqlglot.parse(raw, read=dialect)
    except sqlglot.errors.ParseError as exc:
        raise UnsafeSqlError(f"SQL 解析失败: {exc}") from exc

    if len(statements) != 1:
        raise UnsafeSqlError("一次只允许执行一条 SQL")

    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise UnsafeSqlError("仅允许 SELECT / CTE 查询")

    for node in tree.walk():
        if isinstance(
            node,
            (
                exp.Insert,
                exp.Update,
                exp.Delete,
                exp.Create,
                exp.Drop,
                exp.Alter,
                exp.Command,
                exp.Merge,
            ),
        ):
            raise UnsafeSqlError(f"检测到禁止的 SQL 节点: {node.key}")

        fn = _function_name(node)
        if fn in _DENIED_FUNCTIONS:
            raise UnsafeSqlError(f"禁止调用数据库函数: {fn}")

    normalized = tree.sql(dialect=dialect) if dialect else tree.sql()
    executable = f"SELECT * FROM ({normalized}) AS _agent_result LIMIT {int(max_rows)}"
    return GuardedSql(original=raw, executable=executable)
