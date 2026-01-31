from pathlib import Path

from app.services.market_data.edinet.common import xbrl_utils


def test_find_xbrl_files(tmp_path: Path):
    a = tmp_path / "a.xbrl"
    a.write_text("<root/>", encoding="utf-8")

    sub = tmp_path / "sub"
    sub.mkdir()
    b = sub / "b.xml"
    b.write_text("<root/>", encoding="utf-8")

    c = tmp_path / "c.txt"
    c.write_text("no", encoding="utf-8")

    found = xbrl_utils.find_xbrl_files(tmp_path)
    names = {p.name for p in found}
    assert "a.xbrl" in names
    assert "b.xml" in names
    assert "c.txt" not in names


def test_extract_contexts_basic():
    x = (
        '<xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance">\n'
        '  <xbrli:context id="C1">'
        "<xbrli:entity><xbrli:identifier>JP</xbrli:identifier>"
        "</xbrli:entity><xbrli:period>"
        "<xbrli:instant>2020-03-31</xbrli:instant>"
        "</xbrli:period></xbrli:context>\n"
        '  <xbrli:context id="C2">'
        "<xbrli:entity><xbrli:identifier>JP2</xbrli:identifier>"
        "</xbrli:entity><xbrli:period>"
        "<xbrli:startDate>2019-04-01</xbrli:startDate>"
        "<xbrli:endDate>2020-03-31</xbrli:endDate>"
        "</xbrli:period></xbrli:context>\n"
        "</xbrl>"
    )
    contexts = xbrl_utils.extract_contexts(x)
    assert "C1" in contexts and "C2" in contexts
    assert "instant" in contexts["C1"]["period"]
    assert "startDate" in contexts["C2"]["period"]
