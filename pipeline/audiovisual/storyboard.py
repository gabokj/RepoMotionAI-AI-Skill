"""Planejamento de Storyboard, Motion Design e Continuidade Visual.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from .script import CommercialScript, ScriptScene
from . import config

@dataclass
class MicroEvent:
    frame: int
    time_s: float
    description: str
    sfx_type: Optional[str] = None
    volume: float = 0.1

@dataclass
class StoryboardScene:
    id: int
    name: str
    start_frame: int
    end_frame: int
    duration_frames: int
    duration_s: float
    spoken_text: str
    screen_text: str
    visual_description: str
    camera_direction: str
    transition_in: str
    transition_out: str
    motion_elements: List[str]
    micro_events: List[MicroEvent] = field(default_factory=list)
    html_template_hint: str = ""

@dataclass
class Storyboard:
    title: str
    total_frames: int
    fps: int
    duration_s: float
    scenes: List[StoryboardScene]
    all_events: List[Dict[str, Any]] = field(default_factory=list)

def build_storyboard(script: CommercialScript, fps: int = 60) -> Storyboard:
    """Cria storyboard completo com sincronia quadro a quadro e micro-eventos regulares."""
    scenes: List[StoryboardScene] = []
    current_frame = 0
    all_sfx_events: List[Dict[str, Any]] = []
    
    for i, sc in enumerate(script.scenes):
        dur_frames = round(sc.target_duration_s * fps)
        start_f = current_frame
        end_f = start_f + dur_frames
        
        # Micro-eventos: garante micro-evento a cada 0.8s - 1.2s ao longo de toda a cena
        micro_events = []
        event_interval = int(1.0 * fps)
        
        # 1. Entrada da cena com SFX (se houver transição)
        trans_sfx = config.TRANSITIONS.get(sc.transition_out, {}).get("sfx")
        if i > 0 and trans_sfx:
            micro_events.append(MicroEvent(
                frame=start_f,
                time_s=round(start_f / fps, 3),
                description=f"Transição {sc.transition_out} com morph/reveal",
                sfx_type=trans_sfx,
                volume=0.08
            ))
            all_sfx_events.append({
                "frame": start_f,
                "type": trans_sfx,
                "volume": 0.08,
                "label": f"transicao_cena_{sc.id}"
            })
            
        # 2. Pop de texto / elemento nos primeiros frames
        pop_f = start_f + int(0.25 * fps)
        micro_events.append(MicroEvent(
            frame=pop_f,
            time_s=round(pop_f / fps, 3),
            description="Entrada de tipografia cinética com física spring",
            sfx_type="pop",
            volume=0.14
        ))
        all_sfx_events.append({
            "frame": pop_f,
            "type": "pop",
            "volume": 0.14,
            "label": f"texto_pop_cena_{sc.id}"
        })
        
        # 3. Micro-eventos subsequentes a cada ~1s até o fim da cena
        curr_ev_f = pop_f + event_interval
        while curr_ev_f < end_f - int(0.2 * fps):
            ev_type = "tick" if curr_ev_f % 2 == 0 else "shimmer"
            micro_events.append(MicroEvent(
                frame=curr_ev_f,
                time_s=round(curr_ev_f / fps, 3),
                description="Micro-evento de ritmo visual e destaque",
                sfx_type=ev_type,
                volume=0.05
            ))
            all_sfx_events.append({
                "frame": curr_ev_f,
                "type": ev_type,
                "volume": 0.05,
                "label": f"ritmo_cena_{sc.id}_{curr_ev_f}"
            })
            curr_ev_f += event_interval
            
        trans_in = script.scenes[i - 1].transition_out if i > 0 else "none"
        
        scenes.append(StoryboardScene(
            id=sc.id,
            name=sc.name,
            start_frame=start_f,
            end_frame=end_f,
            duration_frames=dur_frames,
            duration_s=sc.target_duration_s,
            spoken_text=sc.spoken_text,
            screen_text=sc.screen_text,
            visual_description=sc.visual_description,
            camera_direction=sc.camera_movement,
            transition_in=trans_in,
            transition_out=sc.transition_out,
            motion_elements=[
                "Fundo vivo com partículas determinísticas e gradiente",
                "Tipografia kinetic com peso pesado e spring(t, 5.2, 0.55)",
                "Camada 3D com perspective 1200px e sombra dinâmica"
            ],
            micro_events=micro_events,
            html_template_hint=f"function s{sc.id}(n) {{ /* cena {sc.id} */ }}"
        ))
        
        current_frame = end_f
        
    return Storyboard(
        title=f"Storyboard - {script.title}",
        total_frames=current_frame,
        fps=fps,
        duration_s=round(current_frame / fps, 2),
        scenes=scenes,
        all_events=all_sfx_events
    )
