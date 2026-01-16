from __future__ import annotations

from typing import List, Tuple


def build_audio_filter_complex(
    voice_index: int,
    music_index: int | None,
    sfx_indices: list[tuple[int, int]],
    target_duration: float,
    start_offset: float,
    mastering_preset: str,
    ducking_strength: float,
) -> str:
    filters: List[str] = []
    filters.append(
        f"[{voice_index}:a]atrim=start={start_offset:.2f}:duration={target_duration:.2f},"
        "asetpts=PTS-STARTPTS,alimiter=limit=0.98[voice]"
    )

    mix_inputs = ["[voice]"]
    if music_index is not None:
        music_gain = max(0.1, 0.3 - ducking_strength * 0.1)
        filters.append(
            f"[{music_index}:a]atrim=start={start_offset:.2f}:duration={target_duration:.2f},"
            f"asetpts=PTS-STARTPTS,volume={music_gain:.2f},aloop=loop=-1:size=2e+09[music]"
        )
        sc = _sidechain_params(ducking_strength)
        filters.append(f"[music][voice]sidechaincompress={sc}[ducked]")
        mix_inputs.append("[ducked]")

    for index, delay_ms in sfx_indices:
        filters.append(
            f"[{index}:a]volume=0.6,adelay={delay_ms}|{delay_ms},atrim=0:{target_duration:.2f}[sfx{index}]"
        )
        mix_inputs.append(f"[sfx{index}]")

    mix_label = "".join(mix_inputs)
    filters.append(f"{mix_label}amix=inputs={len(mix_inputs)}:duration=longest:dropout_transition=2[mix]")

    mastering_chain = _mastering_chain(mastering_preset)
    filters.append(f"[mix]{mastering_chain}[aout]")
    return ";".join(filters)


def _sidechain_params(strength: float) -> str:
    strength = max(0.0, min(1.0, strength))
    ratio = 4.0 + strength * 8.0
    threshold = 0.12 - strength * 0.05
    attack = 15 + strength * 20
    release = 150 + strength * 150
    return f"threshold={threshold:.2f}:ratio={ratio:.1f}:attack={attack:.0f}:release={release:.0f}"


def _mastering_chain(preset: str) -> str:
    preset = (preset or "hype").lower()
    if preset == "clean":
        eq = "highpass=f=80,lowpass=f=12000"
        comp = "acompressor=threshold=-18dB:ratio=2:attack=6:release=200"
        limiter = "alimiter=limit=0.95"
    elif preset == "aggressive":
        eq = "highpass=f=70,lowpass=f=13000"
        comp = "acompressor=threshold=-22dB:ratio=5:attack=4:release=140"
        limiter = "alimiter=limit=0.9"
    else:
        eq = "highpass=f=75,lowpass=f=12500"
        comp = "acompressor=threshold=-20dB:ratio=3.5:attack=5:release=180"
        limiter = "alimiter=limit=0.92"
    loudnorm = "loudnorm=I=-14:LRA=11:TP=-1.5"
    return f"{eq},{comp},{limiter},{loudnorm}"
