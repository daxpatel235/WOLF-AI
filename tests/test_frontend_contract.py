"""
Static checks that the UI and the Python bridge agree with each other.
These catch the mistakes that otherwise only show up as a broken or blank window.
"""
import ast
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web"
SCRIPT = (WEB / "script.js").read_text(encoding="utf-8")
HTML = (WEB / "index.html").read_text(encoding="utf-8")


def bridge_methods():
    tree = ast.parse((ROOT / "backend" / "bridge.py").read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ApiBridge")
    return {n.name for n in cls.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")}


def bridge_public_attributes():
    """Public instance attributes would be walked and exposed to JS by pywebview."""
    tree = ast.parse((ROOT / "backend" / "bridge.py").read_text(encoding="utf-8"))
    attrs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                        and target.value.id == "self" and not target.attr.startswith("_")):
                    attrs.add(target.attr)
    return attrs


class _Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.refs = set(), []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.refs.append(attrs["href"])
        if tag == "script" and attrs.get("src"):
            self.refs.append(attrs["src"])


def parse_html():
    collector = _Collector()
    collector.feed(HTML)
    return collector


def test_every_js_api_call_exists_in_bridge():
    called = set(re.findall(r"api\(\)\.(\w+)\(", SCRIPT))
    called |= set(re.findall(r"window\.pywebview\.api\.(\w+)\(", SCRIPT))
    missing = called - bridge_methods()
    assert called, "no API calls found; regex out of date?"
    assert not missing, f"JS calls bridge methods that don't exist: {sorted(missing)}"


def test_bridge_exposes_no_public_attributes():
    exposed = bridge_public_attributes()
    assert not exposed, f"pywebview would expose these attributes to JS: {sorted(exposed)}"


def test_every_element_id_used_by_js_exists():
    ids = parse_html().ids
    used = set(re.findall(r"getElementById\('([\w-]+)'\)", SCRIPT))
    missing = used - ids
    assert used
    assert not missing, f"script.js looks up ids missing from index.html: {sorted(missing)}"


def test_html_ids_are_unique():
    found = re.findall(r'\sid="([\w-]+)"', HTML)
    dupes = {i for i in found if found.count(i) > 1}
    assert not dupes, f"duplicate ids: {sorted(dupes)}"


def test_linked_assets_exist():
    for ref in parse_html().refs:
        assert (WEB / ref).exists(), f"index.html references missing file {ref}"


def test_html_is_well_formed_enough():
    # Every opened div/section-like container must be closed; an unclosed tag can hide the whole UI.
    for tag in ("div", "main", "aside", "header", "button", "select", "label", "form"):
        opened = len(re.findall(rf"<{tag}[\s>]", HTML))
        closed = len(re.findall(rf"</{tag}>", HTML))
        assert opened == closed, f"<{tag}> opened {opened} times but closed {closed} times"


def test_css_braces_balanced():
    css = re.sub(r"/\*.*?\*/", "", (WEB / "styles.css").read_text(encoding="utf-8"), flags=re.S)
    assert css.count("{") == css.count("}")

