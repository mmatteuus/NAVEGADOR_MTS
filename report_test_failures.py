"""Publica falhas resumidas de um relatório JUnit como annotations do Actions."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_MESSAGE = 500


def _escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(value: str) -> str:
    return _escape(value).replace(":", "%3A").replace(",", "%2C")[:MAX_MESSAGE]


def _cases(root: ET.Element) -> list[ET.Element]:
    return list(root.iter("testcase"))


def report(path: Path) -> int:
    if not path.is_file():
        print(f"JUnit XML ausente: {path}", file=sys.stderr)
        return 2
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        print(f"JUnit XML inválido ({path}): {exc}", file=sys.stderr)
        return 2
    failures = []
    for case in _cases(root):
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        if problem is None:
            continue
        classname = case.get("classname", "unknown")
        name = case.get("name", "unknown")
        detail = (problem.get("message") or problem.text or "sem mensagem").strip()
        detail = detail[:MAX_MESSAGE]
        title = _escape_property(f"{classname}::{name}")
        failures.append((title, _escape(detail)))
    print(f"JUnit: {len(failures)} falha(s) encontrada(s).")
    for title, detail in failures:
        print(f"::error title={title}::{detail}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Uso: python report_test_failures.py <junit.xml>", file=sys.stderr)
        return 2
    return report(Path(argv[1]))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
