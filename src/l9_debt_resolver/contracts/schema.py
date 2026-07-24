from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import (
    Draft202012Validator,
    FormatChecker,
)
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

from .errors import SchemaValidationError


class SchemaRegistry:
    def __init__(
        self,
        schema_root: Path,
    ) -> None:
        self._schema_root = schema_root
        self._documents = self._load_documents()
        self._registry = self._build_registry()

    @property
    def registry(self) -> Registry:
        return self._registry

    def document(
        self,
        path: Path,
    ) -> dict[str, Any]:
        resolved = path.resolve()
        try:
            return self._documents[resolved]
        except KeyError as error:
            raise SchemaValidationError(
                f"schema is outside registry: {path}"
            ) from error

    def _load_documents(
        self,
    ) -> dict[Path, dict[str, Any]]:
        documents: dict[Path, dict[str, Any]] = {}
        for path in sorted(self._schema_root.glob("*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise SchemaValidationError(f"schema must be an object: {path}")
            Draft202012Validator.check_schema(value)
            documents[path.resolve()] = value
        return documents

    def _build_registry(self) -> Registry:
        registry = Registry()
        for document in self._documents.values():
            identifier = document.get("$id")
            if not isinstance(identifier, str):
                continue
            resource = Resource.from_contents(document)
            registry = registry.with_resource(
                identifier,
                resource,
            )
        return registry


class SchemaValidator:
    def __init__(
        self,
        schema_path: Path,
    ) -> None:
        schema_path = schema_path.resolve()
        registry = SchemaRegistry(schema_path.parent)
        schema = registry.document(schema_path)
        self._validator = Draft202012Validator(
            schema,
            registry=registry.registry,
            format_checker=FormatChecker(),
        )

    def validate(
        self,
        document: object,
    ) -> None:
        errors = sorted(
            self._validator.iter_errors(document),
            key=lambda error: (
                tuple(str(item) for item in error.path),
                error.message,
            ),
        )
        if not errors:
            return
        raise SchemaValidationError("; ".join(_format_error(error) for error in errors))


def _format_error(
    error: ValidationError,
) -> str:
    location = "$"
    for item in error.absolute_path:
        if isinstance(item, int):
            location += f"[{item}]"
        else:
            location += f".{item}"
    return f"{location}: {error.message}"
