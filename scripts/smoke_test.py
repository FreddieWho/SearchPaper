import asyncio
import json
import os
from datetime import UTC, datetime

from paper_search.cache import Cache
from paper_search.config import load_config
from paper_search.pubtator3 import PubTator3Client
from paper_search.semantic_scholar import SemanticScholarClient


async def main():
    cfg = load_config()
    cache_path = cfg.get("cache_path", "/tmp/paper_search_smoke.db")
    api_key = cfg.get("semantic_scholar_api_key")

    cache = Cache(db_path=cache_path)
    cache.clear()
    s2 = SemanticScholarClient(api_key=api_key, cache=cache)
    pt = PubTator3Client(cache=cache)

    results = {
        "run_at": datetime.now(UTC).isoformat(),
        "tests": {},
    }

    print("[1/3] Semantic Scholar search...")
    try:
        r1 = await s2.search_papers(
            "PD-1 immunotherapy hepatocellular carcinoma single-cell",
            limit=5,
            include_abstract=False,
        )
        results["tests"]["s2_search"] = {
            "status": "ok",
            "result_count": len(r1.get("items", [])),
            "from_cache": r1.get("from_cache"),
            "warnings": r1.get("warnings", []),
        }
        # verify cache hit on second call
        r1_cached = await s2.search_papers(
            "PD-1 immunotherapy hepatocellular carcinoma single-cell",
            limit=5,
            include_abstract=False,
        )
        results["tests"]["s2_search_cached"] = {
            "status": "ok",
            "from_cache": r1_cached.get("from_cache"),
        }
    except Exception as e:
        results["tests"]["s2_search"] = {"status": "error", "message": str(e)}

    print("[2/3] PubTator entity autocomplete (JAK1)...")
    try:
        r2 = await pt.find_entity("JAK1", limit=5)
        results["tests"]["pubtator_entity"] = {
            "status": "ok",
            "result_count": len(r2.get("items", [])),
            "from_cache": r2.get("from_cache"),
            "warnings": r2.get("warnings", []),
        }
    except Exception as e:
        results["tests"]["pubtator_entity"] = {"status": "error", "message": str(e)}

    print("[3/3] PubTator relations (JAK1 negative_correlate chemical)...")
    try:
        r3 = await pt.find_relations("@GENE_JAK1", "chemical", "negative_correlate", limit=5)
        results["tests"]["pubtator_relations"] = {
            "status": "ok",
            "result_count": len(r3.get("items", [])),
            "from_cache": r3.get("from_cache"),
            "warnings": r3.get("warnings", []),
        }
    except Exception as e:
        results["tests"]["pubtator_relations"] = {"status": "error", "message": str(e)}

    out_path = os.path.join(os.path.dirname(__file__), "..", "examples", "smoke_test_output.json")
    out_path = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved results to {out_path}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
