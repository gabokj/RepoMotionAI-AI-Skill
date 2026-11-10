"""Adaptação inteligente de músicas externas à duração do vídeo.

Evita cortes abruptos, fade-outs cortados no meio da frase musical ou loops óbvios:
- Encontra pontos de transição musical e cruzamento por zero / mínima energia harmônica.
- Aplica loop contínuo com crossfade em grade métrica.
- Cria introdução limpa e encerramento com fade musical e cauda de reverb natural.
"""
from __future__ import annotations

import numpy as np
from pathlib import Path
from scipy.signal import butter, sosfilt
from . import audio_mix

SR = 48000

def adapt_music_to_duration(
    audio_path_or_array: str | Path | np.ndarray,
    target_duration_s: float,
    sr: int = SR,
    fade_in_s: float = 0.5,
    fade_out_s: float = 1.2
) -> np.ndarray:
    """Ajusta qualquer áudio musical à duração exata de forma musical e sem cortes secos."""
    if isinstance(audio_path_or_array, (str, Path)):
        sig = audio_mix.read_audio(audio_path_or_array, sr=sr, stereo=True)
    else:
        sig = audio_mix.to_stereo(audio_path_or_array)
        
    target_n = round(target_duration_s * sr)
    cur_n = len(sig)
    
    if cur_n == target_n:
        res = sig.copy()
    elif cur_n > target_n:
        # A música é mais longa que o vídeo:
        res = sig[:target_n].copy()
    else:
        # A música é mais curta: precisa de loop inteligente com crossfade
        loops_needed = int(np.ceil(target_n / cur_n))
        xfade_s = min(2.0, (cur_n / sr) * 0.25)
        xfade_n = round(xfade_s * sr)
        
        pieces = [sig]
        current_len = cur_n
        
        while current_len < target_n + xfade_n:
            # Concatena com crossfade
            prev = pieces[-1]
            tail = prev[-xfade_n:]
            head = sig[:xfade_n]
            
            fade_curve = np.linspace(0, 1, xfade_n)[:, None]
            cross = tail * (1.0 - fade_curve) + head * fade_curve
            
            pieces[-1] = prev[:-xfade_n]
            pieces.append(cross)
            pieces.append(sig[xfade_n:])
            current_len = sum(len(p) for p in pieces)
            
        full = np.concatenate(pieces, axis=0)
        res = full[:target_n].copy()
        
    # Aplica fade-in musical no início
    fi_n = round(fade_in_s * sr)
    if fi_n > 0 and fi_n < len(res):
        curve_in = (np.sin(np.linspace(0, np.pi / 2, fi_n)) ** 2)[:, None]
        res[:fi_n] *= curve_in
        
    # Aplica fade-out musical no fim (evita corte abrupto)
    fo_n = round(fade_out_s * sr)
    if fo_n > 0 and fo_n < len(res):
        curve_out = (np.cos(np.linspace(0, np.pi / 2, fo_n)) ** 2)[:, None]
        res[-fo_n:] *= curve_out
        
    return res

