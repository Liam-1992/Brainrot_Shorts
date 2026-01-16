from __future__ import annotations

import json
from typing import Any, Dict

from .models import GenerateRequest, ScriptBeat, ScriptOutput
from .template_manager import Template


def _build_user_prompt(req: GenerateRequest, template: Template, forced_hook: str | None = None) -> str:
    schema = json.dumps(template.schema, indent=2)
    beat_rules = template.beat_rules
    series_context = ""
    if req.series_context:
        series_context = f"Series context: {json.dumps(req.series_context)}\n"
    hook_constraint = ""
    if forced_hook:
        hook_constraint = f"Hook constraint (must use verbatim): {forced_hook}\n"
    return (
        "Write a short vertical video script with 1-3 second beats.\n"
        f"Topic: {req.topic_prompt}\n"
        f"Style: {template.style}\n"
        f"Target duration: {req.duration_seconds} seconds.\n"
        f"{series_context}"
        f"{hook_constraint}"
        f"Beat rules: {beat_rules}\n\n"
        "Output strict JSON in the exact schema:\n"
        f"{schema}\n\n"
        "Ensure beats are 1-3 seconds apart and return ONLY JSON."
    )


def _extract_json(raw: str) -> Dict[str, Any]:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM output")
    payload = raw[start : end + 1]
    return json.loads(payload)


def _generate_llama_cpp(
    settings, system_prompt: str, prompt: str, seed: int | None, model_path: str | None = None
) -> str:
    from llama_cpp import Llama

    resolved = model_path or settings.resolve_llm_model_path()
    if not resolved:
        raise ValueError("LLM model not found. Set LLM_MODEL_PATH or place a .gguf in models/llm.")

    llm = Llama(
        model_path=str(resolved),
        n_ctx=settings.LLM_CTX,
        n_gpu_layers=settings.LLM_N_GPU_LAYERS,
    )
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        seed=seed,
    )
    return response["choices"][0]["message"]["content"]


def _generate_transformers(
    settings, system_prompt: str, prompt: str, model_path: str | None = None
) -> str:
    from transformers import AutoModelForCausalLM, AutoTokenizer

    resolved = model_path or settings.LLM_MODEL_PATH
    if not resolved:
        raise ValueError("LLM_MODEL_PATH is required for transformers backend")

    tokenizer = AutoTokenizer.from_pretrained(resolved)
    model = AutoModelForCausalLM.from_pretrained(
        resolved, device_map="auto"
    )
    full_prompt = f"{system_prompt}\n\n{prompt}"
    inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=settings.LLM_MAX_TOKENS,
        temperature=settings.LLM_TEMPERATURE,
        do_sample=True,
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)


def _normalize_script(payload: Dict[str, Any]) -> ScriptOutput:
    beats = payload.get("beats") or []
    normalized_beats = []
    for beat in beats:
        try:
            normalized_beats.append(
                ScriptBeat(
                    t=float(beat.get("t", 0.0)),
                    text=str(beat.get("text", "")).strip(),
                    on_screen=str(beat.get("on_screen", "")).strip(),
                    emphasis=beat.get("emphasis"),
                )
            )
        except Exception:
            continue
    if not normalized_beats:
        fallback_text = str(payload.get("hook") or payload.get("title") or "")
        normalized_beats = [ScriptBeat(t=0.0, text=fallback_text, on_screen=fallback_text)]
    else:
        needs_retime = False
        last_t = -1.0
        for beat in normalized_beats:
            if beat.t < 0 or beat.t <= last_t:
                needs_retime = True
                break
            last_t = beat.t
        if needs_retime:
            spacing = 2.2
            for index, beat in enumerate(normalized_beats):
                beat.t = round(index * spacing, 2)
    payload["beats"] = normalized_beats
    if not payload.get("full_voiceover_text"):
        payload["full_voiceover_text"] = " ".join(
            beat.text for beat in normalized_beats if beat.text
        ).strip()
    if not payload.get("keywords"):
        payload["keywords"] = []
    return ScriptOutput(**payload)


