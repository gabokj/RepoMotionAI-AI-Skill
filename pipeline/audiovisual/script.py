"""Roteirização Inteligente baseada em Evidências e Orçamento Temporal.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from . import config
from .narration import estimate_speech_duration

@dataclass
class ScriptScene:
    id: int
    name: str
    target_duration_s: float
    spoken_text: str
    screen_text: str
    visual_description: str
    camera_movement: str
    transition_out: str
    estimated_speech_s: float = 0.0

@dataclass
class CommercialScript:
    title: str
    content_type: str
    target_duration_s: float
    audience: str
    main_message: str
    voice_profile: str
    music_style: str
    scenes: List[ScriptScene] = field(default_factory=list)
    total_spoken_words: int = 0
    total_speech_duration_s: float = 0.0

def generate_script(
    evidence: Dict[str, Any],
    duration_s: float = 15.0,
    content_type: str = "ad",
    voice_profile: str = "commercial_premium",
    audience: str = "desenvolvedores e criadores de conteúdo",
    cta: str = "Experimente agora no GitHub"
) -> CommercialScript:
    """Gera roteiro inteligente com orçamento rigoroso de tempo e palavras."""
    proj = evidence.get("project_name", "RepoMotion AI")
    desc = evidence.get("description", "Automação audiovisual inteligente")
    features = evidence.get("features", ["Renderização em 60fps", "Trilha procedural", "Mixagem automática"])
    # Limpa features para frases concisas e diretas (máximo 6 palavras cada)
    def clean_feat(f: str) -> str:
        f = f.split(":")[0].strip()
        words = f.split()
        return " ".join(words[:5])
        
    feat1 = clean_feat(features[0]) if features else "Motion design"
    feat2 = clean_feat(features[1]) if len(features) > 1 else "Áudio sincronizado"
    
    st_info = config.CONTENT_TYPES.get(content_type, config.CONTENT_TYPES["ad"])
    music_style = st_info.get("music", "modern_advertising")
    
    # Orçamento de cenas baseado na duração
    scenes: List[ScriptScene] = []
    
    if duration_s <= 12.0:
        # 10s: Hook/Solução direta + CTA
        scenes = [
            ScriptScene(
                id=1, name="Hook & Solução",
                target_duration_s=round(duration_s * 0.65, 1),
                spoken_text=f"{proj}. {desc}.",
                screen_text=proj.upper(),
                visual_description="Tipografia protagonista cinética com logo 3D flutuando sobre fundo estúdio vivo",
                camera_movement="slow_push_in",
                transition_out="zoom_punch"
            ),
            ScriptScene(
                id=2, name="CTA",
                target_duration_s=round(duration_s * 0.35, 1),
                spoken_text=f"{cta}.",
                screen_text=cta.upper(),
                visual_description="Card de ação clicável com varredura de luz e partículas",
                camera_movement="slow_drift",
                transition_out="fade_out"
            )
        ]
    elif duration_s <= 20.0:
        # 15s padrão comercial: Hook -> Demonstração -> CTA
        s1_dur = round(duration_s * 0.30, 1)
        s2_dur = round(duration_s * 0.48, 1)
        s3_dur = round(duration_s * 0.22, 1)
        
        scenes = [
            ScriptScene(
                id=1, name="Hook",
                target_duration_s=s1_dur,
                spoken_text=f"Chega de vídeos genéricos para apresentar seu projeto.",
                screen_text="CHEGA DE VÍDEOS GENÉRICOS",
                visual_description="Abertura cinematográfica com profundidade e tipografia de alto impacto",
                camera_movement="slow_push_in",
                transition_out="morph"
            ),
            ScriptScene(
                id=2, name="Solução e Demonstração",
                target_duration_s=s2_dur,
                spoken_text=f"Com o {proj}, tenha {feat1.lower()} e {feat2.lower()}.",
                screen_text=feat1.upper(),
                visual_description="Demonstração interativa de interface fluida com dados reais e motion cards 3D",
                camera_movement="orbit_tilt",
                transition_out="zoom_through"
            ),
            ScriptScene(
                id=3, name="CTA",
                target_duration_s=s3_dur,
                spoken_text=f"{cta}.",
                screen_text=cta.upper(),
                visual_description="Botão pílula elegante de fechamento com logo e assinatura",
                camera_movement="slow_drift",
                transition_out="fade_out"
            )
        ]
    elif duration_s <= 35.0:
        # 30s completo: Hook -> Problema -> Solução -> Feature 1 -> Feature 2 -> CTA
        scenes = [
            ScriptScene(
                id=1, name="Hook",
                target_duration_s=5.0,
                spoken_text=f"Seu código merece um vídeo que chame atenção de verdade.",
                screen_text="IMPACTO VISUAL IMEDIATO",
                visual_description="Texto dinâmico em 3D entrando com física subamortecida",
                camera_movement="slow_push_in",
                transition_out="morph"
            ),
            ScriptScene(
                id=2, name="Contexto & Solução",
                target_duration_s=7.0,
                spoken_text=f"O {proj} transforma repositórios e produtos em motion design pronto para anúncios.",
                screen_text=proj.upper(),
                visual_description="Página de app surgindo em perspectiva isométrica com iluminação ambiente",
                camera_movement="pan_right",
                transition_out="cut"
            ),
            ScriptScene(
                id=3, name="Demonstração 1",
                target_duration_s=7.0,
                spoken_text=f"Tenha {feat1.lower()} totalmente sincronizado ao áudio.",
                screen_text="SINCRONIA QUADRO A QUADRO",
                visual_description="Gráficos animados com contadores dinâmicos e partículas",
                camera_movement="orbit_tilt",
                transition_out="zoom_through"
            ),
            ScriptScene(
                id=4, name="Demonstração 2",
                target_duration_s=6.0,
                spoken_text=f"Com trilha sonora original gerada para o seu conteúdo.",
                screen_text="TRILHA PROCEDURAL ORIGINAL",
                visual_description="Forma de onda sonora minimalista reagindo em harmonia com as cores da marca",
                camera_movement="slow_drift",
                transition_out="morph"
            ),
            ScriptScene(
                id=5, name="Fechamento & CTA",
                target_duration_s=5.0,
                spoken_text=f"{cta}.",
                screen_text=cta.upper(),
                visual_description="Card final com botão interativo e link direto",
                camera_movement="slow_drift",
                transition_out="fade_out"
            )
        ]
    else:
        # 60s detalhado
        scenes = [
            ScriptScene(id=1, name="Hook", target_duration_s=8.0, spoken_text=f"Como destacar seu software em um feed cheio de distrações?", screen_text="DESTAQUE SEU PRODUTO", visual_description="Abertura imersiva", camera_movement="slow_push_in", transition_out="morph"),
            ScriptScene(id=2, name="Problema", target_duration_s=10.0, spoken_text="Apresentações estáticas não convertem mais.", screen_text="VÍDEOS COMERCIAIS QUE CONVERTEM", visual_description="Cena comparativa dinâmica", camera_movement="pan_left", transition_out="cut"),
            ScriptScene(id=3, name="Solução", target_duration_s=12.0, spoken_text=f"O {proj} automatiza toda a produção audiovisual profissional.", screen_text=proj.upper(), visual_description="UI em perspectiva 3D", camera_movement="orbit_tilt", transition_out="zoom_through"),
            ScriptScene(id=4, name="Recursos", target_duration_s=14.0, spoken_text=f"Você conta com {feat1.lower()} e {feat2.lower()}.", screen_text="MOTION DESIGN + ÁUDIO", visual_description="Multi-camadas com física e profundidade", camera_movement="pan_right", transition_out="morph"),
            ScriptScene(id=5, name="Fecho & CTA", target_duration_s=16.0, spoken_text=f"{cta}.", screen_text=cta.upper(), visual_description="Fecho elegante com logotipo e CTA", camera_movement="slow_drift", transition_out="fade_out"),
        ]
        
    # Calcula duração de fala de cada cena e valida tempo
    total_words = 0
    total_speech_s = 0.0
    for sc in scenes:
        sc.estimated_speech_s = estimate_speech_duration(sc.spoken_text, voice_profile)
        words = len(re.findall(r"\b\w+\b", sc.spoken_text))
        total_words += words
        total_speech_s += sc.estimated_speech_s
        
    return CommercialScript(
        title=f"Roteiro Comercial - {proj}",
        content_type=content_type,
        target_duration_s=duration_s,
        audience=audience,
        main_message=desc,
        voice_profile=voice_profile,
        music_style=music_style,
        scenes=scenes,
        total_spoken_words=total_words,
        total_speech_duration_s=round(total_speech_s, 2)
    )

def validate_script(script: CommercialScript) -> List[str]:
    """Checa clichês proibidos, estouro de tempo e densidade de leitura."""
    warnings = []
    
    # Checagem de clichês vazios
    all_text = " ".join(s.spoken_text for s in script.scenes).lower()
    for c in config.SCRIPT_CLICHES:
        if c in all_text:
            warnings.append(f"Clichê detectado no roteiro: '{c}'. Prefira fatos concretos.")
            
    # Checagem de tempo de fala x duração da cena
    for s in script.scenes:
        if s.estimated_speech_s > s.target_duration_s:
            warnings.append(
                f"Cena {s.id} ('{s.name}'): fala estimada ({s.estimated_speech_s:.1f}s) "
                f"ultrapassa a duração da cena ({s.target_duration_s:.1f}s). Reduza o texto."
            )
            
    # Checagem de legibilidade do texto na tela
    for s in script.scenes:
        chars = len(s.screen_text)
        cps = chars / max(0.5, s.target_duration_s)
        if cps > config.QA_THRESHOLDS["max_chars_per_second"]:
            warnings.append(
                f"Cena {s.id}: texto na tela muito longo para leitura rápida ({cps:.1f} chars/s > {config.QA_THRESHOLDS['max_chars_per_second']})."
            )
            
    return warnings
