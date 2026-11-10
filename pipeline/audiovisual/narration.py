"""Módulo de Inteligência de Narração e Text-to-Speech (TTS).

Fornece:
- Motor de fallback offline/local determinístico via sintetizador formant/phoneme WAV (garantindo que o pipeline sempre gere áudio mesmo sem chave de API externa).
"""
from __future__ import annotations

import re
import json
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import numpy as np
from scipy.signal import butter, sosfilt

from . import config

SR = 48000

# Dicionário de pronúncia e expansão para narração natural em português
PRONUNCIATION_DICT = {
    r"\bAI\b": "Ei Ái",
    r"\bIA\b": "I Á",
    r"\bAPI\b": "A Pê Í",
    r"\bAPIs\b": "A Pê Ís",
    r"\bUI\b": "Iu Ái",
    r"\bUX\b": "U Xis",
    r"\bCSS\b": "Cê Esse Esse",
    r"\bHTML\b": "Agá Tê Eme Éle",
    r"\bJS\b": "Jota Esse",
    r"\bTS\b": "Tê Esse",
    r"\bJSON\b": "Jei-son",
    r"\bGitHub\b": "Guit-rãbi",
    r"\bGit\b": "Guite",
    r"\bOpenAI\b": "Open Ei Ái",
    r"\bClaude\b": "Clóde",
    r"\bGemini\b": "Djémini",
    r"\bChatGPT\b": "Chate Gê Pê Tê",
    r"\bPython\b": "Páiton",
    r"\bNode\.?js\b": "Nôud Jei Esse",
    r"\bReact\b": "Riect",
    r"\bNext\.?js\b": "Néxte Jei Esse",
    r"\bVue\b": "Viu",
    r"\bDocker\b": "Dóquer",
    r"\bKubernetes\b": "Kubernetes",
    r"\bPostgres\b": "Póst-gres",
    r"\bSQL\b": "Esse Quê Éle",
    r"\bNoSQL\b": "Nôu Esse Quê Éle",
    r"\bAWS\b": "A Dábliu Esse",
    r"\bSaaS\b": "Sáss",
    r"\bB2B\b": "Bê to Bê",
    r"\bB2C\b": "Bê to Cê",
    r"\bCTA\b": "Cê Tê Á",
    r"\bROI\b": "Rói",
    r"\bFPS\b": "Quadros por segundo",
    r"\bWAV\b": "Uéve",
    r"\bMP4\b": "Eme Pê Quatro",
    r"\bHQ\b": "Agá Quê",
    r"\bHD\b": "Agá Dê",
    r"\b4K\b": "Quatro Ká",
}