def _apply_safe_rewrites(text: str, forbidden_words: list[str], safe_rewrites: dict) -> str:
    output = text
    for word in forbidden_words:
        if word in output:
            replacement = safe_rewrites.get(word, "")
            output = output.replace(word, replacement)
    return output


def generate_text(
    settings,
    system_prompt: str,
    prompt: str,
    seed: int | None,
    model_paths: list[str] | None = None,
) -> str:
    backends = [settings.LLM_BACKEND]
    if settings.LLM_BACKEND == "llama_cpp":
        backends.append("transformers")

    paths = model_paths or [None]
    last_error: Exception | None = None
    for backend in backends:
        for path in paths:
            try:
                if backend == "llama_cpp":
                    return _generate_llama_cpp(settings, system_prompt, prompt, seed, model_path=path)
                if backend == "transformers":
                    return _generate_transformers(settings, system_prompt, prompt, model_path=path)
                raise ValueError(f"Unknown LLM_BACKEND '{backend}'")
            except Exception as exc:
                last_error = exc
                continue
    raise RuntimeError(f"Failed to generate text: {last_error}")


def generate_script(
    settings,
    req: GenerateRequest,
    template: Template,
    plugin_manager,
    model_paths: list[str] | None = None,
    forced_hook: str | None = None,
) -> ScriptOutput:
    prompt = _build_user_prompt(req, template, forced_hook=forced_hook)
    last_error: Exception | None = None
    system_prompt = template.system_prompt

    backends = [settings.LLM_BACKEND]
    if settings.LLM_BACKEND == "llama_cpp":
        backends.append("transformers")
    paths = model_paths or [None]

    for backend in backends:
        for path in paths:
            try:
                if backend == "llama_cpp":
                    raw = _generate_llama_cpp(settings, system_prompt, prompt, req.seed, model_path=path)
                elif backend == "transformers":
                    raw = _generate_transformers(settings, system_prompt, prompt, model_path=path)
                else:
                    raise ValueError(f"Unknown LLM_BACKEND '{backend}'")
                try:
                    payload = _extract_json(raw)
                except Exception:
                    retry_prompt = prompt + "\nReturn ONLY valid JSON with no extra text."
                    if backend == "llama_cpp":
                        raw = _generate_llama_cpp(settings, system_prompt, retry_prompt, req.seed, model_path=path)
                    else:
                        raw = _generate_transformers(settings, system_prompt, retry_prompt, model_path=path)
                    payload = _extract_json(raw)
                script = _normalize_script(payload)
                if forced_hook:
                    script.hook = forced_hook
                    if script.beats:
                        script.beats[0].text = forced_hook
                        script.beats[0].on_screen = forced_hook
                    script.full_voiceover_text = " ".join(
                        beat.text for beat in script.beats if beat.text
                    ).strip()
                if template.forbidden_words:
                    script.full_voiceover_text = _apply_safe_rewrites(
                        script.full_voiceover_text,
                        template.forbidden_words,
                        template.safe_rewrites,
                    )
                    script.hook = _apply_safe_rewrites(
                        script.hook, template.forbidden_words, template.safe_rewrites
                    )
                    script.title = _apply_safe_rewrites(
                        script.title, template.forbidden_words, template.safe_rewrites
                    )
                    for beat in script.beats:
                        beat.text = _apply_safe_rewrites(
                            beat.text, template.forbidden_words, template.safe_rewrites
                        )
                        beat.on_screen = _apply_safe_rewrites(
                            beat.on_screen, template.forbidden_words, template.safe_rewrites
                        )
                context = {"template": template.name, "style": template.style}
                script_data = plugin_manager.apply_script(script.model_dump(), context)
                return ScriptOutput(**script_data)
            except Exception as exc:
                last_error = exc
                continue

    raise RuntimeError(f"Failed to generate script: {last_error}")
