"""Testes unitários do diagnóstico público de falhas JUnit."""

from pathlib import Path

from report_test_failures import MAX_MESSAGE, report


def test_reporta_failure_e_error_com_escape(tmp_path: Path, capsys) -> None:
    xml = tmp_path / "results.xml"
    xml.write_text(
        '<testsuites><testsuite><testcase classname="a%b" name="falha&#10;1">'
        '<failure>linha%um\nlinha dois</failure></testcase>'
        '<testcase classname="pkg" name="erro"><error message="erro curto" /></testcase>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    assert report(xml) == 0
    output = capsys.readouterr().out
    assert "::error title=a%25b%3A%3Afalha%0A1::linha%25um%0Alinha dois" in output
    assert "::error title=pkg%3A%3Aerro::erro curto" in output


def test_trunca_mensagem(tmp_path: Path, capsys) -> None:
    xml = tmp_path / "results.xml"
    xml.write_text(f'<testsuite><testcase><failure>{"x" * 900}</failure></testcase></testsuite>', encoding="utf-8")
    assert report(xml) == 0
    line = capsys.readouterr().out.splitlines()[1]
    assert len(line.rsplit("::", 1)[-1]) == MAX_MESSAGE


def test_xml_ausente_ou_invalido_falha(tmp_path: Path, capsys) -> None:
    assert report(tmp_path / "missing.xml") != 0
    assert "ausente" in capsys.readouterr().err
    invalid = tmp_path / "invalid.xml"
    invalid.write_text("<testsuite>", encoding="utf-8")
    assert report(invalid) != 0
    assert "inválido" in capsys.readouterr().err


def test_xml_sem_falhas_e_sucesso(tmp_path: Path, capsys) -> None:
    xml = tmp_path / "ok.xml"
    xml.write_text("<testsuite><testcase classname='a' name='ok' /></testsuite>", encoding="utf-8")
    assert report(xml) == 0
    assert "0 falha(s)" in capsys.readouterr().out
