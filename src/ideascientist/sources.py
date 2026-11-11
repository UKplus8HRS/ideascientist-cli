"""Literature access. v1 searches arXiv only. Tests can inject text instead."""

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from ideascientist.paths import load_vendor
from ideascientist.store import dump

ATOM = "{http://www.w3.org/2005/Atom}"
SEARCH = "https://export.arxiv.org/api/query"


def admit(identity, cutoff):
    """True when this exact version may be registered."""
    if cutoff is None:
        return True
    date = identity.get("publication_date")
    return isinstance(date, str) and date <= cutoff


def register_sources(run, sources, cutoff):
    """Assign P ids to cutoff-valid identities. Rejected sources get no id."""
    admitted, rejected = [], []
    known = {}
    for paper in run.data["papers"]:
        identity = paper["identity"]
        known[(identity.get("doi") or identity.get("url"), identity.get("version"))] = paper["paper_id"]
    for source in sources:
        identity = source.get("identity") or {}
        if not admit(identity, cutoff):
            rejected.append(source)
            continue
        key = (identity.get("doi") or identity.get("url"), identity.get("version"))
        paper_id = known.get(key)
        if paper_id is None:
            paper_id = run.alloc("paper")
            run.data["papers"].append({"paper_id": paper_id, "identity": identity})
            known[key] = paper_id
            run.save()
        admitted.append({**source, "paper_id": paper_id})
    return admitted, rejected


class DictSource:
    def __init__(self, texts):
        self.texts = texts

    def text_for(self, run, paper_id, identity):
        del run, paper_id
        text = self.texts.get(identity.get("url"))
        if not text:
            return None, "no injected text for this identity"
        return text, None


class ArxivSource:
    def text_for(self, run, paper_id, identity):
        request_path = run.path / "sources" / f"{paper_id}.request.json"
        dump(request_path, {"paper_id": paper_id, "identity": identity})
        acquire = load_vendor("acquire_arxiv").acquire
        receipt = acquire(str(request_path.resolve()))
        if receipt.get("status") != "ready":
            return None, receipt.get("reason") or "PDF acquisition failed"
        pdf = run.path / "sources" / f"{paper_id}.pdf"
        try:
            text, _truncated = extract_pdf(pdf)
        except RuntimeError as exc:
            return None, str(exc)
        if not text.strip():
            return None, "PDF had no extractable text"
        return text, None


def extract_pdf(path, max_pages=20, max_chars=40000):
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Install pypdf to read PDFs: python -m pip install pypdf") from exc
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages[:max_pages]:
        parts.append(page.extract_text() or "")
    text = "\n".join(parts).strip()
    return text[:max_chars], len(reader.pages) > max_pages or len(text) > max_chars


def search_arxiv(query, max_results=5):
    params = urllib.parse.urlencode({
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max(1, min(int(max_results), 8)),
    })
    request = urllib.request.Request(
        f"{SEARCH}?{params}",
        headers={"Accept": "application/atom+xml", "User-Agent": "IdeaScientist-cli/0.1"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read(262144)
    feed = ET.fromstring(data)
    found = []
    for entry in feed.findall(f"{ATOM}entry"):
        raw_id = (entry.findtext(f"{ATOM}id") or "").rsplit("/", 1)[-1]
        title = " ".join((entry.findtext(f"{ATOM}title") or "").split())
        published = (entry.findtext(f"{ATOM}published") or "")[:10]
        authors = [" ".join((author.findtext(f"{ATOM}name") or "").split()) for author in entry.findall(f"{ATOM}author")]
        if raw_id and title:
            found.append({"arxiv_id": raw_id, "title": title, "published": published, "authors": authors[:12]})
    return found


def resolve_arxiv(identifier):
    return load_vendor("resolve_metadata").resolve_metadata(identifier)
