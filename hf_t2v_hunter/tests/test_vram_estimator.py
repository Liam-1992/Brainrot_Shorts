from datetime import datetime, timezone

from hf_t2v_hunter.types import Config, ModelCard, ModelFile
from hf_t2v_hunter.vram_estimator import estimate_vram_requirement


def make_card(files, readme_text="", tags=None):
    return ModelCard(
        repo_id="test/model",
        model_name="model",
        tags=tags or ["text-to-video"],
        pipeline_tag="text-to-video",
        library_name="diffusers",
        license="apache-2.0",
        likes=0,
        downloads=0,
        last_modified=datetime.now(timezone.utc),
        siblings=[ModelFile(name=name, size=size) for name, size in files],
        card_data={},
        readme_text=readme_text,
    )


def test_vram_weights_too_large():
    config = Config(max_model_size_gb=1.0)
    files = [("model.safetensors", int(2.2 * (1024**3)))]
    card = make_card(files, readme_text="")
    estimate = estimate_vram_requirement(card, [f[0] for f in files], {}, config)
    assert not estimate.compatible
    assert "weights_too_large" in estimate.reasons


def test_vram_quantized_allows_large():
    config = Config(max_model_size_gb=1.0)
    files = [("model_int8.safetensors", int(2.2 * (1024**3)))]
    card = make_card(files, readme_text="low vram")
    estimate = estimate_vram_requirement(card, [f[0] for f in files], {}, config)
    assert estimate.compatible
