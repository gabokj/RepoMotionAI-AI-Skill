"""Configuração centralizada da produção audiovisual.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Modos de produção (o usuário escolhe um; "custom" respeita apenas overrides)
# ---------------------------------------------------------------------------
PRODUCTION_MODES = {
    "auto": {
        "label": "Automático",
        "description": "A IA decide formato, ritmo, música e voz a partir do conteúdo.",
        "bias": {},
    },
    "custom": {
        "label": "Personalizado",
        "description": "Parâmetros do usuário têm prioridade; o resto é inferido.",
        "bias": {},
    },
    "commercial": {
        "label": "Comercial",
        "description": "Anúncios e publis: valor claro, ritmo moderado, CTA.",
        "bias": {"editing": "moderate", "music_intensity": 0.55, "cta": True},
    },
    "technical": {
        "label": "Técnico",
        "description": "Demonstrações e explicações: clareza, telas reais, ritmo calmo.",
        "bias": {"editing": "calm", "music_intensity": 0.35, "cta": False},
    },
    "cinematic": {
        "label": "Cinematográfico",
        "description": "Narrativa visual e atmosfera: planos longos, crescimento controlado.",
        "bias": {"editing": "calm", "music_intensity": 0.5, "cta": False},
    },
}

# ---------------------------------------------------------------------------
# Plataformas -> formato, resolução, fps e alvo de loudness
# ---------------------------------------------------------------------------
PLATFORMS = {
    "tiktok":    {"aspect": "9:16", "size": (1080, 1920), "fps": 60, "lufs": -14.0, "max_s": 180,
                  "safe": {"top": 220, "bottom": 420, "left": 60, "right": 140}},
    "reels":     {"aspect": "9:16", "size": (1080, 1920), "fps": 60, "lufs": -14.0, "max_s": 90,
                  "safe": {"top": 220, "bottom": 420, "left": 60, "right": 140}},
    "shorts":    {"aspect": "9:16", "size": (1080, 1920), "fps": 60, "lufs": -14.0, "max_s": 60,
                  "safe": {"top": 200, "bottom": 380, "left": 60, "right": 120}},
    "stories":   {"aspect": "9:16", "size": (1080, 1920), "fps": 30, "lufs": -14.0, "max_s": 60,
                  "safe": {"top": 250, "bottom": 340, "left": 60, "right": 60}},
    "feed":      {"aspect": "4:5", "size": (1080, 1350), "fps": 30, "lufs": -14.0, "max_s": 60,
                  "safe": {"top": 80, "bottom": 80, "left": 60, "right": 60}},
    "square":    {"aspect": "1:1", "size": (1080, 1080), "fps": 30, "lufs": -14.0, "max_s": 60,
                  "safe": {"top": 60, "bottom": 60, "left": 60, "right": 60}},
    "youtube":   {"aspect": "16:9", "size": (1920, 1080), "fps": 30, "lufs": -14.0, "max_s": 900,
                  "safe": {"top": 60, "bottom": 90, "left": 96, "right": 96}},
    "linkedin":  {"aspect": "16:9", "size": (1920, 1080), "fps": 30, "lufs": -14.0, "max_s": 600,
                  "safe": {"top": 60, "bottom": 90, "left": 96, "right": 96}},
    "website":   {"aspect": "16:9", "size": (1920, 1080), "fps": 30, "lufs": -16.0, "max_s": 900,
                  "safe": {"top": 54, "bottom": 54, "left": 96, "right": 96}},
    "github":    {"aspect": "16:9", "size": (1920, 1080), "fps": 30, "lufs": -16.0, "max_s": 600,
                  "safe": {"top": 54, "bottom": 54, "left": 96, "right": 96}},
}
DEFAULT_PLATFORM = "reels"

# ---------------------------------------------------------------------------
# Tipos de conteúdo -> estratégia padrão
# ---------------------------------------------------------------------------
CONTENT_TYPES = {
    "ad": {
        "label": "Anúncio", "platform": "reels", "template_family": "ad",
        "music": "modern_advertising", "voice": "commercial_premium", "editing": "moderate",
        "cta": True, "grammar": "B",
    },
    "publi_product": {
        "label": "Publi de produto", "platform": "reels", "template": "publi_product",
        "music": "minimalist_lifestyle", "voice": "conversational", "editing": "moderate",
        "cta": True, "grammar": "D",
    },
    "publi_app": {
        "label": "Publi de aplicativo", "platform": "reels", "template": "publi_app",
        "music": "soft_electronic", "voice": "conversational", "editing": "moderate",
        "cta": True, "grammar": "C",
    },
    "app_promo": {
        "label": "Vídeo de aplicativo", "platform": "reels", "template_family": "ad",
        "music": "soft_electronic", "voice": "technological", "editing": "moderate",
        "cta": True, "grammar": "B",
    },
    "software_presentation": {
        "label": "Apresentação de software", "platform": "youtube", "template": "software_presentation",
        "music": "soft_electronic", "voice": "technological", "editing": "calm",
        "cta": False, "grammar": "C",
    },
    "repo_presentation": {
        "label": "Apresentação de repositório", "platform": "github", "template": "software_presentation",
        "music": "ambient_cinematic", "voice": "technological", "editing": "calm",
        "cta": False, "grammar": "C",
    },
    "demo": {
        "label": "Vídeo demonstrativo", "platform": "youtube", "template": "demo",
        "music": "soft_electronic", "voice": "technological", "editing": "calm",
        "cta": False, "grammar": "C",
    },
    "explainer": {
        "label": "Vídeo explicativo", "platform": "youtube", "template": "explainer",
        "music": "ambient_cinematic", "voice": "narrative", "editing": "calm",
        "cta": False, "grammar": "A",
    },
    "institutional": {
        "label": "Vídeo institucional", "platform": "linkedin", "template": "institutional",
        "music": "ambient_cinematic", "voice": "commercial_premium", "editing": "calm",
        "cta": False, "grammar": "A",
    },
    "social": {
        "label": "Conteúdo para redes", "platform": "tiktok", "template_family": "ad",
        "music": "light_funk", "voice": "conversational", "editing": "dynamic",
        "cta": True, "grammar": "D",
    },
    "lifestyle": {
        "label": "Lifestyle", "platform": "reels", "template": "publi_product",
        "music": "minimalist_lifestyle", "voice": "lifestyle", "editing": "moderate",
        "cta": True, "grammar": "D",
    },
    "narrative": {
        "label": "Conteúdo narrativo", "platform": "youtube", "template": "explainer",
        "music": "ambient_cinematic", "voice": "narrative", "editing": "calm",
        "cta": False, "grammar": "A",
    },
}

# ---------------------------------------------------------------------------
# Estilos de edição: duração média de plano, transições e câmera permitidas
# ---------------------------------------------------------------------------
EDITING_STYLES = {
    "calm": {
        "label": "Calmo",
        "shot_s": (3.5, 7.0),
        "transitions": ["crossfade", "morph", "cut"],
        "camera": ["slow_drift", "slow_push_in", "pan_left", "pan_right", "static_parallax"],
        "zoom_budget": 0.35,
        "micro_event_s": (1.0, 2.0),
    },
    "moderate": {
        "label": "Moderado",
        "shot_s": (2.0, 4.0),
        "transitions": ["morph", "zoom_through", "cut", "crossfade"],
        "camera": ["slow_drift", "push_in", "pan_left", "pan_right", "orbit_tilt", "static_parallax"],
        "zoom_budget": 0.45,
        "micro_event_s": (0.6, 1.5),
    },
    "dynamic": {
        "label": "Dinâmico",
        "shot_s": (1.2, 2.6),
        "transitions": ["cut", "zoom_punch", "morph", "whip_pan"],
        "camera": ["push_in", "pan_left", "pan_right", "orbit_tilt", "slow_drift"],
        "zoom_budget": 0.5,
        "micro_event_s": (0.5, 1.0),
    },
}

# Transições: duração em segundos e o efeito sonoro coerente (ou None)
TRANSITIONS = {
    "none":         {"dur": 0.0,  "sfx": None},
    "cut":          {"dur": 0.0,  "sfx": None},
    "crossfade":    {"dur": 0.45, "sfx": None},
    "morph":        {"dur": 0.5,  "sfx": "whoosh"},
    "zoom_through": {"dur": 0.4,  "sfx": "whoosh"},
    "zoom_punch":   {"dur": 0.3,  "sfx": "whoosh"},
    "whip_pan":     {"dur": 0.25, "sfx": "whoosh"},
    "fade_out":     {"dur": 0.6,  "sfx": None},
}

# ---------------------------------------------------------------------------
# Estilos musicais (direção + parâmetros do motor `sfx_kit`)
# ---------------------------------------------------------------------------
MUSIC_STYLES = {
    "modern_advertising": {
        "label": "Modern Advertising",
        "engine_style": "modern_advertising",
        "bpm": (96, 112), "mode": "major", "keys": ["F", "G", "A", "D"],
        "instrumentation": ["warm electric piano", "soft synth pad", "clean round bass",
                            "light pop percussion", "subtle bell motif"],
        "texture": "polished, spacious, modern",
        "mood": "refined, optimistic, confident",
        "energy": "moderate",
        "use_for": ["anúncios de produto", "aplicativos", "serviços"],
    },
    "soft_electronic": {
        "label": "Soft Electronic",
        "engine_style": "soft_electronic",
        "bpm": (100, 118), "mode": "major", "keys": ["C", "D", "E", "A"],
        "instrumentation": ["airy atmospheric pads", "soft plucked synth arpeggio",
                            "warm sub bass", "gentle electronic kick", "soft shaker and rim"],
        "texture": "airy, clean, digital but warm",
        "mood": "curious, modern, focused",
        "energy": "low to moderate",
        "use_for": ["software", "apps", "apresentações técnicas"],
    },
    "minimalist_lifestyle": {
        "label": "Minimalist Lifestyle",
        "engine_style": "minimalist_lifestyle",
        "bpm": (80, 96), "mode": "major", "keys": ["C", "G", "D", "F"],
        "instrumentation": ["soft felt piano", "clean fingerpicked guitar",
                            "discreet shaker", "light rim clicks", "warm upright-style bass"],
        "texture": "natural, organic, intimate",
        "mood": "relaxed, warm, pleasant",
        "energy": "low",
        "use_for": ["publis", "produtos do dia a dia", "lifestyle"],
    },
    "ambient_cinematic": {
        "label": "Ambient Cinematic",
        "engine_style": "ambient_cinematic",
        "bpm": (70, 90), "mode": "minor", "keys": ["D", "E", "A", "C"],
        "instrumentation": ["evolving ambient pads", "sparse piano", "low warm drone",
                            "soft swells", "restrained cinematic pulse"],
        "texture": "wide, layered, gradually evolving",
        "mood": "premium, contemplative, controlled emotional growth",
        "energy": "low growing to moderate",
        "use_for": ["vídeos institucionais", "estética premium", "explicativos"],
    },
    "light_funk": {
        "label": "Light Funk / Groove",
        "engine_style": "light_funk",
        "bpm": (100, 115), "mode": "minor", "keys": ["E", "A", "D", "G"],
        "instrumentation": ["smooth syncopated bass", "muted clean guitar chops",
                            "electric piano stabs", "balanced groove drums with ghost notes"],
        "texture": "tight, warm, rhythmic",
        "mood": "playful, engaging, commercially upbeat without excess",
        "energy": "moderate to high",
        "use_for": ["anúncios dinâmicos", "redes sociais"],
    },
}

# Termos que deixam a música genérica ou competitiva com a voz
MUSIC_AVOID = [
    "epic trailer drums", "aggressive supersaw synths", "heavy EDM drops",
    "dubstep wobble", "distorted guitars", "busy lead melodies over the voice",
    "generic corporate ukulele and claps", "vocals or vocal chops",
    "sudden stops or abrupt endings", "imitation of any existing song or artist",
]

# ---------------------------------------------------------------------------
# Perfis de voz: parâmetros reais por provedor (não apenas nomes)
# ---------------------------------------------------------------------------
VOICE_PROFILES = {
    "commercial_premium": {

        "elevenlabs": {"stability": 0.55, "similarity_boost": 0.80, "style": 0.22,
                       "use_speaker_boost": True, "speed": 0.96},
        "openai_voice": "onyx",
        "instructions": (
            "Professional premium advertising voice-over. Calm, confident and warm, never salesy. "
            "Medium-low pitch, unhurried pace, clean diction. Let key product words land with a "
            "subtle lift, then relax. Natural breaths between ideas. No telemarketing energy, no "
            "exaggerated smiles in the voice."
        ),
    },
    "conversational": {
        "label": "Conversacional",
        "wpm": 158, "rate": 1.03, "pitch_st": 0.0, "rate_variation": 0.06,
        "pauses": {"comma": 0.14, "period": 0.34, "colon": 0.24, "dash": 0.2, "paragraph": 0.6},
        "emphasis": "moderate",
        "elevenlabs": {"stability": 0.38, "similarity_boost": 0.75, "style": 0.45,
                       "use_speaker_boost": True, "speed": 1.03},
        "openai_voice": "coral",
        "instructions": (
            "Friendly, spontaneous social-media voice, like recommending something to a friend. "
            "Relaxed and close to the mic, light smile, natural rhythm with small variations. "
            "Contractions and casual flow are welcome; never shout, never read like a script."
        ),
    },
    "technological": {
        "label": "Tecnológico",
        "wpm": 150, "rate": 1.0, "pitch_st": 0.0, "rate_variation": 0.02,
        "pauses": {"comma": 0.16, "period": 0.40, "colon": 0.30, "dash": 0.22, "paragraph": 0.7},
        "emphasis": "reduced",
        "elevenlabs": {"stability": 0.62, "similarity_boost": 0.80, "style": 0.12,
                       "use_speaker_boost": True, "speed": 1.0},
        "openai_voice": "alloy",
        "instructions": (
            "Modern, clear and objective tech-product narrator. Precise articulation of technical "
            "terms and product names, steady confident pace, neutral-warm tone. Explain, don't sell. "
            "Short pauses before naming features."
        ),
    },
    "lifestyle": {
        "label": "Lifestyle",
        "wpm": 135, "rate": 0.93, "pitch_st": -0.5, "rate_variation": 0.05,
        "pauses": {"comma": 0.22, "period": 0.52, "colon": 0.32, "dash": 0.3, "paragraph": 0.9},
        "emphasis": "moderate",
        "elevenlabs": {"stability": 0.45, "similarity_boost": 0.78, "style": 0.35,
                       "use_speaker_boost": True, "speed": 0.93},
        "openai_voice": "shimmer",
        "instructions": (
            "Relaxed, warm lifestyle voice. Soft and pleasant, slightly slower, with an easy smile. "
            "Sounds natural and unhurried, like a calm morning. Never pushy."
        ),
    },
    "narrative": {
        "label": "Narrativo",
        "wpm": 145, "rate": 0.98, "pitch_st": -0.5, "rate_variation": 0.08,
        "pauses": {"comma": 0.20, "period": 0.55, "colon": 0.35, "dash": 0.32, "paragraph": 1.0},
        "emphasis": "strong",
        "elevenlabs": {"stability": 0.40, "similarity_boost": 0.78, "style": 0.50,
                       "use_speaker_boost": True, "speed": 0.98},
        "openai_voice": "sage",
        "instructions": (
            "Engaging storyteller. Vary pace and intensity with the meaning: slow down for context, "
            "build gently toward the key idea, leave meaningful pauses after important lines. "
            "Expressive but sincere; no melodrama."
        ),
    },
}

# Velocidade de fala de referência por idioma (palavras/s para wpm=150)
LANGUAGE_WPS_FACTOR = {"pt-BR": 1.0, "en-US": 1.08, "es-ES": 1.02}

# ---------------------------------------------------------------------------
# Mixagem e QA
# ---------------------------------------------------------------------------
MIX_DEFAULTS = {
    "target_lufs": -14.0,       # plataformas sociais normalizam por volta de -14 LUFS
    "true_peak_db": -1.0,       # teto de true peak (dBTP)
    "voice_lufs": -16.0,        # loudness interno da voz antes do master
    "music_offset_db": {        # música abaixo da voz quando NÃO há fala (por intensidade)
        "low": -12.0, "medium": -9.0, "high": -6.0,
    },
    "duck_db": -9.0,            # redução extra da música durante a fala
    "duck_attack_s": 0.08,
    "duck_release_s": 0.45,
    "duck_hold_s": 0.20,
    "voice_pocket_db": -2.5,    # corte suave em ~2.5 kHz na música quando há voz
    "sfx_peak_db": -9.0,
}

QA_THRESHOLDS = {
    "lufs_tolerance": 1.5,          # LU de tolerância em relação ao alvo
    "max_true_peak_db": -0.5,
    "max_clipped_samples": 0,
    "max_internal_silence_s": 1.5,
    "min_voice_over_music_db": 8.0, # voz deve ficar ≥ 8 dB acima da música durante a fala
    "max_voice_over_music_db": 30.0,
    "av_duration_tolerance_s": 0.10,
    "min_scene_s": 0.8,
    "max_chars_per_second": 17.0,   # leitura de texto na tela
    "max_sentence_words": 18,
    "max_transition_types": 3,
}

# Frases que só podem aparecer se fizerem sentido (o validador avisa)
SCRIPT_CLICHES = [
    "você já imaginou", "voce ja imaginou", "conheça o futuro", "conheca o futuro",
    "transforme sua experiência", "transforme sua experiencia", "solução inovadora",
    "solucao inovadora", "revolucionário", "revolucionario", "o futuro chegou",
    "leve sua experiência a outro nível", "nunca foi tão fácil", "nunca foi tao facil",
    "mude sua vida", "game changer", "next level", "imagine a world",
    "the future of", "revolutionary", "cutting-edge", "seamless experience",
]

HYPE_WORDS = [
    "incrível", "incrivel", "inovador", "inovadora", "revolucionário", "revolucionaria",
    "poderoso", "poderosa", "perfeito", "perfeita", "único", "unica", "única", "melhor",
    "extraordinário", "fantástico", "sensacional", "absurdo", "surreal", "definitivo",
    "amazing", "powerful", "ultimate", "best", "perfect", "unique", "incredible",
]

