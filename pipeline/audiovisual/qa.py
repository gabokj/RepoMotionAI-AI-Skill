"""Sistema de Avaliação e Relatório de Qualidade Audiovisual."""
from __future__ import annotations

from typing import Dict, Any, List, Optional
import numpy as np

from . import config
from . import audio_mix

def evaluate_audio_quality(
    mixed_audio: np.ndarray,
    sr: int = 48000,
    target_lufs: float = -14.0,
    voice_audio: Optional[np.ndarray] = None,
    music_audio: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """Avaliação técnica profunda do áudio final."""
    issues = []
    passes = []
    
    # 1. Loudness integrado (BS.1770)
    lufs = audio_mix.integrated_loudness(mixed_audio, sr)
    diff_lufs = abs(lufs - target_lufs)
    if diff_lufs <= config.QA_THRESHOLDS["lufs_tolerance"]:
        passes.append(f"Loudness integrado: {lufs:.1f} LUFS (alvo: {target_lufs:.1f} ± {config.QA_THRESHOLDS['lufs_tolerance']} LU)")
    else:
        issues.append(f"Loudness fora do alvo: {lufs:.1f} LUFS vs alvo {target_lufs:.1f} LUFS")
        
    # 2. True Peak
    tp = audio_mix.true_peak_db(mixed_audio, sr)
    if tp <= config.QA_THRESHOLDS["max_true_peak_db"]:
        passes.append(f"True Peak seguro: {tp:.2f} dBTP (teto: {config.QA_THRESHOLDS['max_true_peak_db']} dBTP)")
    else:
        issues.append(f"Risco de clipping inter-amostra: True Peak em {tp:.2f} dBTP")
        
    # 3. Amostras clipadas
    clipped = np.sum(np.abs(mixed_audio) >= 0.9999)
    if clipped == 0:
        passes.append("Sem clipping digital de amostras (0 amostras no teto)")
    else:
        issues.append(f"Clipping digital detectado: {clipped} amostras saturadas")
        
    # 4. Relação Voz sobre Música
    if voice_audio is not None and music_audio is not None:
        vom = audio_mix.voice_to_music_ratio_db(voice_audio, music_audio, sr)
        if vom is not None:
            if vom < config.QA_THRESHOLDS["min_voice_over_music_db"]:
                issues.append(f"Música muito alta durante a fala: voz apenas {vom:.1f} dB acima da música (mínimo recomendado: {config.QA_THRESHOLDS['min_voice_over_music_db']} dB)")
            else:
                passes.append(f"Clareza da fala excelente: voz {vom:.1f} dB acima da música durante o discurso")
                
    return {
        "status": "PASS" if not issues else "WARN",
        "lufs": round(lufs, 2),
        "true_peak_db": round(tp, 2),
        "passes": passes,
        "issues": issues,
    }

def evaluate_storyboard_quality(storyboard) -> Dict[str, Any]:
    """Verifica densidade de micro-eventos e ritmo do storyboard."""
    issues = []
    passes = []
    
    # 1. Checar densidade de micro-eventos (máximo 1.8s sem evento)
    prev_f = 0
    max_gap_f = int(1.8 * storyboard.fps)
    all_events_sorted = sorted(storyboard.all_events, key=lambda e: e["frame"])
    
    for ev in all_events_sorted:
        gap = ev["frame"] - prev_f
        if gap > max_gap_f and prev_f > 0:
            issues.append(f"Lacuna sem micro-eventos de {gap/storyboard.fps:.1f}s no quadro {prev_f} ao {ev['frame']}.")
        prev_f = ev["frame"]
        
    if not issues:
        passes.append("Densidade de micro-eventos aprovada (nenhum trecho superior a 1.8s sem eventos visuais/sonoros)")
        
    # 2. Duração mínima por cena
    for sc in storyboard.scenes:
        if sc.duration_s < config.QA_THRESHOLDS["min_scene_s"]:
            issues.append(f"Cena {sc.id} muito curta ({sc.duration_s:.2f}s < {config.QA_THRESHOLDS['min_scene_s']}s)")
            
    if not any("Cena" in iss for iss in issues):
        passes.append(f"Todas as {len(storyboard.scenes)} cenas respeitam a duração mínima confortável de visualização")
        
    return {
        "status": "PASS" if not issues else "WARN",
        "passes": passes,
        "issues": issues,
    }

def generate_quality_report(audio_qa: Dict[str, Any], storyboard_qa: Dict[str, Any], script_warnings: List[str]) -> str:
    """Gera relatório de qualidade em Markdown legível e detalhado."""
    overall_ok = (audio_qa["status"] == "PASS" and storyboard_qa["status"] == "PASS" and not script_warnings)
    badge = "✅ APROVADO PARA PRODUÇÃO" if overall_ok else "⚠️ REVISÕES RECOMENDADAS"
    
    md = [
        f"## 📋 Relatório de Qualidade Audiovisual — {badge}\n",
        "### 🎧 Áudio & Mixagem",
    ]
    for p in audio_qa.get("passes", []):
        md.append(f"- [OK] {p}")
    for i in audio_qa.get("issues", []):
        md.append(f"- ⚠️ {i}")
        
    md.append("\n### 🎬 Storyboard & Motion Design")
    for p in storyboard_qa.get("passes", []):
        md.append(f"- [OK] {p}")
    for i in storyboard_qa.get("issues", []):
        md.append(f"- ⚠️ {i}")
        
    md.append("\n### 📝 Roteiro & Narrativa")
    if not script_warnings:
        md.append("- [OK] Roteiro conciso, sem clichês vazios e com orçamentos de leitura respeitados.")
    else:
        for w in script_warnings:
            md.append(f"- ⚠️ {w}")
            
    return "\n".join(md)

