from typing import Any

from pydantic import BaseModel, Field


class UnifiedPaper(BaseModel):
    paper_id: str
    title: str
    year: int | None = None
    publication_date: str | None = None
    venue: str | None = None
    url: str | None = None
    doi: str | None = None
    pmid: str | None = None
    arxiv: str | None = None
    citation_count: int | None = None
    influential_citation_count: int | None = None
    authors: list[dict[str, Any]] = Field(default_factory=list)
    open_access_pdf: dict[str, Any] | None = None
    fields_of_study: list[str] = Field(default_factory=list)
    publication_types: list[str] = Field(default_factory=list)
    abstract: str | None = None
    tldr: str | None = None
    source: str = "semantic_scholar"


class UnifiedEntity(BaseModel):
    entity_id: str
    name: str | None = None
    type: str | None = None
    source: str = "pubtator3"


class EvidenceUrl(BaseModel):
    pmid: str
    pubmed_url: str
    pubtator_url: str


class UnifiedRelation(BaseModel):
    entity1: UnifiedEntity
    entity2: UnifiedEntity
    relation_type: str
    pmids: list[str] = Field(default_factory=list)
    evidence_urls: list[EvidenceUrl] = Field(default_factory=list)
    source: str = "pubtator3"
