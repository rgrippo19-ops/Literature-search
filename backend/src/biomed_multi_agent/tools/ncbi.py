from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from typing import Iterable

import requests

from ..config import SETTINGS
from ..schemas import PaperRecord

logger = logging.getLogger(__name__)

NCBI_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
NCBI_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PMC_IDCONV = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
PMC_BIOC = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/{id}/unicode"

_SESSION: requests.Session | None = None


def _session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        s = requests.Session()
        s.headers.update({"User-Agent": SETTINGS.http_user_agent})
        _SESSION = s
    return _SESSION


def _common_params() -> dict[str, str]:
    params = {"tool": SETTINGS.ncbi_tool, "email": SETTINGS.ncbi_email}
    if SETTINGS.ncbi_api_key:
        params["api_key"] = SETTINGS.ncbi_api_key
    return params


def search_pubmed(queries: Iterable[str], *, max_papers: int | None = None, max_papers_per_query: int | None = None) -> list[PaperRecord]:
    query_list = [q.strip() for q in queries if q and q.strip()]
    if not query_list:
        return []
    max_papers = max_papers or SETTINGS.max_papers
    max_papers_per_query = max_papers_per_query or SETTINGS.max_papers_per_query
    all_pmids: list[str] = []
    for query in query_list:
        pmids = _esearch(query, max_results=max_papers_per_query)
        all_pmids.extend(pmids)
        if SETTINGS.sleep_between_requests_sec:
            time.sleep(SETTINGS.sleep_between_requests_sec)
    unique_pmids = list(dict.fromkeys(all_pmids))
    if not unique_pmids:
        return []
    papers = _efetch_pubmed(unique_pmids)
    if SETTINGS.enable_pmc_fulltext and papers:
        papers = enrich_with_pmc_fulltext(papers)
    return rank_papers(papers, query_list)[:max_papers]


def _esearch(query: str, max_results: int) -> list[str]:
    params = {
        **_common_params(),
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": min(max_results, 100),
        "sort": "relevance",
    }
    r = _session().get(NCBI_ESEARCH, params=params, timeout=SETTINGS.http_timeout_sec)
    r.raise_for_status()
    payload = r.json()
    return payload.get("esearchresult", {}).get("idlist", [])


def _efetch_pubmed(pmids: list[str]) -> list[PaperRecord]:
    params = {
        **_common_params(),
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }
    r = _session().get(NCBI_EFETCH, params=params, timeout=SETTINGS.http_timeout_sec)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    papers: list[PaperRecord] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = _xml_text(article, ".//PMID")
        title = _xml_text(article, ".//ArticleTitle")
        if not pmid or not title:
            continue
        abstract_parts = [" ".join(node.itertext()).strip() for node in article.findall(".//Abstract/AbstractText")]
        abstract = " ".join(part for part in abstract_parts if part)
        journal = _xml_text(article, ".//Journal/Title")
        year = _year_from_article(article)
        authors = _authors_from_article(article)
        doi = _article_doi(article)
        publication_types = [pt.text.strip() for pt in article.findall(".//PublicationType") if pt.text and pt.text.strip()]
        species_hint = infer_species(f"{title} {abstract}")
        papers.append(PaperRecord(
            paper_id=pmid,
            pmid=pmid,
            title=title,
            year=year,
            journal=journal,
            authors=authors,
            abstract=abstract,
            evidence_source_type="abstract",
            species_hint=species_hint,
            publication_types=publication_types,
            doi=doi,
            source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            selection_reason="Retrieved from PubMed",
        ))
    return papers


def enrich_with_pmc_fulltext(papers: list[PaperRecord]) -> list[PaperRecord]:
    pmids = [p.pmid for p in papers if p.pmid]
    if not pmids:
        return papers
    pmcid_map = _lookup_pmcids(pmids)
    enriched: list[PaperRecord] = []
    for paper in papers:
        pmcid = pmcid_map.get(paper.pmid, "")
        if not pmcid:
            enriched.append(paper)
            continue
        paper.pmcid = pmcid
        full_text = _fetch_pmc_bioc_text(pmcid) or _fetch_pmc_bioc_text(paper.pmid)
        if full_text:
            paper.full_text = full_text[: SETTINGS.fulltext_char_limit]
            paper.evidence_source_type = "mixed" if paper.abstract else "full_text"
            paper.source_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
        enriched.append(paper)
        if SETTINGS.sleep_between_requests_sec:
            time.sleep(SETTINGS.sleep_between_requests_sec)
    return enriched


