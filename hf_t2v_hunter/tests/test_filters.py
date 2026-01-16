from datetime import datetime, timezone

from hf_t2v_hunter.filters import filter_and_estimate
from hf_t2v_hunter.types import Config, ModelCard, ModelFile


def make_card(license_value=None, tags=None, pipeline_tag="text-to-video"):
    return ModelCard(
        repo_id="test/model",
        model_name="model",
        tags=tags or ["text-to-video"],
        pipeline_tag=pipeline_tag,
        library_name="diffusers",
        license=license_value,
        likes=0,
        downloads=0,
        last_modified=datetime.now(timezone.utc),
        siblings=[ModelFile(name="model.safetensors", size=1000)],
        card_data={},
        readme_text="",
    )


def test_license_blocked():
    config = Config()
    model = make_card(license_value=None)
    compatible, reasons, _ = filter_and_estimate(config, model)
    assert not compatible
    assert "missing_license" in reasons


def test_nsfw_blocked():
    config = Config()
    model = make_card(license_value="apache-2.0", tags=["text-to-video", "nsfw"])
    compatible, reasons, _ = filter_and_estimate(config, model)
    assert not compatible
    assert "nsfw_blocked" in reasons


def test_allow_over_vram_keeps_license_block():
    config = Config(allow_over_vram=True)
    model = make_card(license_value=None)
    compatible, reasons, _ = filter_and_estimate(config, model)
    assert not compatible
    assert "missing_license" in reasons