def normalize_text_for_speech(text: str, lang: str = "pt-BR") -> str:
    """Normaliza siglas técnicas, números e símbolos para leitura fluida."""
    t = text
    # Substituições fonéticas
    for pat, rep in PRONUNCIATION_DICT.items():
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)
    
    # Normalização de símbolos comuns
    t = re.sub(r"(\d+)%", r"\1 por cento", t)
    t = re.sub(r"\$(\d+)", r"\1 dólares", t)
    t = re.sub(r"R\$\s?(\d+)", r"\1 reais", t)
    t = re.sub(r"&", " e ", t)
    t = re.sub(r"\+", " mais ", t)
    t = re.sub(r"\/", " barra ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

@dataclass
class VoiceDirection:
    profile: str
    target_wpm: int
    rate: float
    pitch_st: float
    pauses: Dict[str, float]
    instructions: str
    elevenlabs_settings: Dict[str, Any]
    openai_voice: str

def get_voice_direction(profile_name: str = "commercial_premium") -> VoiceDirection:
    cfg = config.VOICE_PROFILES.get(profile_name, config.VOICE_PROFILES["commercial_premium"])
    return VoiceDirection(
        profile=profile_name,
        target_wpm=cfg["wpm"],
        rate=cfg["rate"],
        pitch_st=cfg["pitch_st"],
        pauses=cfg["pauses"],
        instructions=cfg["instructions"],
        elevenlabs_settings=cfg["elevenlabs"],
        openai_voice=cfg["openai_voice"]
    )

def estimate_speech_duration(text: str, profile_name: str = "commercial_premium") -> float:
    """Calcula duração estimada em segundos considerando pausas e velocidade do perfil."""
    direction = get_voice_direction(profile_name)
    words = len(re.findall(r"\b\w+\b", text))
    if words == 0:
        return 0.0
    
    base_s = (words / direction.target_wpm) * 60.0
    
    # Adiciona pausas por pontuação
    commas = len(re.findall(r"[,;]", text))
    periods = len(re.findall(r"[.!?]", text))
    colons = len(re.findall(r"[:—–-]", text))
    
    pauses_s = (
        commas * direction.pauses.get("comma", 0.18) +
        periods * direction.pauses.get("period", 0.45) +
        colons * direction.pauses.get("colon", 0.28)
    )
    return round(base_s + pauses_s, 2)

def generate_ssml(text: str, profile_name: str = "commercial_premium", lang: str = "pt-BR") -> str:
    """Gera SSML otimizado com rate, pitch e pausas ajustadas ao perfil de voz."""
    direction = get_voice_direction(profile_name)
    norm = normalize_text_for_speech(text, lang)
    
    # Substituir pontuações por tags de break naturais
    p_comma = int(direction.pauses.get("comma", 0.18) * 1000)
    p_period = int(direction.pauses.get("period", 0.45) * 1000)
    
    # Processa pontuação para pausas controladas
    processed = norm
    processed = re.sub(r"([.!?])\s+", rf'\1 <break time="{p_period}ms"/> ', processed)
    processed = re.sub(r"([,;])\s+", rf'\1 <break time="{p_comma}ms"/> ', processed)
    
    rate_pct = f"{int((direction.rate - 1.0) * 100):+d}%"
    pitch_pct = f"{int(direction.pitch_st * 5):+d}%"
    
    ssml = (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang}">\n'
        f'  <prosody rate="{rate_pct}" pitch="{pitch_pct}">\n'
        f'    {processed}\n'
        f'  </prosody>\n'
        f'</speak>'
    )
    return ssml

# ---------------------------------------------------------------------------
# Sintetizador local offline para fallback determinístico
# ---------------------------------------------------------------------------
def synthesize_mock_speech(text: str, profile_name: str = "commercial_premium", duration_s: Optional[float] = None) -> np.ndarray:
    """Gera voz simulada limpa (formante vocal) caso não haja API de TTS configurada.
    """
    est_dur = duration_s or estimate_speech_duration(text, profile_name)
    n = max(SR, round(est_dur * SR))
    t = np.arange(n) / SR
    
    direction = get_voice_direction(profile_name)
    f0 = 120.0 * (2.0 ** (direction.pitch_st / 12.0)) # frequência fundamental
    
    # Onda glotal com harmônicos decrescentes
    glottal = np.zeros(n)
    for h in range(1, 16):
        glottal += (1.0 / (h ** 1.3)) * np.sin(2 * np.pi * f0 * h * t)
    
    # Formantes vocais típicos de fala natural (/a/ e /e/ combinados)
    sos1 = butter(2, [600, 1100], btype="bandpass", fs=SR, output="sos")
    sos2 = butter(2, [1800, 2600], btype="bandpass", fs=SR, output="sos")
    sos3 = butter(2, [2800, 3600], btype="bandpass", fs=SR, output="sos")
    
    vocal = (sosfilt(sos1, glottal) * 1.0 + 
             sosfilt(sos2, glottal) * 0.45 + 
             sosfilt(sos3, glottal) * 0.25)
    
    # Envelope de sílabas baseado nas palavras
    words = re.findall(r"\b\w+\b", text) or ["som"]
    syl_count = sum(max(1, len(w) // 3) for w in words)
    syl_dur = n / max(1, syl_count)
    
    envelope = np.zeros(n)
    for i in range(syl_count):
        s0 = int(i * syl_dur)
        s1 = min(n, int((i + 0.82) * syl_dur))
        l = s1 - s0
        if l > 0:
            env_syl = np.sin(np.linspace(0, np.pi, l)) ** 1.5
            envelope[s0:s1] = env_syl
            
    out = vocal * envelope * 0.18
    # Fade in / out suave
    fade = round(0.02 * SR)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return np.repeat(out[:, None], 2, axis=1)

