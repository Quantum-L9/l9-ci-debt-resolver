from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationRule:
    name: str
    category: str
    weight: float
    pattern: re.Pattern[str]


RULES = (
    ClassificationRule(
        "pytest_failure",
        "test_failure",
        0.45,
        re.compile(
            r"(?im)(?:=+\s+FAILURES\s+=+|"
            r"\bFAILED\s+.+::.+|"
            r"\b\d+\s+failed(?:,\s+\d+\s+passed)?)"
        ),
    ),
    ClassificationRule(
        "jest_failure",
        "test_failure",
        0.45,
        re.compile(
            r"(?im)(?:Test Suites:\s+\d+\s+failed|"
            r"Tests:\s+\d+\s+failed)"
        ),
    ),
    ClassificationRule(
        "generic_assertion_failure",
        "test_failure",
        0.30,
        re.compile(
            r"(?im)(?:AssertionError|assertion failed|"
            r"expected .+ (?:to equal|but was))"
        ),
    ),
    ClassificationRule(
        "python_syntax_error",
        "compilation",
        0.45,
        re.compile(
            r"(?im)(?:SyntaxError:|IndentationError:|"
            r"TabError:)"
        ),
    ),
    ClassificationRule(
        "compiler_error",
        "compilation",
        0.45,
        re.compile(
            r"(?im)(?:\berror\s+[A-Z]?\d{3,5}\b|"
            r"\bfatal error:|"
            r"\bcompilation failed\b|"
            r"\bcould not compile\b)"
        ),
    ),
    ClassificationRule(
        "typescript_compile", "type_failure", 0.45, re.compile(r"(?im)\berror TS\d{4}:")
    ),
    ClassificationRule(
        "mypy_failure",
        "type_failure",
        0.45,
        re.compile(
            r"(?im)(?:\berror:\s+.+\s+\[[a-z0-9-]+\]|"
            r"Found \d+ errors? in \d+ files?)"
        ),
    ),
    ClassificationRule(
        "pyright_failure",
        "type_failure",
        0.45,
        re.compile(r"(?im)\b\d+\s+errors?,\s+\d+\s+warnings?"),
    ),
    ClassificationRule(
        "ruff_failure",
        "lint_failure",
        0.45,
        re.compile(
            r"(?im)(?:Found \d+ errors?\.?$|"
            r"\b[A-Z]{1,4}\d{3,4}\b.+)"
        ),
    ),
    ClassificationRule(
        "eslint_failure",
        "lint_failure",
        0.45,
        re.compile(
            r"(?im)(?:\b\d+\s+problems?\s+"
            r"\(\d+\s+errors?|"
            r"\beslint\b.+\berror\b)"
        ),
    ),
    ClassificationRule(
        "dependency_not_found",
        "dependency",
        0.45,
        re.compile(
            r"(?im)(?:ModuleNotFoundError:|"
            r"Cannot find module|"
            r"package .+ is not in GOROOT|"
            r"could not find .+ in registry|"
            r"failed to resolve dependency)"
        ),
    ),
    ClassificationRule(
        "dependency_version_conflict",
        "dependency",
        0.45,
        re.compile(
            r"(?im)(?:ResolutionImpossible|"
            r"version solving failed|"
            r"dependency conflict|"
            r"conflicting dependencies)"
        ),
    ),
    ClassificationRule(
        "configuration_parse",
        "configuration",
        0.45,
        re.compile(
            r"(?im)(?:invalid configuration|"
            r"configuration error|"
            r"failed to parse .+\.(?:ya?ml|toml|json)|"
            r"unknown configuration key)"
        ),
    ),
    ClassificationRule(
        "generated_drift",
        "generated_file_drift",
        0.45,
        re.compile(
            r"(?im)(?:generated files? (?:are )?out of date|"
            r"run .+generate|"
            r"code generation produced changes|"
            r"generated output differs)"
        ),
    ),
    ClassificationRule(
        "security_scanner",
        "security_failure",
        0.45,
        re.compile(
            r"(?im)(?:critical vulnerability|"
            r"high severity vulnerability|"
            r"security scan failed|"
            r"secret detected|"
            r"policy violation)"
        ),
    ),
    ClassificationRule(
        "runner_infrastructure",
        "infrastructure",
        0.45,
        re.compile(
            r"(?im)(?:The hosted runner lost communication|"
            r"No space left on device|"
            r"runner was terminated|"
            r"service unavailable|"
            r"connection reset by peer|"
            r"network is unreachable|"
            r"rate limit exceeded)"
        ),
    ),
)
COMMAND_RULES = (
    (
        re.compile(r"(?i)\bpytest\b"),
        "test_failure",
    ),
    (
        re.compile(r"(?i)\b(?:jest|vitest|mocha)\b"),
        "test_failure",
    ),
    (
        re.compile(r"(?i)\b(?:ruff|flake8|pylint|eslint)\b"),
        "lint_failure",
    ),
    (
        re.compile(r"(?i)\b(?:mypy|pyright|tsc)\b"),
        "type_failure",
    ),
    (
        re.compile(r"(?i)\b(?:cargo build|go build|javac|gradle compile)\b"),
        "compilation",
    ),
    (
        re.compile(
            r"(?i)\b(?:pip install|npm install|npm ci|"
            r"pnpm install|yarn install|cargo fetch)\b"
        ),
        "dependency",
    ),
)
