PLUGIN_NAME = "sample_plugin"


def postprocess_script(script: dict, context: dict) -> dict:
    return script


def augment_caption_style(style: dict, context: dict) -> dict:
    return style


def augment_audio_filters(filters: list[str], context: dict) -> list[str]:
    return filters


def augment_video_filters(filters: list[str], context: dict) -> list[str]:
    return filters
