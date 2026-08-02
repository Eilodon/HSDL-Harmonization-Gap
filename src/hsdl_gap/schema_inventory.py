from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SchemaInventoryError(ValueError):
    pass


def inspect_schema(path: str | Path) -> dict[str, Any]:
    schema_path = Path(path)
    try:
        payload = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaInventoryError(f"cannot load schema {schema_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SchemaInventoryError(f"schema {schema_path} must be a JSON object")
    required = ("$schema", "$id", "title", "type")
    missing = [field for field in required if not payload.get(field)]
    if missing:
        raise SchemaInventoryError(
            f"schema {schema_path} is missing self-description fields: {missing}"
        )
    if payload["$schema"] != "https://json-schema.org/draft/2020-12/schema":
        raise SchemaInventoryError(
            f"schema {schema_path} must declare JSON Schema Draft 2020-12"
        )
    return {
        "path": schema_path.as_posix(),
        "$id": payload["$id"],
        "title": payload["title"],
        "type": payload["type"],
    }


def build_schema_inventory(schema_dir: str | Path = "schemas") -> dict[str, Any]:
    root = Path(schema_dir)
    paths = sorted(root.glob("*.schema.json"))
    if not paths:
        raise SchemaInventoryError(f"no schema files found in {root}")
    schemas = [inspect_schema(path) for path in paths]
    ids = [schema["$id"] for schema in schemas]
    duplicates = sorted({schema_id for schema_id in ids if ids.count(schema_id) > 1})
    if duplicates:
        raise SchemaInventoryError(f"duplicate schema IDs: {duplicates}")
    return {
        "schema_version": "1.0.0",
        "status": "SCHEMA_INVENTORY_VALID",
        "schema_count": len(schemas),
        "schemas": schemas,
    }