def _lookup_pmcids(pmids: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for i in range(0, len(pmids), 200):
        batch = pmids[i:i + 200]
        params = {
            **_common_params(),
            "ids": ",".join(batch),
            "idtype": "pmid",
            "format": "json",
        }
        r = _session().get(PMC_IDCONV, params=params, timeout=SETTINGS.http_timeout_sec)
        r.raise_for_status()
        payload = r.json()
        for record in payload.get("records", []):
            pmid = str(record.get("pmid") or "")
            pmcid = str(record.get("pmcid") or "")
            if pmid and pmcid:
                out[pmid] = pmcid if pmcid.startswith("PMC") else f"PMC{pmcid}"
    return out


def _fetch_pmc_bioc_text(article_id: str) -> str:
    url = PMC_BIOC.format(id=article_id)
    try:
        r = _session().get(url, timeout=SETTINGS.http_timeout_sec)
        if r.status_code == 404:
            return ""
        r.raise_for_status()
        payload = r.json()
    except Exception as exc:
        logger.info("PMC BioC fetch failed for %s: %s", article_id, exc)
        return ""

    paragraphs: list[str] = []
    documents = payload.get("documents", []) if isinstance(payload, dict) else []
    for doc in documents:
        for passage in doc.get("passages", []):
            infons = passage.get("infons", {}) or {}
            section_type = str(infons.get("section_type", "")).lower()
            text = str(passage.get("text", "")).strip()
            if not text or section_type in {"title", "front"}:
                continue
            paragraphs.append(text)
            if len(paragraphs) >= SETTINGS.fulltext_paragraph_limit:
                break
        if len(paragraphs) >= SETTINGS.fulltext_paragraph_limit:
            break
    return "\n\n".join(paragraphs)


def rank_papers(papers: list[PaperRecord], queries: list[str]) -> list[PaperRecord]:
    query_tokens = {tok for q in queries for tok in q.lower().split() if len(tok) > 2}
    scored: list[tuple[tuple[int, int, int, int], PaperRecord]] = []
    for paper in papers:
        text = f"{paper.title} {paper.abstract} {paper.full_text[:4000]}".lower()
        overlap = sum(1 for token in query_tokens if token in text)
        fulltext_bonus = 1 if paper.full_text else 0
        primary_penalty = -1 if any("review" in pt.lower() for pt in paper.publication_types) else 0
        scored.append(((overlap, fulltext_bonus, primary_penalty, paper.year), paper))
    scored.sort(key=lambda x: x[0], reverse=True)
    deduped: list[PaperRecord] = []
    seen_keys: set[str] = set()
    for _, paper in scored:
        key = paper.pmid or paper.doi or paper.title.lower()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(paper)
    return deduped


def infer_species(text: str) -> str:
    lower = text.lower()
    if any(term in lower for term in ["mouse", "mice", "murine"]):
        return "mouse"
    if any(term in lower for term in ["rat", "rats"]):
        return "rat"
    if "rodent" in lower:
        return "rodent"
    if any(term in lower for term in ["human", "humans", "patient", "patients", "participant", "participants", "cohort", "adults", "volunteers"]):
        return "human"
    return "unknown"


def _xml_text(node, path: str) -> str:
    found = node.find(path)
    if found is None:
        return ""
    return " ".join(t.strip() for t in found.itertext() if t and t.strip()).strip()


def _year_from_article(article) -> int:
    year = _xml_text(article, ".//PubDate/Year")
    if year.isdigit():
        return int(year)
    medline = _xml_text(article, ".//PubDate/MedlineDate")
    for token in medline.split():
        if token[:4].isdigit():
            return int(token[:4])
    return 0


def _authors_from_article(article) -> list[str]:
    authors: list[str] = []
    for author in article.findall(".//Author"):
        collective = _xml_text(author, "CollectiveName")
        if collective:
            authors.append(collective)
            continue
        fore = _xml_text(author, "ForeName")
        last = _xml_text(author, "LastName")
        joined = " ".join(x for x in [fore, last] if x)
        if joined:
            authors.append(joined)
    return authors


def _article_doi(article) -> str:
    for node in article.findall(".//ArticleId"):
        if node.attrib.get("IdType") == "doi" and node.text:
            return node.text.strip()
    return ""
