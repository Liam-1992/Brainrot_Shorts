from datetime import datetime, timedelta, timezone

from hf_t2v_hunter.scoring import rank_models
from hf_t2v_hunter.types import Config, ModelCard, ModelFile, ScoredModel, VramEstimate


def make_scored(repo_id, downloads, likes, days_ago):
    card = ModelCard(
        repo_id=repo_id,
        model_name=repo_id.split("/")[-1],
        tags=["text-to-video"],
        pipeline_tag="text-to-video",
        library_name="diffusers",
        license="apache-2.0",
        likes=likes,
        downloads=downloads,
        last_modified=datetime.now(timezone.utc) - timedelta(days=days_ago),
        siblings=[ModelFile(name="model_index.json", size=1)],
        card_data={},
        readme_text="",
    )
    estimate = VramEstimate(compatible=True, required_gb=8.0, reasons=[], hints={})
    return ScoredModel(model=card, score=0, reasons=[], vram_estimate=estimate)


def test_scoring_prefers_downloads():
    config = Config()
    a = make_scored("a/model", downloads=1000, likes=10, days_ago=10)
    b = make_scored("b/model", downloads=10, likes=200, days_ago=10)
    ranked = rank_models([a, b], config)
    assert ranked[0].model.repo_id == "a/model"
