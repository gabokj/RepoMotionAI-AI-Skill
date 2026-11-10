"""Direção musical contextual.
Nada aqui copia música existente: o motor interno sintetiza composição
original, e o prompt externo pede explicitamente uma obra original.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

import numpy as np

from . import config

SECTION_ENERGY = {"intro": 0.28, "verse": 0.45, "build": 0.6, "main": 0.75, "breakdown": 0.35, "outro": 0.5}

EMOTION_WORDS = {
    # chave (pt/en) -> adjetivos em inglês para o prompt e viés de estilo
    "confian": (["confident", "assured"], None),
    "confident": (["confident", "assured"], None),
    "premium": (["refined", "premium", "elegant"], "modern_advertising"),
    "luxo": (["refined", "luxurious", "elegant"], "ambient_cinematic"),
    "elegan": (["elegant", "refined"], None),
    "alegr": (["joyful", "bright"], "light_funk"),
    "divert": (["playful", "light"], "light_funk"),
    "fun": (["playful", "light"], "light_funk"),
    "energ": (["energetic", "lively"], "light_funk"),
    "calm": (["calm", "gentle"], "minimalist_lifestyle"),
    "relax": (["relaxed", "warm"], "minimalist_lifestyle"),
    "aconcheg": (["warm", "cozy"], "minimalist_lifestyle"),
    "inspir": (["inspiring", "hopeful"], "ambient_cinematic"),
    "emo": (["heartfelt", "emotive"], "ambient_cinematic"),
    "curios": (["curious", "intriguing"], "soft_electronic"),
    "tecnol": (["modern", "focused"], "soft_electronic"),
    "foco": (["focused", "clear"], "soft_electronic"),
    "otimis": (["optimistic", "uplifting"], "modern_advertising"),
    "modern": (["modern", "fresh"], None),
}


@dataclass
class MusicBrief:
    duration_s: float
    product: str = ""
    audience: str = ""
    objective: str = ""
    emotion: str = ""
    content_type: str = "ad"
    platform: str = config.DEFAULT_PLATFORM
    has_narration: bool = True
    commercial: bool = True
    fast_cuts: bool = False
    highlights_s: list = field(default_factory=list)
    style: str | None = None
    intensity: float = 0.5           # 0..1 (intensidade geral da música)
    language: str = "pt-BR"
    seed: int | None = None


def _stable_int(*parts):
    h = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _emotion_profile(emotion):
    words, bias = [], []
    e = (emotion or "").lower()
    for key, (adj, style) in EMOTION_WORDS.items():
        if key in e:
            words += adj
            if style:
                bias.append(style)
    seen, uniq = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            uniq.append(w)
    return uniq, bias


def choose_style(brief: MusicBrief):
    """Escolhe o estilo musical e explica o porquê."""
    if brief.style:
        if brief.style not in config.MUSIC_STYLES:
            raise ValueError(f"Estilo musical desconhecido: {brief.style}. "
                             f"Use: {', '.join(config.MUSIC_STYLES)}")
        return brief.style, f"estilo definido pelo usuário ({brief.style})"
    base = config.CONTENT_TYPES.get(brief.content_type, config.CONTENT_TYPES["ad"])["music"]
    _, bias = _emotion_profile(brief.emotion)
    if bias:
        style = bias[0]
        reason = f"emoção '{brief.emotion}' pede {config.MUSIC_STYLES[style]['label']}"
    else:
        style = base
        reason = f"padrão para {config.CONTENT_TYPES.get(brief.content_type, {}).get('label', brief.content_type)}"
    if brief.fast_cuts and style in ("ambient_cinematic", "minimalist_lifestyle"):
        style = "modern_advertising"
        reason += "; cortes rápidos pedem pulso mais definido (Modern Advertising)"
    return style, reason


def best_bpm(boundaries_s, bpm_range, prefer=None):
    """BPM dentro da faixa que deixa as fronteiras de cena mais perto da grade."""
    lo, hi = int(bpm_range[0]), int(bpm_range[1])
    center = prefer if prefer is not None else (lo + hi) / 2
    if not boundaries_s:
        return int(round(center))
    best = None
    for bpm in range(lo, hi + 1):
        beat = 60 / bpm
        err = float(np.mean([min(t / beat % 1, 1 - t / beat % 1) ** 2 for t in boundaries_s]))
        err += 0.02 * ((bpm - center) / max(1, hi - lo)) ** 2
        if best is None or err < best[0]:
            best = (err, bpm)
    return best[1]


def plan_arrangement(duration_s, bpm, has_narration=True, highlights_s=None, intensity=0.5,
                     narration_regions=None):
    """Seções musicais adaptadas à duração (não apenas um loop cortado).
    """
    d = float(duration_s)
    bar = 240.0 / bpm
    if d <= 12:
        plan = [("intro", 0.0), ("main", min(0.18, bar / d))]
    elif d <= 20:
        plan = [("intro", 0.0), ("verse", 0.12), ("main", 0.5)]
    elif d <= 40:
        plan = [("intro", 0.0), ("verse", 0.09), ("build", 0.38), ("main", 0.52), ("outro", 0.88)]
    else:
        plan = [("intro", 0.0), ("verse", 0.07), ("verse", 0.26), ("build", 0.44), ("main", 0.54),
                ("breakdown", 0.72), ("main", 0.8), ("outro", 0.93)]
    # destaque visual principal puxa o início do "main" (quando cabe no terço central)
    if highlights_s:
        mid = [h for h in highlights_s if 0.3 * d <= h <= 0.8 * d]
        if mid:
            for i, (sec, frac) in enumerate(plan):
                if sec == "main":
                    plan[i] = (sec, mid[0] / d)
                    break
    # encaixa na grade de compassos, mantendo ordem e ao menos 1 compasso por seção
    starts = []
    for i, (sec, frac) in enumerate(plan):
        t = 0.0 if i == 0 else round(frac * d / bar) * bar
        if starts and t <= starts[-1][1] + bar * 0.99:
            t = starts[-1][1] + bar
        if t < d - bar * 0.5:
            starts.append((sec, t))
    sections = []
    for i, (sec, t) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else d
        k = 0.6 + 0.8 * float(np.clip(intensity, 0, 1))
        energy = float(np.clip(SECTION_ENERGY[sec] * k, 0.12, 0.95))
        if sec == "verse" and i > 1 and starts[i - 1][0] == "verse":
            energy = min(0.95, energy + 0.08)  # variação ganha corpo
        narration = has_narration
        if narration_regions is not None:
            covered = sum(max(0.0, min(end, b) - max(t, a)) for a, b in narration_regions)
            narration = covered >= 0.35 * (end - t)
        if narration:
            energy = max(0.12, energy - 0.08)
        sections.append({"section": sec, "start_s": round(t, 4), "end_s": round(end, 4),
                         "energy": round(energy, 3), "narration": bool(narration)})
    return sections


def _structure_text(sections, duration_s):
    parts = []
    names = {"intro": "soft intro", "verse": "main theme", "build": "gentle build",
             "main": "full main section", "breakdown": "breathing breakdown", "outro": "resolving outro"}
    for s in sections:
        parts.append(f"{names[s['section']]} {s['start_s']:.0f}-{s['end_s']:.0f}s")
    return f"{duration_s:.0f}-second structure: " + ", ".join(parts)


def build_prompt(brief: MusicBrief, direction):
    """Prompt musical específico do projeto (inglês, melhor suportado pelos modelos)."""
    st = config.MUSIC_STYLES[direction["style"]]
    adjectives, _ = _emotion_profile(brief.emotion)
    mood = ", ".join(adjectives[:3]) if adjectives else st["mood"]
    label = config.CONTENT_TYPES.get(brief.content_type, {}).get("label", brief.content_type)
    content_en = {
        "Anúncio": "advertisement", "Publi de produto": "sponsored product video",
        "Publi de aplicativo": "sponsored app video", "Vídeo de aplicativo": "app promo",
        "Apresentação de software": "software presentation", "Apresentação de repositório":
        "open-source project presentation", "Vídeo demonstrativo": "product demo",
        "Vídeo explicativo": "explainer video", "Vídeo institucional": "brand film",
        "Conteúdo para redes": "social media video", "Lifestyle": "lifestyle video",
        "Conteúdo narrativo": "narrative video",
    }.get(label, "video")
    sentences = [
        f"Create an original {mood} instrumental for a {brief.duration_s:.0f}-second {content_en}"
        + (f" about {brief.product}" if brief.product else "")
        + (f", for {brief.audience}" if brief.audience else "") + ".",
        f"Style: {st['label']} — {', '.join(st['instrumentation'])}; texture {st['texture']}.",
        f"Around {direction['bpm']} BPM in {direction['key']} {direction['mode']}, "
        f"{_energy_words(brief.intensity)} energy that grows with intention rather than constantly.",
        _structure_text(direction["sections"], brief.duration_s) + ".",
    ]
    if brief.has_narration:
        sentences.append("Leave clear room for a voice-over: sparse mid-range, no busy lead melody "
                         "while the narrator speaks, keep the motif for the gaps and the ending.")
    if brief.fast_cuts:
        sentences.append("Clear rhythmic pulse so quick edits can land on the beat.")
    else:
        sentences.append("Smooth, flowing transitions between sections; no hard stops.")
    if brief.highlights_s:
        hl = ", ".join(f"{h:.1f}s" for h in brief.highlights_s[:4])
        sentences.append(f"Subtle musical lift at {hl} to support visual highlights.")
    ending = ("End on a resolved tonic chord with a natural short tail — a complete ending, "
              "not a fade-in-progress or a cut.")
    sentences.append(ending)
    sentences.append("Polished, warm and clean mix with controlled low end and soft highs. "
                     "Instrumental only, no vocals. Original composition: do not imitate any existing "
                     "song, artist, melody or recognizable chord progression."
                     + (" Suitable for commercial advertising." if brief.commercial else ""))
    prompt = " ".join(sentences)
    short = (f"original {st['label'].lower()} instrumental, {mood}, "
             f"{', '.join(st['instrumentation'][:3])}, {direction['bpm']} bpm, "
             f"{'room for voice-over, ' if brief.has_narration else ''}resolved ending, no vocals")
    negative = ", ".join(config.MUSIC_AVOID)
    return {"prompt": prompt, "short_prompt": short[:200], "negative_prompt": negative}


def _energy_words(intensity):
    if intensity < 0.35:
        return "low, gentle"
    if intensity < 0.65:
        return "moderate"
    return "lively but controlled"


def plan_music(brief: MusicBrief, scene_boundaries_s=None, narration_regions=None):
    """Direção musical completa (dict serializável)."""
    if brief.duration_s <= 0:
        raise ValueError("duration_s deve ser maior que zero")
    style, why = choose_style(brief)
    st = config.MUSIC_STYLES[style]
    lo, hi = st["bpm"]
    prefer = hi - (hi - lo) * 0.25 if brief.fast_cuts else lo + (hi - lo) * (0.3 + 0.4 * brief.intensity)
    bpm = best_bpm(scene_boundaries_s or [], (lo, hi), prefer)
    seed = brief.seed if brief.seed is not None else _stable_int(brief.product, brief.objective, style) % 10000
    key = st["keys"][_stable_int(brief.product, style) % len(st["keys"])]
    mode = st["mode"]
    adjectives, _ = _emotion_profile(brief.emotion)
    if mode == "minor" and any(a in adjectives for a in ("joyful", "optimistic", "bright", "uplifting")):
        mode = "dorian"  # mantém a cor do estilo, mas mais luminoso
    sections = plan_arrangement(brief.duration_s, bpm, brief.has_narration, brief.highlights_s,
                                brief.intensity, narration_regions)
    direction = {
        "style": style, "style_label": st["label"], "bpm": bpm, "key": key, "mode": mode,
        "seed": seed, "intensity": brief.intensity, "sections": sections, "ending": "resolve",
        "rationale": [why,
                      f"BPM {bpm} dentro da faixa {lo}-{hi} do estilo, ajustado às fronteiras de cena",
                      f"tonalidade {key} {mode} (estável por projeto: mesma marca, mesma cor)",
                      f"{len(sections)} seções para {brief.duration_s:.0f}s com final resolvido"],
    }
    direction.update(build_prompt(brief, direction))
    return direction


def to_timeline(direction, duration_s, fps=60, events=None, music_level=0.9, sfx_level=0.7,
                loudness=-16.0):
    """Converte a direção em timeline JSON do `sfx_kit` (mesmos quadros do vídeo)."""
    scenes = []
    total = round(duration_s * fps)
    for s in direction["sections"]:
        a = round(s["start_s"] * fps)
        b = min(total, round(s["end_s"] * fps))
        if b > a:
            scenes.append({"start_frame": a, "end_frame": b, "section": s["section"],
                           "energy": s["energy"], "narration": s["narration"],
                           "mood": "uplifting" if direction["mode"] == "major" else "cinematic"})
            scenes[-1].pop("mood")  # o estilo define a progressão; mood explícito sobrescreveria
    return {
        "duration": round(duration_s, 4), "fps": fps, "seed": direction["seed"], "bpm": direction["bpm"],
        "key": direction["key"], "mode": direction["mode"], "style": direction["engine_style"]
        if "engine_style" in direction else config.MUSIC_STYLES[direction["style"]]["engine_style"],
        "ending": direction.get("ending", "resolve"), "music_level": music_level, "sfx_level": sfx_level,
        "loudness": loudness, "scenes": scenes, "events": events or [],
    }


# ---------------------------------------------------------------------------
# Licenciamento: toda trilha usada precisa de procedência registrada
# ---------------------------------------------------------------------------
LICENSE_FIELDS = ("source", "license", "commercial_use", "url", "attribution", "verified_by", "notes")


def internal_license(track_path, direction=None):
    return {
        "file": str(track_path),
        "source": "sfx_kit — síntese procedural original deste projeto (sem samples de terceiros)",
        "license": "obra própria gerada pelo projeto",
        "commercial_use": True,
        "url": None, "attribution": None, "verified_by": "gerada localmente",
        "notes": f"estilo {direction['style']} seed {direction['seed']}" if direction else None,
    }


def check_license(manifest):
    """Problemas de licenciamento (lista vazia = documentado e utilizável)."""
    issues = []
    if not manifest:
        return ["trilha sem manifesto de licença: registre fonte, licença e uso comercial"]
    for f in ("source", "license", "commercial_use"):
        if manifest.get(f) in (None, ""):
            issues.append(f"manifesto de licença sem o campo '{f}'")
    if manifest.get("commercial_use") is False:
        issues.append("a licença registrada NÃO permite uso comercial")
    lic = str(manifest.get("license", "")).lower()
    if any(k in lic for k in ("desconhecida", "unknown", "youtube", "internet")):
        issues.append("licença não verificada: não trate música encontrada na internet como livre")
    if "by" in lic.replace("-", " ").split() or "cc by" in lic or "cc-by" in lic:
        if not manifest.get("attribution"):
            issues.append("licença exige atribuição, mas 'attribution' está vazio")
    if "nc" in lic.replace("-", " ").split() and manifest.get("commercial_use"):
        issues.append("licença NC (não comercial) marcada como uso comercial")
    if manifest.get("source", "").startswith("sfx_kit"):
        return issues
    if not manifest.get("verified_by"):
        issues.append("licença externa sem 'verified_by' (quem conferiu os termos e quando)")
    return issues


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def brief_from_dict(d):
    allowed = set(MusicBrief.__dataclass_fields__)
    return MusicBrief(**{k: v for k, v in d.items() if k in allowed})


def brief_to_dict(b: MusicBrief):
    return asdict(b)

