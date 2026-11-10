"""Mixagem e masterização: loudness ITU-R BS.1770-4, true peak, ducking,
EQ de "bolsão de voz", limitador com lookahead e I/O de WAV.

Somente numpy/scipy (já exigidos pelo projeto). Formatos não-WAV são
convertidos com ffmpeg quando ele está disponível.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from math import gcd
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.signal import lfilter, resample_poly

from . import config

SR = 48000


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------
def _to_float(data):
    if data.dtype == np.int16:
        return data.astype(np.float64) / 32768.0
    if data.dtype == np.int32:
        return data.astype(np.float64) / 2147483648.0
    if data.dtype == np.uint8:
        return (data.astype(np.float64) - 128) / 128.0
    return data.astype(np.float64)


def read_audio(path, sr=SR, stereo=True):
    """Lê áudio como float64 [-1, 1], reamostrado para `sr`.

    WAV é lido direto; outros formatos (mp3, m4a, ogg) exigem ffmpeg.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de áudio não encontrado: {path}")
    if path.suffix.lower() != ".wav":
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError(f"{path.name}: formato {path.suffix} requer ffmpeg instalado no PATH")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "decoded.wav"
            subprocess.run([ffmpeg, "-y", "-v", "error", "-i", str(path), "-ar", str(sr), "-ac", "2", str(out)],
                           check=True)
            return read_audio(out, sr, stereo)
    file_sr, data = wavfile.read(path)
    x = _to_float(data)
    if x.ndim == 1:
        x = x[:, None]
    if file_sr != sr:
        g = gcd(int(file_sr), int(sr))
        x = resample_poly(x, sr // g, file_sr // g, axis=0)
    if stereo and x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    elif not stereo and x.shape[1] > 1:
        x = x.mean(axis=1, keepdims=True)
    return x


def write_wav(path, x, sr=SR, rng=None, bits=16):
    """Grava WAV PCM. 16 bit usa dither TPDF; 24 bit é gravado em int32."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    x = np.asarray(x, dtype=np.float64)
    if bits == 16:
        rng = rng or np.random.default_rng(0)
        dither = (rng.random(x.shape) - rng.random(x.shape)) / 32768.0
        data = np.clip(np.round((x + dither) * 32767), -32768, 32767).astype(np.int16)
    else:
        data = np.clip(np.round(x * 2147483647), -2147483648, 2147483647).astype(np.int32)
    wavfile.write(path, sr, data)
    return path


def to_stereo(x):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    return x


def fit_length(x, n):
    if len(x) >= n:
        return x[:n]
    pad = np.zeros((n - len(x),) + x.shape[1:])
    return np.concatenate([x, pad])


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-12))


# ---------------------------------------------------------------------------
# Loudness (ITU-R BS.1770-4 / EBU R128)
# ---------------------------------------------------------------------------
def _k_weighting(sr):
    # estágio 1: high-shelf (efeito da cabeça)
    G, Q, fc = 3.99984385397, 0.7071752369554193, 1681.9744509555319
    A = 10 ** (G / 40)
    w0 = 2 * np.pi * fc / sr
    alpha = np.sin(w0) / (2 * Q)
    cw = np.cos(w0)
    b1 = np.array([A * ((A + 1) + (A - 1) * cw + 2 * np.sqrt(A) * alpha),
                   -2 * A * ((A - 1) + (A + 1) * cw),
                   A * ((A + 1) + (A - 1) * cw - 2 * np.sqrt(A) * alpha)])
    a1 = np.array([(A + 1) - (A - 1) * cw + 2 * np.sqrt(A) * alpha,
                   2 * ((A - 1) - (A + 1) * cw),
                   (A + 1) - (A - 1) * cw - 2 * np.sqrt(A) * alpha])
    # estágio 2: high-pass (RLB)
    Q2, fc2 = 0.5003270373253953, 38.13547087613982
    w0 = 2 * np.pi * fc2 / sr
    alpha = np.sin(w0) / (2 * Q2)
    cw = np.cos(w0)
    b2 = np.array([(1 + cw) / 2, -(1 + cw), (1 + cw) / 2])
    a2 = np.array([1 + alpha, -2 * cw, 1 - alpha])
    return (b1 / a1[0], a1 / a1[0]), (b2 / a2[0], a2 / a2[0])


def _block_powers(x, sr, block_s=0.4, overlap=0.75):
    x = to_stereo(x) if x.ndim == 1 else x
    (b1, a1), (b2, a2) = _k_weighting(sr)
    y = lfilter(b2, a2, lfilter(b1, a1, x, axis=0), axis=0)
    n = round(block_s * sr)
    hop = max(1, round(n * (1 - overlap)))
    if len(y) < n:
        return np.array([np.sum(np.mean(y ** 2, axis=0))]) if len(y) else np.array([])
    sq = y ** 2
    csum = np.concatenate([np.zeros((1, sq.shape[1])), np.cumsum(sq, axis=0)])
    starts = np.arange(0, len(y) - n + 1, hop)
    z = (csum[starts + n] - csum[starts]) / n  # média quadrática por canal
    return z.sum(axis=1)


def integrated_loudness(x, sr=SR):
    """Loudness integrado em LUFS (com gates absoluto -70 e relativo -10)."""
    p = _block_powers(np.asarray(x, dtype=np.float64), sr)
    if p.size == 0:
        return float("-inf")
    lk = -0.691 + 10 * np.log10(np.maximum(p, 1e-20))
    gated = p[lk > -70]
    if gated.size == 0:
        return float("-inf")
    rel = -0.691 + 10 * np.log10(np.mean(gated)) - 10
    gated2 = p[(lk > -70) & (lk > rel)]
    if gated2.size == 0:
        return float("-inf")
    return float(-0.691 + 10 * np.log10(np.mean(gated2)))


def short_term_loudness(x, sr=SR):
    """Loudness de curto prazo (janelas de 3 s, passo 1 s)."""
    p = _block_powers(np.asarray(x, dtype=np.float64), sr, block_s=3.0, overlap=2 / 3)
    return -0.691 + 10 * np.log10(np.maximum(p, 1e-20))


def true_peak_db(x, sr=SR):
    """True peak aproximado por sobreamostragem 4x (BS.1770 anexo 2)."""
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return float("-inf")
    up = resample_poly(x, 4, 1, axis=0)
    return float(db(np.max(np.abs(up))))


def sample_peak_db(x):
    return float(db(np.max(np.abs(x)))) if np.size(x) else float("-inf")


# ---------------------------------------------------------------------------
# Processadores
# ---------------------------------------------------------------------------
def peaking_eq(x, sr, freq, gain_db, q=1.0):
    """Filtro peaking (RBJ cookbook)."""
    if abs(gain_db) < 1e-3:
        return x
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * freq / sr
    alpha = np.sin(w0) / (2 * q)
    b = np.array([1 + alpha * A, -2 * np.cos(w0), 1 - alpha * A])
    a = np.array([1 + alpha / A, -2 * np.cos(w0), 1 - alpha / A])
    return lfilter(b / a[0], a / a[0], x, axis=0)


def limiter(x, sr=SR, ceiling_db=-1.0, lookahead_s=0.006, iterations=3):
    """Limitador de pico com lookahead (sem distorção por clipping duro).

    Ganho exigido por amostra -> mínimo numa janela (hold) -> média móvel
    (rampas suaves). A média de mínimos garante ganho <= exigido no pico.
    Repete se o true peak (4x) ainda exceder o teto.
    """
    x = np.asarray(x, dtype=np.float64)
    L = max(1, round(lookahead_s * sr))
    ceiling = 10 ** (ceiling_db / 20)
    y = x
    for _ in range(iterations):
        if true_peak_db(y, sr) <= ceiling_db + 0.05:
            break
        peak = np.max(np.abs(y), axis=1) if y.ndim > 1 else np.abs(y)
        req = np.minimum(1.0, (ceiling * 0.98) / np.maximum(peak, 1e-12))
        g = minimum_filter1d(req, size=2 * L + 1, mode="nearest")
        g = uniform_filter1d(g, size=L + 1 if L % 2 == 0 else L, mode="nearest")
        y = y * (g[:, None] if y.ndim > 1 else g)
        ceiling *= 0.995
    return y


def master(x, sr=SR, target_lufs=-14.0, true_peak=-1.0):
    """Normaliza loudness e limita true peak. Retorna (sinal, ganho_linear)."""
    x = np.asarray(x, dtype=np.float64)
    lufs = integrated_loudness(x, sr)
    if not np.isfinite(lufs):
        return x, 1.0
    gain = 10 ** ((target_lufs - lufs) / 20)
    y = limiter(x * gain, sr, true_peak)
    return y, gain


# ---------------------------------------------------------------------------
# Detecção de fala e ducking
# ---------------------------------------------------------------------------
def voice_activity(voice, sr=SR, frame_s=0.01, min_gap_s=0.35, threshold_db=None):
    """Retorna (tempos_s, ativo_bool) a cada `frame_s`.

    Limiar adaptativo: 30 dB abaixo do percentil 95 de energia, nunca abaixo
    de -50 dBFS. Lacunas menores que `min_gap_s` (respiros entre palavras)
    contam como fala, para a música não "bombear" entre palavras.
    """
    v = np.asarray(voice, dtype=np.float64)
    if v.ndim > 1:
        v = v.mean(axis=1)
    hop = max(1, round(frame_s * sr))
    n_frames = max(1, len(v) // hop)
    frames = v[: n_frames * hop].reshape(n_frames, hop)
    rms_db = 10 * np.log10(np.mean(frames ** 2, axis=1) + 1e-12)
    if threshold_db is None:
        threshold_db = max(-50.0, float(np.percentile(rms_db, 95)) - 30.0)
    active = rms_db > threshold_db
    # fecha lacunas curtas
    gap = round(min_gap_s / frame_s)
    idx = np.flatnonzero(active)
    if idx.size:
        for a, b in zip(idx[:-1], idx[1:]):
            if 1 < b - a <= gap:
                active[a:b] = True
    times = np.arange(n_frames) * frame_s
    return times, active


def speech_regions(voice, sr=SR, **kw):
    """Lista de (início_s, fim_s) com fala."""
    times, active = voice_activity(voice, sr, **kw)
    regions, start = [], None
    step = times[1] - times[0] if len(times) > 1 else 0.01
    for t, a in zip(times, active):
        if a and start is None:
            start = t
        elif not a and start is not None:
            regions.append((round(start, 3), round(t, 3)))
            start = None
    if start is not None:
        regions.append((round(start, 3), round(times[-1] + step, 3)))
    return regions


def ducking_gain(voice, n_samples, sr=SR, duck_db=None, attack_s=None, release_s=None,
                 hold_s=None):
    """Curva de ganho (linear, por amostra) para a música.

    Só reduz onde há fala; antecipa o ataque para a primeira sílaba não ser
    mascarada; mantém (hold) e solta devagar (release) nas pausas longas.
    """
    d = config.MIX_DEFAULTS
    duck_db = d["duck_db"] if duck_db is None else duck_db
    attack_s = d["duck_attack_s"] if attack_s is None else attack_s
    release_s = d["duck_release_s"] if release_s is None else release_s
    hold_s = d["duck_hold_s"] if hold_s is None else hold_s
    frame_s = 0.01
    times, active = voice_activity(voice, sr, frame_s=frame_s)
    act = active.copy()
    lead = round(attack_s / frame_s)
    hold = round(hold_s / frame_s)
    idx = np.flatnonzero(active)
    for i in idx:  # antecipa o ataque e segura após a fala
        act[max(0, i - lead): min(len(act), i + hold + 1)] = True
    target = np.where(act, duck_db, 0.0)
    out = np.zeros_like(target)
    a_coef = np.exp(-frame_s / max(1e-3, attack_s / 3))
    r_coef = np.exp(-frame_s / max(1e-3, release_s / 3))
    cur = 0.0
    for k, tg in enumerate(target):
        coef = a_coef if tg < cur else r_coef
        cur = coef * cur + (1 - coef) * tg
        out[k] = cur
    gain_db = np.interp(np.arange(n_samples) / sr, times, out, right=0.0)
    return 10 ** (gain_db / 20)


def voice_to_music_ratio_db(voice, music, sr=SR):
    """Diferença média (dB) entre voz e música nos trechos com fala."""
    times, active = voice_activity(voice, sr)
    if not active.any():
        return None
    hop = round(0.01 * sr)
    v = np.asarray(voice).mean(axis=1) if np.ndim(voice) > 1 else np.asarray(voice)
    m = np.asarray(music).mean(axis=1) if np.ndim(music) > 1 else np.asarray(music)
    n = min(len(v), len(m)) // hop
    v = v[: n * hop].reshape(n, hop)
    m = m[: n * hop].reshape(n, hop)
    act = active[:n]
    pv = np.mean(v[act] ** 2)
    pm = np.mean(m[act] ** 2)
    if pm <= 1e-14:
        return float("inf")
    return float(10 * np.log10(pv / pm))


# ---------------------------------------------------------------------------
# Mixagem completa
# ---------------------------------------------------------------------------
def mix_tracks(voice=None, music=None, sfx=None, sr=SR, duration_s=None, target_lufs=None,
               true_peak=None, music_intensity="medium", duck_db=None, voice_pocket=True,
               voice_offset_s=0.0, music_fade_in_s=0.0, music_fade_out_s=0.0):
    """Mixa voz (primeiro plano), música (fundo, com ducking) e SFX.

    Todas as entradas são arrays float (n,) ou (n, 2) já em `sr`.
    Retorna (mix, relatório_dict).
    """
    d = config.MIX_DEFAULTS
    target_lufs = d["target_lufs"] if target_lufs is None else target_lufs
    true_peak = d["true_peak_db"] if true_peak is None else true_peak
    if music_intensity not in d["music_offset_db"]:
        raise ValueError(f"music_intensity deve ser um de: {', '.join(d['music_offset_db'])}")
    tracks = {k: to_stereo(v) for k, v in (("voice", voice), ("music", music), ("sfx", sfx)) if v is not None}
    if not tracks:
        raise ValueError("Informe ao menos uma trilha (voz, música ou SFX)")
    if "voice" in tracks and voice_offset_s:
        off = round(voice_offset_s * sr)
        tracks["voice"] = np.concatenate([np.zeros((off, 2)), tracks["voice"]])
    n = round(duration_s * sr) if duration_s else max(len(t) for t in tracks.values())
    tracks = {k: fit_length(v, n) for k, v in tracks.items()}
    report = {"duration_s": n / sr, "target_lufs": target_lufs, "true_peak_target": true_peak,
              "music_intensity": music_intensity, "steps": []}

    out = np.zeros((n, 2))
    voice_t = tracks.get("voice")
    music_t = tracks.get("music")
    sfx_t = tracks.get("sfx")
    has_voice = voice_t is not None and np.isfinite(integrated_loudness(voice_t, sr))

    if has_voice:
        vl = integrated_loudness(voice_t, sr)
        if np.isfinite(vl):
            voice_t = voice_t * 10 ** ((d["voice_lufs"] - vl) / 20)
        # HPF leve na voz (remove ronco < 80 Hz sem afinar o timbre)
        b = np.array([1, -1]); a = np.array([1, -np.exp(-2 * np.pi * 70 / sr)])
        voice_t = lfilter(b, a, voice_t, axis=0)
        tracks["voice"] = voice_t
        report["steps"].append(f"voz normalizada de {vl:.1f} para {d['voice_lufs']:.1f} LUFS")
        out += voice_t

    music_gain = 1.0
    if music_t is not None:
        ml = integrated_loudness(music_t, sr)
        if np.isfinite(ml):
            ref = d["voice_lufs"] if has_voice else target_lufs
            offset = d["music_offset_db"][music_intensity] if has_voice else 0.0
            music_gain = 10 ** ((ref + offset - ml) / 20)
            music_t = music_t * music_gain
            report["steps"].append(f"música ajustada para {ref + offset:.1f} LUFS (sem fala)")
        if has_voice and voice_pocket:
            music_t = peaking_eq(music_t, sr, 2500, d["voice_pocket_db"], q=0.9)
            report["steps"].append(f"EQ de bolsão de voz na música ({d['voice_pocket_db']} dB @ 2.5 kHz)")
        if has_voice:
            g = ducking_gain(voice_t, n, sr, duck_db=duck_db)
            music_t = music_t * g[:, None]
            report["steps"].append(f"ducking {duck_db if duck_db is not None else d['duck_db']} dB "
                                   "apenas durante a fala")
        if music_fade_in_s > 0:
            k = min(n, round(music_fade_in_s * sr))
            music_t[:k] *= (np.sin(np.linspace(0, np.pi / 2, k)) ** 2)[:, None]
        if music_fade_out_s > 0:
            k = min(n, round(music_fade_out_s * sr))
            music_t[-k:] *= (np.cos(np.linspace(0, np.pi / 2, k)) ** 2)[:, None]
        out += music_t

    if sfx_t is not None and np.max(np.abs(sfx_t)) > 0:
        sfx_t = sfx_t * music_gain if music_t is not None else (
            sfx_t * 10 ** (d["sfx_peak_db"] / 20) / max(1e-9, np.max(np.abs(sfx_t))))
        if has_voice:  # SFX também abrem espaço para a fala, mas menos que a música
            g = ducking_gain(voice_t, n, sr, duck_db=(duck_db if duck_db is not None else d["duck_db"]) / 2)
            sfx_t = sfx_t * g[:, None]
        out += sfx_t
        report["steps"].append("SFX equilibrados com a música")

    pre_peak = sample_peak_db(out)
    mixed, gain = master(out, sr, target_lufs, true_peak)
    # fades de segurança (sem clique no início/fim)
    k = min(round(0.005 * sr), n // 2)
    if k:
        mixed[:k] *= np.linspace(0, 1, k)[:, None]
        mixed[-k:] *= np.linspace(1, 0, k)[:, None]
    report.update({
        "pre_master_peak_db": round(pre_peak, 2),
        "lufs": round(integrated_loudness(mixed, sr), 2),
        "true_peak_db": round(true_peak_db(mixed, sr), 2),
        "master_gain_db": round(20 * np.log10(max(gain, 1e-12)), 2),
    })
    if has_voice and music_t is not None:
        r = voice_to_music_ratio_db(voice_t, music_t, sr)
        report["voice_over_music_db"] = None if r is None else round(r, 1)
        report["speech_regions"] = speech_regions(voice_t, sr)
    report["voice_track"] = voice_t if has_voice else None
    report["music_track"] = music_t if music_t is not None else None
    return mixed, report

