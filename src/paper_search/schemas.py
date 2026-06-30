from typing import Any
from pydantic import BaseModel, Field
from typing import Optional


class UnifiedPaper(BaseModel):
    paper_id: str
    title: str
    year: Optional[int] = None
    publication_date: Optional[str] = None
    venue: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    arxiv: Optional[str] = None
    citation_count: Optional[int] = None
    influential_citation_count: Optional[int] = None
    authors: list[dict[str, Any]] = Field(default_factory=list)
    open_access_pdf: Optional[dict[str, Any]] = None
    fields_of_study: list[str] = Field(default_factory=list)
    publication_types: list[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    tldr: Optional[str] = None
    source: str = "semantic_scholar"


class UnifiedEntity(BaseModel):
    entity_id: str
    name: Optional[str] = None
    type: Optional[str] = None
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
