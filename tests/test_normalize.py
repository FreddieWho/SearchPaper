from paper_search.normalize import normalize_entity, normalize_paper, normalize_relation


def test_normalize_paper_minimal():
    raw = {
        "paperId": "abc123",
        "title": "Test Paper",
        "year": 2024,
        "publicationDate": "2024-06-01",
        "venue": "Nature",
        "url": "https://semanticscholar.org/paper/abc123",
        "externalIds": {"DOI": "10.1000/test", "PubMed": "12345678", "ArXiv": "2401.00001"},
        "citationCount": 42,
        "influentialCitationCount": 5,
        "authors": [{"authorId": "a1", "name": "Alice"}, {"name": "Bob"}],
        "openAccessPdf": {"url": "https://pdf.url", "status": "HYBRID"},
        "fieldsOfStudy": ["Biology"],
        "publicationTypes": ["JournalArticle"],
        "abstract": "An abstract.",
        "tldr": {"text": "Too long; didn't read."},
    }
    result = normalize_paper(raw)
    assert result["paper_id"] == "abc123"
    assert result["title"] == "Test Paper"
    assert result["year"] == 2024
    assert result["doi"] == "10.1000/test"
    assert result["pmid"] == "12345678"
    assert result["arxiv"] == "2401.00001"
    assert result["citation_count"] == 42
    assert result["authors"] == [
        {"author_id": "a1", "name": "Alice"},
        {"author_id": None, "name": "Bob"},
    ]
    assert result["open_access_pdf"]["url"] == "https://pdf.url"
    assert result["tldr"] == "Too long; didn't read."
    assert result["source"] == "semantic_scholar"


def test_normalize_entity():
    raw = {"_id": "@GENE_JAK1", "name": "JAK1", "biotype": "gene"}
    result = normalize_entity(raw)
    assert result == {
        "entity_id": "@GENE_JAK1",
        "name": "JAK1",
        "type": "gene",
        "source": "pubtator3",
    }


def test_normalize_entity_legacy_fields():
    raw = {"id": "@GENE_JAK1", "name": "JAK1", "type": "gene"}
    result = normalize_entity(raw)
    assert result == {
        "entity_id": "@GENE_JAK1",
        "name": "JAK1",
        "type": "gene",
        "source": "pubtator3",
    }


def test_normalize_relation_pubtator3_api_format():
    raw = {
        "entity1": {"_id": "@GENE_JAK1"},
        "entity2": {"_id": "@CHEMICAL_Cysteine"},
        "relation_type": "interact",
        "pmids": [],
        "evidence_count": 1,
    }
    result = normalize_relation(raw)
    assert result["entity1"]["entity_id"] == "@GENE_JAK1"
    assert result["entity2"]["entity_id"] == "@CHEMICAL_Cysteine"
    assert result["relation_type"] == "interact"
    assert result["evidence_count"] == 1
    assert result["pmids"] == []
    assert result["evidence_urls"] == []


def test_normalize_relation():
    raw = {
        "entity1": {"id": "@GENE_JAK1", "name": "JAK1", "type": "gene"},
        "entity2": {"id": "@CHEMICAL_Dox", "name": "Doxorubicin", "type": "chemical"},
        "relation_type": "treat",
        "pmids": ["123", "456"],
    }
    result = normalize_relation(raw)
    assert result["relation_type"] == "treat"
    assert len(result["evidence_urls"]) == 2
    assert result["evidence_urls"][0]["pmid"] == "123"
    assert "https://pubmed.ncbi.nlm.nih.gov/123/" in result["evidence_urls"][0]["pubmed_url"]
    assert (
        "https://www.ncbi.nlm.nih.gov/research/pubtator3/publication/123"
        in result["evidence_urls"][0]["pubtator_url"]
    )
