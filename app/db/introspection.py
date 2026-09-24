from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def describe_schema(engine: Engine, schema: str | None = None) -> dict:
    inspector = inspect(engine)
    table_names = inspector.get_table_names(schema=schema)

    tables: list[dict] = []
    for table_name in table_names:
        columns = inspector.get_columns(table_name, schema=schema)
        primary_key = inspector.get_pk_constraint(table_name, schema=schema) or {}
        indexes = inspector.get_indexes(table_name, schema=schema)

        tables.append(
            {
                "name": table_name,
                "columns": [
                    {
                        "name": column["name"],
                        "type": str(column["type"]),
                        "nullable": bool(column.get("nullable", True)),
                    }
                    for column in columns
                ],
                "primary_key": primary_key.get("constrained_columns") or [],
                "indexes": [
                    {
                        "name": idx.get("name"),
                        "columns": idx.get("column_names") or [],
                        "unique": bool(idx.get("unique", False)),
                    }
                    for idx in indexes
                ],
            }
        )

    return {
        "dialect": engine.dialect.name,
        "schema": schema,
        "tables": tables,
    }


def schema_to_prompt(schema_info: dict) -> str:
    lines = [f"Database dialect: {schema_info['dialect']}"]
    if schema_info.get("schema"):
        lines.append(f"Schema: {schema_info['schema']}")

    for table in schema_info["tables"]:
        lines.append(f"\nTABLE {table['name']}")
        pk = set(table.get("primary_key") or [])
        for column in table["columns"]:
            suffix = " PRIMARY KEY" if column["name"] in pk else ""
            lines.append(f"- {column['name']}: {column['type']}{suffix}")

    return "\n".join(lines)
