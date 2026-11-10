"""Planejador e Orquestrador Geral de Produção Audiovisual.    
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional

from . import config
from .evidence import analyze_repo_evidence
from .script import generate_script, validate_script
from .storyboard import build_storyboard
from .narration import get_voice_direction, generate_ssml, synthesize_mock_speech
from .music import MusicBrief, plan_music, to_timeline
from .qa import evaluate_audio_quality, evaluate_storyboard_quality, generate_quality_report
from .audio_mix import mix_tracks, write_wav

def produce_video_project(
    repo_path: str | Path,
    output_dir: str | Path,
    duration_s: float = 15.0,
    content_type: str = "ad",
    platform: str = "reels",
    voice_profile: str = "commercial_premium",
    music_style: Optional[str] = None,
    cta: str = "Experimente agora no GitHub",
    seed: int = 7
) -> Dict[str, Any]:
    """Executa o pipeline completo de produção inteligente."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    # 1. Extração de evidências
    evidence = analyze_repo_evidence(repo_path)
    
    # 2. Roteiro inteligente
    script = generate_script(
        evidence=evidence,
        duration_s=duration_s,
        content_type=content_type,
        voice_profile=voice_profile,
        cta=cta
    )
    script_warnings = validate_script(script)
    
    # 3. Storyboard
    storyboard = build_storyboard(script, fps=60)
    storyboard_qa = evaluate_storyboard_quality(storyboard)
    
    # 4. Narração (geração de SSML e áudio de voz sincronizado)
    full_speech_text = " ".join(sc.spoken_text for sc in script.scenes if sc.spoken_text)
    ssml = generate_ssml(full_speech_text, voice_profile)
    voice_audio = synthesize_mock_speech(full_speech_text, voice_profile, duration_s=storyboard.duration_s)
    
    # 5. Direção musical contextual
    brief = MusicBrief(
        duration_s=storyboard.duration_s,
        product=evidence.get("project_name", "RepoMotion"),
        objective="anúncio comercial de alta conversão",
        emotion="moderno, refinado e confiante",
        content_type=content_type,
        platform=platform,
        has_narration=True,
        style=music_style,
        seed=seed
    )
    music_plan = plan_music(brief)
    timeline = to_timeline(
        music_plan,
        duration_s=storyboard.duration_s,
        fps=60,
        events=storyboard.all_events
    )
    
    # 6. Salvar artefatos intermediários
    (out / "script.json").write_text(json.dumps({
        "title": script.title,
        "content_type": script.content_type,
        "duration_s": script.target_duration_s,
        "words": script.total_spoken_words,
        "scenes": [s.__dict__ for s in script.scenes]
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    
    (out / "storyboard.json").write_text(json.dumps({
        "title": storyboard.title,
        "total_frames": storyboard.total_frames,
        "fps": storyboard.fps,
        "scenes": [
            {
                "id": s.id,
                "name": s.name,
                "start_frame": s.start_frame,
                "end_frame": s.end_frame,
                "duration_frames": s.duration_frames,
                "screen_text": s.screen_text,
                "spoken_text": s.spoken_text,
                "visual": s.visual_description,
                "camera": s.camera_direction,
                "transition_out": s.transition_out
            } for s in storyboard.scenes
        ],
        "events": storyboard.all_events
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    
    (out / "narration.ssml").write_text(ssml, encoding="utf-8")
    (out / "music_timeline.json").write_text(json.dumps(timeline, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "music_prompt.txt").write_text(music_plan["prompt"], encoding="utf-8")
    
    # 7. Síntese musical via sfx_kit
    from .. import sfx_kit
    music_wav_path = out / "soundtrack.wav"
    sfx_kit.render_spec_dict(timeline, str(music_wav_path))
    
    # Lê música sintetizada
    from . import audio_mix
    music_audio = audio_mix.read_audio(music_wav_path, sr=48000, stereo=True)
    
    # 8. Mixagem Profissional com Ducking e Normalização
    final_mix, mix_report = mix_tracks(
        voice=voice_audio,
        music=music_audio,
        sfx=None,
        sr=48000,
        duration_s=storyboard.duration_s,
        target_lufs=-14.0,
        music_intensity="medium"
    )
    
    final_audio_path = out / "master_audio.wav"
    write_wav(final_audio_path, final_mix, sr=48000)
    
    # 9. Avaliação e Relatório de QA
    audio_qa = evaluate_audio_quality(
        final_mix,
        sr=48000,
        target_lufs=-14.0,
        voice_audio=mix_report.get("voice_track"),
        music_audio=mix_report.get("music_track")
    )
    
    report_md = generate_quality_report(audio_qa, storyboard_qa, script_warnings)
    (out / "QA_REPORT.md").write_text(report_md, encoding="utf-8")
    
    return {
        "status": "SUCCESS",
        "output_dir": str(out),
        "duration_s": storyboard.duration_s,
        "total_frames": storyboard.total_frames,
        "master_audio": str(final_audio_path),
        "script_warnings": script_warnings,
        "qa_summary": {
            "audio": audio_qa["status"],
            "storyboard": storyboard_qa["status"],
            "lufs": audio_qa["lufs"],
            "true_peak": audio_qa["true_peak_db"]
        }
    }
