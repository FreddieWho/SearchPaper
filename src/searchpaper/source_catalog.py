"""Static source catalog for routing and integration warnings."""

from __future__ import annotations

from pydantic import BaseModel


class SourceDescriptor(BaseModel):
    """Describes a scholarly source independent of adapter availability."""

    name: str
    tier: str
    domain: str
    implemented: bool
    access_model: str
    api_docs_url: str | None = None
    requires_key: bool = False
    risk_note: str | None = None


_SOURCE_CATALOG: tuple[SourceDescriptor, ...] = (
    SourceDescriptor(
        name="pubmed",
        tier="T1",
        domain="biomedical",
        implemented=True,
        access_model="official_api",
        api_docs_url="https://www.ncbi.nlm.nih.gov/books/NBK25501/",
    ),
    SourceDescriptor(
        name="crossref",
        tier="T1",
        domain="cross-disciplinary",
        implemented=True,
        access_model="official_api",
        api_docs_url="https://api.crossref.org/swagger-ui/index.html",
    ),
    SourceDescriptor(
        name="openalex",
        tier="T1",
        domain="cross-disciplinary",
        implemented=True,
        access_model="official_api",
        api_docs_url="https://docs.openalex.org/",
    ),
    SourceDescriptor(
        name="europepmc",
        tier="T1",
        domain="biomedical",
        implemented=True,
        access_model="official_api",
        api_docs_url="https://europepmc.org/RestfulWebService",
    ),
    SourceDescriptor(
        name="arxiv",
        tier="T1",
        domain="preprint",
        implemented=True,
        access_model="official_api",
        api_docs_url="https://info.arxiv.org/help/api/index.html",
    ),
    SourceDescriptor(
        name="biorxiv",
        tier="T2",
        domain="preprint",
        implemented=True,
        access_model="official_api",
        api_docs_url="https://api.biorxiv.org/",
    ),
    SourceDescriptor(
        name="medrxiv",
        tier="T2",
        domain="preprint",
        implemented=True,
        access_model="official_api",
        api_docs_url="https://api.biorxiv.org/",
    ),
    SourceDescriptor(
        name="semantic_scholar",
        tier="T2",
        domain="citation",
        implemented=True,
        access_model="official_api",
        api_docs_url="https://api.semanticscholar.org/api-docs/",
    ),
    SourceDescriptor(
        name="unpaywall",
        tier="T2",
        domain="open_access",
        implemented=True,
        access_model="official_api",
        api_docs_url="https://unpaywall.org/products/api",
        requires_key=False,
        risk_note="Email is required for polite pool; falls back to crossref_email if unpaywall_email is not set.",
    ),
    SourceDescriptor(
        name="opencitations",
        tier="T2",
        domain="citation",
        implemented=True,
        access_model="official_api",
        api_docs_url="https://opencitations.net/",
        requires_key=False,
        risk_note="Rate limits apply; primarily useful for DOI-to-DOI citation links.",
    ),
    SourceDescriptor(
        name="pubtator3",
        tier="signal",
        domain="biomedical",
        implemented=True,
        access_model="official_api",
        api_docs_url="https://www.ncbi.nlm.nih.gov/research/pubtator3/api",
    ),
    SourceDescriptor(
        name="scopus",
        tier="T3",
        domain="citation",
        implemented=False,
        access_model="external_or_institutional",
        requires_key=True,
        api_docs_url="https://dev.elsevier.com/",
        risk_note="Institutional entitlement and quota are required; not enabled by default.",
    ),
    SourceDescriptor(
        name="sciencedirect",
        tier="T3",
        domain="publisher",
        implemented=False,
        access_model="external_or_institutional",
        requires_key=True,
        api_docs_url="https://dev.elsevier.com/",
        risk_note="Institutional entitlement and quota are required; not enabled by default.",
    ),
    SourceDescriptor(
        name="webofscience",
        tier="T3",
        domain="citation",
        implemented=False,
        access_model="external_or_institutional",
        requires_key=True,
        risk_note="Institutional subscription is required; treated as manual/external.",
    ),
    SourceDescriptor(
        name="google_scholar",
        tier="T3",
        domain="general",
        implemented=False,
        access_model="scraped",
        risk_note="Scraping is unstable and may violate service limits; not implemented.",
    ),
    SourceDescriptor(
        name="cnki",
        tier="manual",
        domain="chinese-literature",
        implemented=False,
        access_model="manual",
        risk_note="No stable open programmatic access; report as manual coverage gap.",
    ),
    SourceDescriptor(
        name="wanfang",
        tier="manual",
        domain="chinese-literature",
        implemented=False,
        access_model="manual",
        risk_note="No stable open programmatic access; report as manual coverage gap.",
    ),
)


def list_source_descriptors() -> list[SourceDescriptor]:
    return list(_SOURCE_CATALOG)


def get_source_descriptor(name: str) -> SourceDescriptor:
    normalized = name.lower().strip()
    for descriptor in _SOURCE_CATALOG:
        if descriptor.name == normalized:
            return descriptor
    raise KeyError(f"Unknown source descriptor: {name}")


def implemented_sources() -> list[str]:
    return [descriptor.name for descriptor in _SOURCE_CATALOG if descriptor.implemented]
