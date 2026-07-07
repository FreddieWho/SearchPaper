import asyncio
import json
import os
from datetime import UTC, datetime

from searchpaper.engine import SearchEngine
from searchpaper.schemas import SearchFilters
from searchpaper.sources.pubtator3 import PubTator3Adapter


async def main():
    engine = SearchEngine()

    results = {
        "run_at": datetime.now(UTC).isoformat(),
        "tests": {},
    }

    print("[1/3] Multi-source search...")
    try:
        result = await engine.search(
            "PD-1 immunotherapy hepatocellular carcinoma",
            filters=SearchFilters(limit=3),
        )
        data = result.data if hasattr(result, "data") else result.get("data", {})
        works = data.get("works", [])
        results["tests"]["search"] = {
            "status": "ok",
            "work_count": len(works),
            "warnings": data.get("warnings", []),
        }
    except Exception as e:
        results["tests"]["search"] = {"status": "error", "message": str(e)}

    adapter = PubTator3Adapter()
    try:
        print("[2/3] PubTator entity autocomplete (JAK1)...")
        entity_res = await adapter.find_entity("JAK1", limit=5)
        items = entity_res.get("items", [])
        results["tests"]["pubtator_entity"] = {
            "status": "ok",
            "result_count": len(items),
        }

        print("[3/3] PubTator relations (JAK1 negative_correlate chemical)...")
        signals = await adapter.find_relations("@GENE_JAK1", "chemical", "negative_correlate", limit=5)
        results["tests"]["pubtator_relations"] = {
            "status": "ok",
            "signal_count": len(signals),
        }
    except Exception as e:
        results["tests"]["pubtator"] = {"status": "error", "message": str(e)}
    finally:
        await adapter.aclose()

    out_path = os.path.join(os.path.dirname(__file__), "..", "examples", "smoke_test_output.json")
    out_path = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved results to {out_path}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
