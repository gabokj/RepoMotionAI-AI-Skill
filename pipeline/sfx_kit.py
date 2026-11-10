#!/usr/bin/env python3
"""Trilha musical original e SFX determinísticos sincronizados aos quadros do vídeo.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, lfilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audiovisual import audio_mix  # noqa: E402  (mesmo diretório da skill)

SR = 48000
SCALES = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
}
NOTES = {
    "C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3,
    "E": 4, "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8,
    "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11,
}
# Progressões por clima (graus da escala, um acorde por compasso)
PROGRESSIONS = {
    "calm": (0, 3, 5, 4),
    "uplifting": (0, 4, 5, 3),
    "cinematic": (0, 5, 3, 4),
    "tension": (0, 5, 1, 4),
    "drive": (0, 5, 6, 4),
    "playful": (0, 3, 4, 5),
}
SECTIONS = ("intro", "verse", "build", "main", "breakdown", "outro")

# ---------------------------------------------------------------------------
# Estilos de arranjo. Cada estilo muda timbres, voicings, padrões rítmicos,
# densidade e espaço — não apenas o nome.
# ---------------------------------------------------------------------------
STYLES = {
    "classic": {  # timbre e padrões da versão 1 (compatibilidade)
        "chords": "pad", "chord_rhythm": "sustain", "extensions": (0, 2, 4),
        "bass": "classic", "bass_pattern": "classic", "arp": "pluck_classic",
        "lead": "keys", "drums": "classic", "swing": 0.0, "space": 0.32,
        "pump": 0.0, "cadence": "authentic", "auto_transition_sfx": True,
        "register": 60, "brightness": 0.6, "progression": None,
    },
    "modern_advertising": {
        "chords": "epiano", "chord_rhythm": "pulse", "extensions": (0, 2, 4, 6),
        "pad": "warm", "bass": "soft", "bass_pattern": "eighths_light", "arp": None,
        "lead": "bell", "drums": "pop_light", "swing": 0.0, "space": 0.30,
        "pump": 0.12, "cadence": "authentic", "auto_transition_sfx": False,
        "register": 62, "brightness": 0.55, "progression": (0, 5, 3, 4),
        "melody_rhythm": ((0, 3, 6, 10, 12), (0, 4, 8, 14)),
    },
    "soft_electronic": {
        "chords": "pad", "chord_rhythm": "sustain", "extensions": (0, 2, 4, 8),
        "pad": "airy", "bass": "sub", "bass_pattern": "pulse", "arp": "pluck",
        "lead": "bell", "drums": "electronic_soft", "swing": 0.0, "space": 0.42,
        "pump": 0.22, "cadence": "authentic", "auto_transition_sfx": False,
        "register": 62, "brightness": 0.5, "progression": (0, 4, 5, 3),
        "melody_rhythm": ((0, 6, 12), (2, 8, 14)),
    },
    "minimalist_lifestyle": {
        "chords": "piano", "chord_rhythm": "broken", "extensions": (0, 2, 4, 8),
        "pad": None, "bass": "upright", "bass_pattern": "half", "arp": "guitar",
        "lead": "piano", "drums": "brush", "swing": 0.06, "space": 0.34,
        "pump": 0.0, "cadence": "plagal", "auto_transition_sfx": False,
        "register": 60, "brightness": 0.45, "progression": (0, 3, 5, 4),
        "melody_rhythm": ((0, 6, 10), (4, 12)),
    },
    "ambient_cinematic": {
        "chords": "pad", "chord_rhythm": "long", "extensions": (0, 2, 4, 8),
        "pad": "warm", "bass": "drone", "bass_pattern": "drone", "arp": None,
        "lead": "piano", "drums": "cinematic", "swing": 0.0, "space": 0.55,
        "pump": 0.0, "cadence": "plagal", "auto_transition_sfx": False,
        "register": 57, "brightness": 0.4, "progression": (0, 5, 3, 4),
        "melody_rhythm": ((0, 8), (4, 12)),
    },
    "light_funk": {
        "chords": "epiano", "chord_rhythm": "stabs", "extensions": (0, 2, 4, 6),
        "pad": None, "bass": "funk", "bass_pattern": "syncopated", "arp": "guitar_chop",
        "lead": "bell", "drums": "groove", "swing": 0.12, "space": 0.22,
        "pump": 0.0, "cadence": "authentic", "auto_transition_sfx": False,
        "register": 60, "brightness": 0.6, "progression": (0, 3, 6, 4),
        "melody_rhythm": ((0, 3, 7, 10), (2, 6, 12)),
    },
}

# Padrões de bateria em 16 passos: (passo, velocidade, energia mínima)
DRUM_PATTERNS = {
    "pop_light": {
        "kick": [(0, 1.0, 0.15), (8, 0.9, 0.15), (10, 0.55, 0.65)],
        "clap": [(4, 0.8, 0.38), (12, 0.85, 0.38)],
        "hat": [(s, 0.7 if s % 4 else 0.5, 0.3) for s in range(2, 16, 4)]
               + [(s, 0.45, 0.62) for s in range(0, 16, 4)],
        "shaker": [(s, 0.35 + 0.25 * (s % 2), 0.55) for s in range(16)],
    },
    "electronic_soft": {
        "kick": [(0, 1.0, 0.2), (8, 0.9, 0.2), (4, 0.8, 0.55), (12, 0.8, 0.55)],
        "rim": [(4, 0.7, 0.35), (12, 0.7, 0.35)],
        "shaker": [(s, 0.25 + 0.35 * (s % 2), 0.4) for s in range(16)],
        "hat": [(s, 0.6, 0.65) for s in (2, 6, 10, 14)],
    },
    "brush": {
        "kick": [(0, 0.55, 0.6)],
        "rim": [(12, 0.6, 0.3), (4, 0.45, 0.55)],
        "shaker": [(s, 0.3 + 0.3 * (s % 4 == 2), 0.25) for s in range(0, 16, 2)],
    },
    "cinematic": {
        "kick": [(0, 0.9, 0.45), (8, 0.6, 0.7)],
        "shaker": [(s, 0.3, 0.75) for s in range(0, 16, 2)],
    },
    "groove": {
        "kick": [(0, 1.0, 0.15), (7, 0.55, 0.5), (10, 0.85, 0.3)],
        "snare": [(4, 0.9, 0.3), (12, 0.95, 0.3)],
        "ghost": [(6, 0.3, 0.5), (9, 0.25, 0.55), (14, 0.3, 0.6)],
        "hat": [(s, 0.75 if s % 2 == 0 else 0.4, 0.25) for s in range(16)],
    },
}
BASS_PATTERNS = {  # (passo, duração em passos, oitava, energia mínima)
    "eighths_light": [(0, 3, 0, 0.0), (6, 2, 0, 0.45), (8, 3, 0, 0.0), (14, 2, 0, 0.55)],
    "pulse": [(s, 1.5, 0, 0.0 if s in (0, 8) else 0.5) for s in range(0, 16, 2)],
    "half": [(0, 7, 0, 0.0), (8, 7, 0, 0.0)],
    "drone": [(0, 16, 0, 0.0)],
    "syncopated": [(0, 2, 0, 0.0), (3, 1, 0, 0.45), (6, 1, 1, 0.5), (8, 2, 0, 0.0),
                   (10, 1, 0, 0.35), (11, 1, 1, 0.6), (14, 2, 0, 0.4)],
}
SECTION_RULES = {  # multiplicadores/limites por seção
    "intro":     {"drums": 0.0, "bass": 0.6, "lead": 0.0, "energy_cap": 0.45},
    "verse":     {"drums": 0.8, "bass": 1.0, "lead": 0.6, "energy_cap": 0.75},
    "build":     {"drums": 0.9, "bass": 1.0, "lead": 0.7, "energy_cap": 0.9, "swell": True},
    "main":      {"drums": 1.0, "bass": 1.0, "lead": 1.0, "energy_cap": 1.0},
    "breakdown": {"drums": 0.0, "bass": 0.5, "lead": 0.8, "energy_cap": 0.55},
    "outro":     {"drums": 0.6, "bass": 1.0, "lead": 0.5, "energy_cap": 0.7},
}


def midi_hz(note):
    return 440.0 * 2.0 ** ((note - 69) / 12.0)


def scale_note(root, mode, degree):
    octave, index = divmod(degree, 7)
    return root + SCALES[mode][index] + 12 * octave


def _voice_lead(pitch_classes, previous, center):
    """Escolhe a inversão mais próxima do acorde anterior (movimento mínimo)."""
    candidates = []
    pcs = sorted(set(p % 12 for p in pitch_classes))
    for inv in range(len(pcs)):
        rotated = pcs[inv:] + pcs[:inv]
        for base_oct in range(3, 7):
            notes, last = [], None
            for pc in rotated:
                n = base_oct * 12 + pc
                while last is not None and n <= last:
                    n += 12
                notes.append(n)
                last = n
            candidates.append(notes)
    ref = previous or [center + i * 4 for i in range(len(pcs))]

    def cost(c):
        mean = sum(c) / len(c)
        spread = c[-1] - c[0]
        move = sum(min(abs(n - r) for r in ref) for n in c)
        return move + 0.35 * abs(mean - center) + 0.2 * max(0, spread - 14)

    return min(candidates, key=cost)


class Track:
    def __init__(self, dur_s, seed=7, fps=60):
        if dur_s <= 0:
            raise ValueError("dur_s deve ser maior que zero")
        if fps <= 0:
            raise ValueError("fps deve ser maior que zero")
        self.dur_s = float(dur_s)
        self.buf = np.zeros((round(SR * dur_s), 2), dtype=np.float64)   # SFX
        self.music = np.zeros_like(self.buf)                             # música (dry)
        self.pads = np.zeros_like(self.buf)                              # pads (sidechain)
        self.drums = np.zeros_like(self.buf)                             # bateria (pouca reverb)
        self.rng = np.random.default_rng(seed)                           # composição
        self.noise_rng = np.random.default_rng(seed + 1000)              # ruídos
        self.fps = fps
        self.seed = seed
        self.space = 0.32
        self.pump = 0.0
        self._kicks = []
        self.final_at = None
        self.meta = {}

    # ------------------------------------------------------------------ util
    @staticmethod
    def _env(n, tau):
        return np.exp(-np.arange(n) / (tau * SR))

    @staticmethod
    def _envelope(n, attack, release, decay=None):
        env = np.ones(n)
        a = min(n, max(1, round(attack * SR)))
        r = min(n, max(1, round(release * SR)))
        env[:a] = np.sin(np.linspace(0, np.pi / 2, a)) ** 2
        if decay:
            env *= np.exp(-np.arange(n) / (decay * SR))
        env[-r:] *= np.cos(np.linspace(0, np.pi / 2, r)) ** 2
        return env

    def _target(self, bus):
        return {"music": self.music, "pad": self.pads, "drums": self.drums}.get(bus, self.buf)

    def _place_at(self, start_s, sig, vol=1.0, pan=0.0, bus="sfx"):
        sig = np.asarray(sig, dtype=np.float64)
        if sig.ndim == 1:
            angle = (np.clip(pan, -1, 1) + 1) * np.pi / 4
            sig = sig[:, None] * np.array([np.cos(angle), np.sin(angle)])
        i = round(start_s * SR)
        source_start = max(0, -i)
        i = max(0, i)
        j = min(len(self.buf), i + len(sig) - source_start)
        if j > i:
            self._target(bus)[i:j] += sig[source_start:source_start + j - i] * vol

    def _place(self, frame, sig, vol=1.0, pan=0.0, bus="sfx"):
        self._place_at(frame / self.fps, sig, vol, pan, bus)

    def _noise(self, n):
        return self.noise_rng.standard_normal(n)

    # ----------------------------------------------------------- instrumentos
    def _oscillator(self, freq, dur, kind):
        """Timbres da v1 (pad/pluck/bass/keys) mantidos para compatibilidade."""
        n = max(1, round(dur * SR))
        t = np.arange(n) / SR
        phase = 2 * np.pi * freq * t
        if kind == "pad":
            sig = np.sin(phase) + 0.22 * np.sin(2 * phase) + 0.08 * np.sin(3 * phase)
            env = self._envelope(n, min(0.35, dur / 3), min(0.6, dur / 2))
        elif kind == "pluck":
            sig = sum(np.sin(h * phase) * np.exp(-t * (2.5 + h)) / h for h in range(1, 6))
            env = self._envelope(n, 0.004, min(0.09, dur / 2), decay=dur * 0.8)
        elif kind == "bass":
            sig = np.tanh(np.sin(phase) + 0.32 * np.sin(2 * phase) + 0.1 * np.sin(3 * phase))
            env = self._envelope(n, 0.008, min(0.08, dur / 2), decay=dur * 2.5)
        else:
            sig = np.sin(phase) + 0.3 * np.sin(2 * phase) + 0.08 * np.sin(3 * phase)
            env = self._envelope(n, 0.008, min(0.14, dur / 2), decay=max(0.2, dur))
        return sig * env

    def _synth(self, kind, freq, dur, vel=1.0, brightness=0.5):
        """Instrumentos da v2. Todos vetorizados e sem samples externos."""
        if kind in ("pad", "pluck", "bass", "keys"):
            return self._oscillator(freq, dur, kind)
        n = max(1, round(dur * SR))
        t = np.arange(n) / SR
        nyq = SR / 2 - 2000
        if kind == "epiano":  # FM estilo piano elétrico: corpo + "tine" no ataque
            index = (0.6 + 1.4 * vel * brightness) * np.exp(-t * 4.0)
            body = np.sin(2 * np.pi * freq * t + index * np.sin(2 * np.pi * freq * t))
            tine = np.sin(2 * np.pi * min(freq * 14, nyq) * t) * np.exp(-t * 38) * 0.12 * vel
            tau = 1.5 * (220 / freq) ** 0.35
            env = self._envelope(n, 0.003, min(0.12, dur / 2), decay=tau)
            return (body + tine) * env
        if kind == "piano":  # aditivo com inharmonicidade e decaimento por parcial
            B = 0.00035
            sig = np.zeros(n)
            tau1 = 2.2 * (262 / freq) ** 0.5
            for h in range(1, 9):
                fh = freq * h * np.sqrt(1 + B * h * h)
                if fh >= nyq:
                    break
                amp = (1 / h ** (1.6 - 0.5 * brightness)) * (0.6 + 0.4 * vel)
                sig += amp * np.sin(2 * np.pi * fh * t) * np.exp(-t / (tau1 / (1 + 0.55 * (h - 1))))
            hammer = np.zeros(n)
            k = min(n, 240)
            hammer[:k] = self._noise(k) * np.exp(-np.arange(k) / 40) * 0.05 * vel
            env = self._envelope(n, 0.002, min(0.18, dur / 2))
            return (sig + hammer) * env
        if kind in ("warm", "airy"):  # pad com 3 vozes desafinadas, harmônicos filtrados
            sig = np.zeros(n)
            rolloff = 1.0 + brightness * 5.0
            for detune in (-0.0045, 0.0, 0.0041):
                f = freq * (1 + detune)
                phase0 = self.rng.uniform(0, 2 * np.pi)
                for h in range(1, 10):
                    if f * h >= nyq:
                        break
                    sig += np.sin(2 * np.pi * f * h * t + phase0 * h) * np.exp(-(h - 1) / rolloff) / h
            sig /= 3.0
            if kind == "airy":
                breath = sosfilt(butter(2, [min(freq * 3, 6000), min(freq * 7, 12000)], "bandpass",
                                        fs=SR, output="sos"), self._noise(n))
                sig += breath * 0.08
            att = min(0.9, dur / 3)
            env = self._envelope(n, att, min(0.9, dur / 2))
            return sig * env
        if kind in ("guitar", "guitar_chop"):  # corda dedilhada (aditivo com posição de ataque)
            pos = 0.18
            sig = np.zeros(n)
            mute = kind == "guitar_chop"
            for h in range(1, 14):
                fh = freq * h
                if fh >= nyq:
                    break
                amp = abs(np.sin(h * np.pi * pos)) / (h ** 1.15)
                decay = (0.08 if mute else 1.4) / (1 + 0.35 * (h - 1))
                sig += amp * np.sin(2 * np.pi * fh * t) * np.exp(-t / decay)
            env = self._envelope(n, 0.002, min(0.05 if mute else 0.15, dur / 2))
            return sig * env
        if kind == "bell":  # FM suave para o motivo (ataque macio, pouco agressivo)
            index = 1.6 * np.exp(-t * 2.5)
            sig = np.sin(2 * np.pi * freq * t + index * np.sin(2 * np.pi * freq * 3.5 * t))
            sig += 0.3 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t * 3)
            env = self._envelope(n, 0.006, min(0.2, dur / 2), decay=0.9)
            return sig * env
        if kind in ("soft", "sub", "upright", "funk", "drone", "classic_bass"):
            phase = 2 * np.pi * freq * t
            if kind == "sub":
                sig = np.sin(phase) + 0.12 * np.sin(2 * phase)
                env = self._envelope(n, 0.01, min(0.06, dur / 2), decay=dur * 3)
            elif kind == "upright":
                sig = np.sin(phase) + 0.35 * np.sin(2 * phase) * np.exp(-t * 6) + 0.1 * np.sin(3 * phase) * np.exp(-t * 9)
                env = self._envelope(n, 0.006, min(0.08, dur / 2), decay=0.7)
            elif kind == "funk":
                sig = np.sin(phase) + 0.45 * np.sin(2 * phase) * np.exp(-t * 10) + 0.2 * np.sin(3 * phase) * np.exp(-t * 16)
                env = self._envelope(n, 0.003, min(0.04, dur / 2), decay=0.35)
            elif kind == "drone":
                lfo = 1 + 0.15 * np.sin(2 * np.pi * 0.2 * t)
                sig = (np.sin(phase) + 0.2 * np.sin(2 * phase)) * lfo
                env = self._envelope(n, min(1.2, dur / 3), min(1.2, dur / 2))
            else:
                sig = np.tanh(1.2 * (np.sin(phase) + 0.25 * np.sin(2 * phase)))
                env = self._envelope(n, 0.008, min(0.08, dur / 2), decay=dur * 2.0)
            return sig * env
        raise ValueError(f"Instrumento desconhecido: {kind}")

    # ------------------------------------------------------------- API v1
    def chord(self, notes, start_s, dur_s, vol=0.05, kind="pad"):
        for index, note in enumerate(notes):
            freq = midi_hz(note)
            if kind == "pad":
                self._place_at(start_s, self._oscillator(freq * 0.9985, dur_s, kind), vol / len(notes), -0.3, "music")
                self._place_at(start_s, self._oscillator(freq * 1.0015, dur_s, kind), vol / len(notes), 0.3, "music")
            else:
                pan = np.linspace(-0.25, 0.25, len(notes))[index]
                self._place_at(start_s, self._synth(kind, freq, dur_s), vol / len(notes), pan, "music")

    def note(self, note, start_s, dur_s, vol=0.05, kind="keys", pan=0.0, vel=1.0, bus="music", brightness=0.5):
        self._place_at(start_s, self._synth(kind, midi_hz(note), dur_s, vel, brightness), vol, pan, bus)

    def kick(self, start_s, vol=0.16, soft=False):
        dur = 0.32 if not soft else 0.4
        n = round(dur * SR)
        t = np.arange(n) / SR
        freq = (44 if soft else 46) + (70 if soft else 105) * np.exp(-t * (22 if soft else 28))
        phase = np.cumsum(freq) / SR * 2 * np.pi
        sig = np.sin(phase) * self._envelope(n, 0.002, 0.05, decay=0.16 if soft else 0.12)
        self._place_at(start_s, sig, vol, 0, "drums")
        self._kicks.append(start_s)

    def snare(self, start_s, vol=0.08):
        dur = 0.2
        n = round(dur * SR)
        t = np.arange(n) / SR
        noise = self._noise(n)
        noise -= np.convolve(noise, np.ones(11) / 11, mode="same")
        sig = noise * 0.5 + np.sin(2 * np.pi * 185 * t) * 0.3
        sig *= self._envelope(n, 0.002, 0.04, decay=0.055)
        self._place_at(start_s, sig, vol, 0.05, "drums")

    def clap(self, start_s, vol=0.06):
        n = round(0.22 * SR)
        noise = sosfilt(butter(2, [900, 2600], "bandpass", fs=SR, output="sos"), self._noise(n))
        env = np.zeros(n)
        for k, off in enumerate((0, 0.009, 0.018)):
            i = round(off * SR)
            env[i:] += np.exp(-np.arange(n - i) / ((0.004 if k < 2 else 0.05) * SR))
        self._place_at(start_s, noise * env * 1.6, vol, -0.05, "drums")

    def rim(self, start_s, vol=0.04):
        n = round(0.06 * SR)
        t = np.arange(n) / SR
        sig = (np.sin(2 * np.pi * 1700 * t) * 0.6 + np.sin(2 * np.pi * 820 * t) * 0.4) * np.exp(-t * 90)
        sig[:60] += self._noise(60) * 0.3
        self._place_at(start_s, sig, vol, 0.2, "drums")

    def shaker(self, start_s, vol=0.02, pan=-0.25):
        n = round(0.09 * SR)
        noise = sosfilt(butter(2, [5000, 11000], "bandpass", fs=SR, output="sos"), self._noise(n))
        env = self._envelope(n, 0.012, 0.03, decay=0.03)
        self._place_at(start_s, noise * env * 2.2, vol, pan, "drums")

    def hat(self, start_s, vol=0.025, open_hat=False, pan=0.15):
        dur = 0.18 if open_hat else 0.055
        n = round(dur * SR)
        noise = self._noise(n)
        noise = np.concatenate(([0.0], np.diff(noise)))
        sig = noise * self._envelope(n, 0.001, min(0.025, dur / 2), decay=dur * 0.3)
        self._place_at(start_s, sig, vol, pan, "drums")

    def swell(self, end_s, dur=1.6, vol=0.03):
        """Ruído reverso filtrado que cresce até `end_s` (entrada de seção)."""
        start = max(0.0, end_s - dur)
        n = round((end_s - start) * SR)
        if n < 64:
            return
        noise = sosfilt(butter(2, 3500, "highpass", fs=SR, output="sos"), self._noise(n))
        env = np.linspace(0, 1, n) ** 3
        env[-64:] *= np.linspace(1, 0, 64)
        self._place_at(start, noise * env, vol, 0.0, "music")

    # ------------------------------------------------------------- análise
    def suggest_bpm(self, scenes, bpm_range=(84, 132)):
        boundaries = [s["start_frame"] / self.fps for s in scenes[1:]]
        center = (bpm_range[0] + bpm_range[1]) / 2
        if not boundaries:
            return int(round(center))
        best = None
        for bpm in range(bpm_range[0], bpm_range[1] + 1):
            beat = 60 / bpm
            error = np.mean([min(t / beat % 1, 1 - t / beat % 1) ** 2 for t in boundaries])
            error += 0.015 * ((bpm - center) / 24) ** 2
            if best is None or error < best[0]:
                best = (error, bpm)
        return best[1]

    def _normalize_scenes(self, scenes):
        total_frames = round(self.dur_s * self.fps)
        if not scenes:
            scenes = [{"start_frame": 0, "end_frame": total_frames, "mood": "cinematic", "energy": 0.5}]
        normalized, previous_end = [], 0
        for scene in scenes:
            start = int(scene["start_frame"])
            end = int(scene["end_frame"])
            mood = scene.get("mood", "cinematic").lower()
            energy = float(scene.get("energy", 0.5))
            section = scene.get("section")
            if start < previous_end or end <= start or end > total_frames + 1:
                raise ValueError("Cenas devem ser ordenadas, não sobrepostas e estar dentro da duração")
            if mood not in PROGRESSIONS:
                raise ValueError(f"Mood deve ser um de: {', '.join(PROGRESSIONS)}")
            if not 0 <= energy <= 1:
                raise ValueError("energy deve estar entre 0 e 1")
            if section is not None and section not in SECTIONS:
                raise ValueError(f"section deve ser uma de: {', '.join(SECTIONS)}")
            normalized.append({
                "start": start / self.fps, "end": min(self.dur_s, end / self.fps), "mood": mood,
                "energy": energy, "section": section, "narration": bool(scene.get("narration", False)),
                "explicit_mood": "mood" in scene,
            })
            previous_end = end
        return normalized

    # ------------------------------------------------------------- composição
    def _motif(self, style_cfg):
        """Motivo de 2 compassos (pergunta/resposta) com contorno por graus conjuntos."""
        rhythms = style_cfg.get("melody_rhythm") or ((0, 4, 8, 12), (0, 8))
        degrees, d = [], 0
        for bar_steps in rhythms:
            bar = []
            for _ in bar_steps:
                step = int(self.rng.choice((-1, 1, 1, 2, -2, 0, 3), p=(0.22, 0.24, 0.14, 0.12, 0.1, 0.1, 0.08)))
                d = int(np.clip(d + step, -2, 6))
                bar.append(d)
            degrees.append(bar)
        degrees[-1][-1] = 0 if degrees[-1][-1] % 2 else degrees[-1][-1]  # termina em nota do acorde
        return [list(zip(r, ds)) for r, ds in zip(rhythms, degrees)]

    def score(self, scenes, bpm=None, key="D", mode="minor", style=None, ending=None,
              bpm_range=None):
        """Compõe a trilha. `style=None` usa o timbre clássico da v1.

        ending: "resolve" (cadência e acorde final soando), "fade" (fade-out
        musical no último compasso) ou "none" (comportamento antigo).
        """
        key = key.upper()
        mode = mode.lower()
        if key not in NOTES:
            raise ValueError(f"Tonalidade desconhecida: {key}")
        if mode not in SCALES:
            raise ValueError(f"mode deve ser um de: {', '.join(SCALES)}")
        style_name = style or "classic"
        if style_name not in STYLES:
            raise ValueError(f"style deve ser um de: {', '.join(STYLES)}")
        cfg = STYLES[style_name]
        ending = ending or "resolve"
        if ending not in ("resolve", "fade", "none"):
            raise ValueError("ending deve ser 'resolve', 'fade' ou 'none'")
        self.space = cfg["space"]
        self.pump = cfg["pump"]

        normalized = self._normalize_scenes(scenes)
        bpm = int(bpm or self.suggest_bpm(
            [{"start_frame": round(s["start"] * self.fps)} for s in normalized],
            tuple(bpm_range) if bpm_range else (84, 132)))
        if not 60 <= bpm <= 180:
            raise ValueError("bpm deve estar entre 60 e 180")
        beat = 60 / bpm
        bar = beat * 4
        step = beat / 4
        root = 36 + NOTES[key]
        swing = cfg["swing"]
        legacy = style_name == "classic"
        motif = self.rng.choice((0, 1, 2, 4), size=8) if legacy else self._motif(cfg)

        # ---- final: escolhe o tempo do acorde final na grade global
        music_end = normalized[-1]["end"]
        self.final_at = None
        if ending == "resolve" and music_end > 2.5:
            tail = min(2.0, max(1.1, music_end * 0.08))
            latest = music_end - tail
            k_beat = int(np.floor(latest / beat + 1e-9))
            k_bar_beat = k_beat - (k_beat % 4)
            pick = k_bar_beat if k_beat - k_bar_beat <= 2 else k_beat - (k_beat % 2)
            final_at = pick * beat
            if final_at > max(bar, music_end * 0.5) and scene_at_static(normalized, final_at):
                self.final_at = final_at
        cut = self.final_at if self.final_at is not None else music_end

        def scene_at(t):
            return scene_at_static(normalized, t)

        prev_voicing = None
        total_bars = int(np.ceil(music_end / bar)) + 1
        scene_bar_counter = {}
        for bar_index in range(total_bars):
            bar_start = bar_index * bar
            # cenas que tocam este compasso (uma cena pode começar no meio do compasso)
            starts = sorted({bar_start} | {s["start"] for s in normalized if bar_start < s["start"] < bar_start + bar})
            for seg_i, seg_start in enumerate(starts):
                seg_end = starts[seg_i + 1] if seg_i + 1 < len(starts) else bar_start + bar
                scene = scene_at(seg_start)
                if scene is None or seg_start >= cut - 1e-6:
                    continue
                seg_end = min(seg_end, scene["end"], cut)
                if seg_end - seg_start <= 0.04:
                    continue
                sid = id(scene)
                count = scene_bar_counter.get(sid, 0)
                if seg_start == bar_start or count == 0:
                    scene_bar_counter[sid] = count + 1
                section = scene["section"]
                rules = SECTION_RULES.get(section or "main")
                energy = min(scene["energy"], rules["energy_cap"]) if section else scene["energy"]
                if scene["explicit_mood"] or legacy or not cfg.get("progression"):
                    progression = PROGRESSIONS[scene["mood"]]
                else:
                    progression = cfg["progression"]
                degree = progression[count % len(progression)]
                # cadência: o trecho imediatamente antes do acorde final prepara a resolução
                if self.final_at is not None and seg_start < self.final_at <= seg_start + bar + 1e-6:
                    degree = 4 if cfg["cadence"] == "authentic" else 3
                if legacy:
                    self._legacy_bar(seg_start, seg_end, bar_start, beat, root, mode, degree, energy, motif)
                else:
                    prev_voicing = self._styled_bar(cfg, seg_start, seg_end, bar_start, step, swing, root,
                                                    mode, degree, energy, scene, rules, motif, count,
                                                    prev_voicing)
            # transição automática entre cenas (estilo clássico ou se habilitada)
            for s in normalized:
                if s["start"] > 0 and bar_start <= s["start"] < bar_start + bar and s["start"] < cut:
                    if cfg["auto_transition_sfx"]:
                        start_frame = round(s["start"] * self.fps)
                        self.whoosh(start_frame - round(min(0.22, beat / 2) * self.fps),
                                    vol=0.035 + s["energy"] * 0.035, dur=min(0.3, beat / 2))
                        self.kick(s["start"], 0.13 + s["energy"] * 0.04)
                    elif not legacy:
                        before = scene_at(s["start"] - 0.01)
                        rising = before is not None and s["energy"] - before["energy"] >= 0.2
                        if rising or (before and before["section"] == "build"):
                            self.swell(s["start"], dur=min(1.6, bar * 0.75), vol=0.02 + 0.02 * s["energy"])

        if self.final_at is not None:
            self._final_chord(cfg, root, mode, prev_voicing, music_end, legacy)
        if ending in ("resolve", "fade"):
            fade_len = min(1.5 if ending == "fade" else 0.6, music_end / 4)
            self._fade_music(music_end - fade_len, music_end)

        self.meta = {"bpm": bpm, "key": key, "mode": mode, "style": style_name,
                     "ending": ending, "final_at_s": self.final_at, "music_end_s": music_end}
        return bpm

    def _legacy_bar(self, start_s, end_s, bar_start, beat, root, mode, degree, energy, motif):
        """Arranjo da v1, agora tocado na grade global (notas presas ao compasso)."""
        duration = end_s - start_s

        def ok(at, margin=0.03):
            return start_s - 1e-6 <= at < end_s - margin

        harmony = [scale_note(root + 24, mode, degree + d) for d in (0, 2, 4)]
        self.chord(harmony, start_s, duration + 0.06, vol=0.055 + 0.015 * (1 - energy))
        bass_note = scale_note(root, mode, degree)
        bass_beats = range(4) if energy >= 0.42 else (0, 2)
        for b in bass_beats:
            at = bar_start + b * beat
            if ok(at):
                self.note(bass_note, at, beat * 0.72, 0.075 + energy * 0.025, "bass")
        for b in range(4):
            at = bar_start + b * beat
            if energy > 0.12 and (b in (0, 2) or energy > 0.8) and ok(at):
                self.kick(at, 0.12 + energy * 0.055)
            if energy > 0.28 and b in (1, 3) and ok(at):
                self.snare(at, 0.04 + energy * 0.045)
            subdivisions = 2 if energy > 0.32 else 1
            for sub in range(subdivisions):
                hat_at = at + sub * beat / subdivisions
                if ok(hat_at, 0.02):
                    velocity = 0.012 + energy * 0.018
                    self.hat(hat_at, velocity * self.rng.uniform(0.8, 1.1),
                             energy > 0.75 and b == 3 and sub == subdivisions - 1)
        arp_steps = 8 if energy >= 0.52 else 4 if energy >= 0.28 else 0
        for s in range(arp_steps):
            at = bar_start + s * 4 * beat / arp_steps
            if not ok(at):
                continue
            arp_note = harmony[s % 3] + (12 if s >= 6 and energy > 0.78 else 0)
            self.note(arp_note, at, beat * 0.38, 0.018 + energy * 0.014, "pluck", -0.35 + 0.7 * (s % 2))
        melody_steps = 8 if energy >= 0.72 else 4 if energy >= 0.35 else 2
        for s in range(melody_steps):
            motif_index = s * 8 // melody_steps
            at = bar_start + motif_index * beat / 2
            if not ok(at, 0.04):
                continue
            melody_note = scale_note(root + 24, mode, degree + int(motif[motif_index]))
            self.note(melody_note, at, beat * 0.65, 0.024 + energy * 0.018, "keys", 0.12)

    def _styled_bar(self, cfg, seg_start, seg_end, bar_start, step, swing, root, mode, degree,
                    energy, scene, rules, motif, count, prev_voicing):
        narr = scene["narration"]
        section = scene["section"] or "main"
        bright = cfg["brightness"] * (0.75 + 0.5 * energy) * (0.8 if narr else 1.0)
        pcs = [scale_note(root, mode, degree + d) for d in cfg["extensions"]]
        voicing = _voice_lead(pcs, prev_voicing, cfg["register"])

        def when(s):  # passo de 16 avos -> segundos (com swing nos contratempos)
            return bar_start + s * step + (swing * step if s % 2 else 0.0)

        def inside(t):
            return seg_start - 1e-6 <= t < seg_end - 0.02

        seg_len = seg_end - seg_start
        # ---- pad (camada de sustentação)
        pad_kind = cfg.get("pad") if cfg["chords"] != "pad" else (cfg.get("pad") or "warm")
        if pad_kind:
            pad_vol = 0.05 * (0.9 if cfg["chords"] == "pad" else 0.55)
            for i, nt in enumerate(voicing):
                self.note(nt, seg_start, seg_len + 0.25, pad_vol / len(voicing), pad_kind,
                          pan=(-0.4 + 0.8 * i / max(1, len(voicing) - 1)), bus="pad", brightness=bright)
        # ---- acordes rítmicos
        rhythm = cfg["chord_rhythm"]
        ch = cfg["chords"]
        if ch != "pad":
            if rhythm == "pulse":
                hits = [(0, 1.0, 8)] + ([(6, 0.6, 2), (10, 0.55, 2)] if energy >= 0.45 and not narr else [])
            elif rhythm == "stabs":
                hits = [(0, 0.8, 2), (3, 0.6, 1), (8, 0.7, 2), (11, 0.6, 1)] if energy >= 0.3 else [(0, 0.8, 4)]
                if narr:
                    hits = hits[::2]
            elif rhythm == "broken":
                order = [0, 2, 1, 3, 2, 1, 3, 2]
                hits = [("b", order[k], 2 * k) for k in range(8 if energy >= 0.35 else 4)]
            else:  # long / sustain
                hits = [(0, 0.8, 16)]
            for h in hits:
                if h[0] == "b":
                    _, idx, s = h
                    t0 = when(s)
                    if inside(t0):
                        nt = voicing[idx % len(voicing)]
                        self.note(nt, t0, step * 6, 0.05 * (0.75 + 0.25 * energy), ch,
                                  pan=-0.2 + 0.4 * (idx % 2), vel=0.65 + 0.2 * energy, brightness=bright)
                    continue
                s, vel, length = h
                t0 = when(s)
                if inside(t0):
                    for i, nt in enumerate(voicing):
                        self.note(nt, t0, step * length + 0.05, 0.075 / len(voicing) * vel, ch,
                                  pan=-0.25 + 0.5 * i / max(1, len(voicing) - 1),
                                  vel=vel * (0.6 + 0.4 * energy), brightness=bright)
        # ---- arpejo / guitarra
        arp = cfg.get("arp")
        if arp and energy >= 0.25:
            if arp == "pluck":
                steps = range(0, 16, 2) if energy < 0.6 or narr else range(16)
                kind = "guitar"
                for k, s in enumerate(steps):
                    t0 = when(s)
                    if inside(t0):
                        nt = voicing[k % len(voicing)] + 12
                        self.note(nt, t0, step * 2.5, 0.018 * (0.7 + 0.5 * energy), kind,
                                  pan=-0.45 + 0.9 * (k % 2), vel=0.7, bus="music", brightness=bright)
            elif arp == "guitar":
                pattern = [0, 3, 2, 3, 1, 3, 2, 3]
                for k, s in enumerate(range(0, 16, 2)):
                    t0 = when(s)
                    if inside(t0) and (energy >= 0.4 or k % 2 == 0):
                        idx = pattern[k]
                        nt = voicing[0] - 12 if idx == 0 else voicing[min(idx, len(voicing) - 1)]
                        self.note(nt, t0, step * 6, 0.03, "guitar", pan=0.35, vel=0.7)
            elif arp == "guitar_chop":
                for s in (2, 6, 10, 14):
                    t0 = when(s)
                    if inside(t0) and not (narr and s in (6, 14)):
                        for nt in voicing[1:]:
                            self.note(nt + 12, t0, step * 0.9, 0.022, "guitar_chop", pan=0.4)
        # ---- baixo
        bass_kind = cfg["bass"]
        if bass_kind and rules["bass"] > 0 and energy >= 0.18:
            bass_root = scale_note(root, mode, degree)
            while bass_root < 33:
                bass_root += 12
            for s, length, octv, min_e in BASS_PATTERNS[cfg["bass_pattern"]]:
                t0 = when(s)
                if energy >= min_e and inside(t0):
                    dur = min(step * length, seg_end - t0 + 0.1)
                    self.note(bass_root + 12 * octv, t0, dur, 0.11 * rules["bass"] * (0.8 + 0.3 * energy),
                              bass_kind, vel=0.8)
        # ---- bateria
        drum_scale = rules["drums"] * (0.75 if narr else 1.0)
        pattern = DRUM_PATTERNS.get(cfg["drums"], {})
        if drum_scale > 0:
            for inst, hits in pattern.items():
                for s, vel, min_e in hits:
                    t0 = when(s)
                    if energy < min_e or not inside(t0):
                        continue
                    v = vel * drum_scale * (0.75 + 0.35 * energy)
                    if inst == "kick":
                        self.kick(t0, 0.15 * v, soft=cfg["drums"] in ("brush", "cinematic", "electronic_soft"))
                    elif inst == "snare":
                        self.snare(t0, 0.07 * v)
                    elif inst == "ghost":
                        self.snare(t0, 0.025 * v)
                    elif inst == "clap":
                        self.clap(t0, 0.07 * v)
                    elif inst == "rim":
                        self.rim(t0, 0.05 * v)
                    elif inst == "shaker":
                        self.shaker(t0, 0.03 * v * self.rng.uniform(0.85, 1.1))
                    elif inst == "hat":
                        self.hat(t0, 0.022 * v * self.rng.uniform(0.85, 1.1))
        # ---- melodia (motivo); sob narração fica fora para não competir com a voz
        lead = cfg.get("lead")
        lead_amt = rules["lead"] * (0.0 if narr else 1.0)
        if lead and lead_amt > 0 and energy >= 0.3:
            phrase = motif[count % len(motif)]
            for s, deg in phrase:
                t0 = when(s)
                if inside(t0):
                    nt = scale_note(root + 36, mode, degree + deg)
                    while nt > 88:
                        nt -= 12
                    self.note(nt, t0, step * 3.5, 0.032 * lead_amt * (0.7 + 0.4 * energy), lead,
                              pan=0.15, vel=0.7, brightness=bright)
        # ---- piano esparso do cinematic mesmo sob narração (muito discreto)
        if cfg["drums"] == "cinematic" and narr and energy >= 0.3:
            t0 = when(8)
            if inside(t0):
                self.note(voicing[-1] + 12, t0, step * 8, 0.012, "piano", pan=0.2, vel=0.5)
        return voicing

    def _final_chord(self, cfg, root, mode, prev_voicing, music_end, legacy):
        t0 = self.final_at
        dur = music_end - t0 + 0.2
        pcs = [scale_note(root, mode, d) for d in ((0, 2, 4) if legacy else cfg["extensions"])]
        voicing = _voice_lead(pcs, prev_voicing, cfg["register"])
        if legacy:
            self.chord([scale_note(root + 24, mode, d) for d in (0, 2, 4)], t0, dur, vol=0.065)
            self.note(scale_note(root, mode, 0), t0, dur, 0.08, "bass")
            self.kick(t0, 0.14)
            return
        pad_kind = cfg.get("pad") or "warm"
        for i, nt in enumerate(voicing):
            self.note(nt, t0, dur, 0.05 / len(voicing), pad_kind, pan=-0.4 + 0.8 * i / max(1, len(voicing) - 1),
                      bus="pad", brightness=cfg["brightness"])
            if cfg["chords"] != "pad":
                self.note(nt, t0, dur, 0.07 / len(voicing), cfg["chords"], vel=0.7, brightness=cfg["brightness"])
        bass_root = scale_note(root, mode, 0)
        while bass_root < 33:
            bass_root += 12
        if cfg["bass"]:
            self.note(bass_root, t0, min(dur, 2.5), 0.1, cfg["bass"] if cfg["bass"] != "funk" else "upright")
        if cfg["drums"] not in ("cinematic",):
            self.kick(t0, 0.1, soft=True)
        self.shimmer(round(t0 * self.fps), vol=0.018, dur=min(1.2, dur), bus="music")

    def _fade_music(self, start_s, end_s):
        i, j = round(start_s * SR), min(len(self.music), round(end_s * SR))
        if j <= i:
            return
        ramp = np.cos(np.linspace(0, np.pi / 2, j - i)) ** 2
        for bus in (self.music, self.pads, self.drums):
            bus[i:j] *= ramp[:, None]
            bus[j:] = 0.0

    # ----------------------------------------------------------------- SFX
    def pop(self, frame, vol=0.22, f0=640, f1=210, dur=0.09):
        n = int(dur * SR)
        t = np.arange(n) / SR
        freq = f1 + (f0 - f1) * np.exp(-t * 46)
        sig = np.sin(np.cumsum(freq) / SR * 2 * np.pi) * self._env(n, 0.02)
        sig *= self._envelope(n, 0.0015, 0.004)  # sem clique no ataque
        self._place(frame, sig, vol)

    def tick(self, frame, vol=0.05, freq=2200):
        n = int(0.022 * SR)
        t = np.arange(n) / SR
        sig = np.sin(2 * np.pi * freq * t) * self._env(n, 0.005) * self._envelope(n, 0.0008, 0.003)
        self._place(frame, sig, vol)

    def whoosh(self, frame, vol=0.11, dur=0.36):
        """Ruído com filtro passa-baixa variável (vetorizado em blocos)."""
        n = int(dur * SR)
        if n < 16:
            return
        noise = self._noise(n)
        sweep = 0.5 - 0.5 * np.cos(np.linspace(0, 2 * np.pi, n))
        alpha = 0.02 + 0.3 * sweep
        out = np.empty(n)
        zi = np.zeros(1)
        block = 256
        for b0 in range(0, n, block):
            b1 = min(n, b0 + block)
            a = float(alpha[(b0 + b1) // 2])
            out[b0:b1], zi = lfilter([a], [1, -(1 - a)], noise[b0:b1], zi=zi)
        sig = out * (np.sin(np.linspace(0, np.pi, n)) ** 1.5) * 3.2
        self._place(frame, sig, vol)

    def shimmer(self, frame, vol=0.05, freqs=(1568, 2093), dur=0.5, bus="sfx"):
        n = int(dur * SR)
        t = np.arange(n) / SR
        sig = sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs)
        sig *= self._envelope(n, 0.008, min(0.15, dur / 2), decay=0.16 if dur <= 0.6 else dur / 3)
        self._place(frame, sig, vol, 0.15, bus)

    def tone(self, frame, freq, dur, vol, tau=0.24):
        n = int(dur * SR)
        t = np.arange(n) / SR
        sig = (np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * freq * 2 * t)) * self._env(n, tau)
        sig *= self._envelope(n, 0.002, min(0.01, dur / 2))
        self._place(frame, sig, vol)

    def pad(self, freqs, start_s, dur_s, vol=0.05):
        for freq in freqs:
            self._place_at(start_s, self._oscillator(freq, dur_s, "pad"), vol / len(freqs), 0, "music")

    # ----------------------------------------------------------- mix/master
    @staticmethod
    def _reverb(signal, space=0.32):
        """Reverb estéreo Schroeder (4 combs com amortecimento + 2 allpass)."""
        if space <= 0:
            return signal
        out = np.zeros_like(signal)
        damp_sos = butter(1, 5200, "lowpass", fs=SR, output="sos")
        src = sosfilt(damp_sos, signal, axis=0)
        combs = ((0.0297, 0.0371, 0.0411, 0.0437), (0.0311, 0.0389, 0.0423, 0.0453))
        fb = 0.72 + 0.12 * min(1.0, space)
        for ch in range(2):
            x = src[:, ch]
            wet = np.zeros_like(x)
            for d_s in combs[ch]:
                wet += _comb(x, round(d_s * SR), fb)
            wet /= 4
            for d_s, g in ((0.005, 0.7), (0.0017, 0.7)):
                wet = _allpass(wet, round(d_s * SR), g)
            out[:, ch] = wet
        pre = round(0.012 * SR)
        delayed = np.zeros_like(out)
        delayed[pre:] = out[:-pre]
        return signal + delayed * space

    def _sidechain(self, signal):
        if self.pump <= 0 or not self._kicks:
            return signal
        n = len(signal)
        env = np.ones(n)
        rel = round(0.18 * SR)
        shape = 1 - self.pump * np.cos(np.linspace(0, np.pi / 2, rel)) ** 2
        for k in self._kicks:
            i = round(k * SR)
            if 0 <= i < n:
                j = min(n, i + rel)
                env[i:j] = np.minimum(env[i:j], shape[: j - i])
        return signal * env[:, None]

    def music_mix(self):
        pads = self._sidechain(self.pads)
        drums_wet = self._reverb(self.drums, self.space * 0.25) if self.space else self.drums
        tonal = self._reverb(self.music + pads, self.space)
        mix = tonal + drums_wet
        hp = butter(2, 28, "highpass", fs=SR, output="sos")  # remove subgrave inútil / DC
        return sosfilt(hp, mix, axis=0)

    def render(self, music_level=1.0, sfx_level=1.0):
        return self.music_mix() * music_level + self.buf * sfx_level

    def save(self, path, peak=None, music_level=1.0, sfx_level=1.0, target_lufs=-16.0,
             true_peak_db=-1.0, stems_dir=None):
        """Masteriza e grava WAV estéreo 48 kHz/16 bit com dither.

        Por padrão normaliza loudness para `target_lufs` e limita o true peak.
        `peak` (v1) ainda funciona: com `target_lufs=None` normaliza por pico.
        """
        music = self.music_mix()
        sfx = self.buf
        mix = music * music_level + sfx * sfx_level
        fade = min(round(0.01 * SR), len(mix) // 2)
        if fade:
            mix[:fade] *= np.linspace(0, 1, fade)[:, None]
            mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
        if target_lufs is not None:
            mix, gain = audio_mix.master(mix, SR, target_lufs, true_peak_db)
        else:
            ceiling = peak if peak is not None else 0.86
            mix = mix / max(1e-9, np.max(np.abs(mix))) * ceiling
            gain = ceiling
        path = Path(path)
        audio_mix.write_wav(path, mix, SR, rng=self.noise_rng)
        if stems_dir:
            stems = Path(stems_dir)
            g = gain if np.isscalar(gain) else 1.0
            audio_mix.write_wav(stems / "music.wav", np.clip(music * music_level * g, -1, 1), SR)
            audio_mix.write_wav(stems / "sfx.wav", np.clip(sfx * sfx_level * g, -1, 1), SR)
        lufs = audio_mix.integrated_loudness(mix, SR)
        tp = audio_mix.true_peak_db(mix, SR)
        print(f"{path} ok — {self.dur_s:.2f}s, estéreo, {SR} Hz, {lufs:.1f} LUFS, true peak {tp:.1f} dBTP")
        return {"path": str(path), "lufs": lufs, "true_peak_db": tp}


def scene_at_static(normalized, t):
    for s in normalized:
        if s["start"] - 1e-6 <= t < s["end"] - 1e-6:
            return s
    return None


def _comb(x, d, g):
    """y[n] = x[n] + g*y[n-d], vetorizado em blocos de d amostras."""
    y = np.copy(x)
    for b0 in range(d, len(x), d):
        b1 = min(len(x), b0 + d)
        y[b0:b1] += g * y[b0 - d:b1 - d]
    return y


def _allpass(x, d, g):
    """Allpass de Schroeder: y[n] = -g x[n] + x[n-d] + g y[n-d] (blocos)."""
    y = -g * x
    y[d:] += x[:-d]
    for b0 in range(d, len(x), d):
        b1 = min(len(x), b0 + d)
        y[b0:b1] += g * y[b0 - d:b1 - d]
    return y


def render_spec(spec_path, output_path, stems_dir=None):
    with open(spec_path, encoding="utf-8") as file:
        spec = json.load(file)
    return render_spec_dict(spec, output_path, stems_dir)


def render_spec_dict(spec, output_path, stems_dir=None):
    track = Track(spec["duration"], spec.get("seed", 7), spec.get("fps", 60))
    style = spec.get("style")
    bpm = track.score(
        spec.get("scenes", []),
        spec.get("bpm"),
        spec.get("key", "D"),
        spec.get("mode", "minor"),
        style=style,
        ending=spec.get("ending"),
        bpm_range=spec.get("bpm_range"),
    )
    if "auto_transition_sfx" in spec and not spec["auto_transition_sfx"]:
        pass  # o valor do estilo já foi aplicado; mantido para documentação
    methods = {"pop", "tick", "whoosh", "shimmer", "tone"}
    for event in spec.get("events", []):
        kind = event["type"]
        if kind not in methods:
            raise ValueError(f"Evento deve ser um de: {', '.join(sorted(methods))}")
        params = {k: v for k, v in event.items() if k not in ("type", "frame", "volume", "label")}
        if "volume" in event:
            params["vol"] = event["volume"]
        getattr(track, kind)(int(event["frame"]), **params)
    result = track.save(
        output_path,
        peak=spec.get("peak"),
        music_level=spec.get("music_level", 1.0),
        sfx_level=spec.get("sfx_level", 1.0),
        target_lufs=spec.get("loudness", -16.0),
        true_peak_db=spec.get("true_peak", -1.0),
        stems_dir=stems_dir,
    )
    print(f"Trilha {track.meta['style']} em {bpm} BPM, {len(spec.get('scenes', []))} cena(s) "
          f"e {len(spec.get('events', []))} evento(s)")
    result.update(track.meta)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera trilha musical e SFX a partir de uma timeline JSON")
    parser.add_argument("timeline", help="JSON com duração, cenas e eventos")
    parser.add_argument("output", help="Arquivo WAV de saída")
    parser.add_argument("--stems", help="Pasta para gravar stems separados (music.wav, sfx.wav)")
    args = parser.parse_args()
    render_spec(args.timeline, args.output, args.stems)
