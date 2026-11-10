"""Inteligência audiovisual do RepoMotion AI / Motion Frames.

Módulos (cada um com responsabilidade única):

- ``config``      presets centralizados (modos, plataformas, estilos musicais,
                   perfis de voz, estilos de edição, alvos de loudness)
- ``planner``     decide a estratégia de produção a partir do briefing
- ``evidence``    analisa um repositório e extrai fatos com fonte
- ``script``      modelos de roteiro, orçamento de fala e validação
- ``storyboard``  storyboard por cena, continuidade e sincronização
- ``music``       direção musical, prompt musical e arranjo por duração
- ``music_fit``   adapta uma música externa à duração (sem cortes abruptos)
- ``narration``   direção de voz, normalização de texto, SSML e provedores TTS
- ``audio_mix``   loudness BS.1770, true peak, ducking, EQ e limitador
- ``qa``          relatório de qualidade de áudio, vídeo, roteiro e storyboard
- ``wavio``       leitura/escrita de WAV e conversão via ffmpeg
"""

__version__ = "2.0.0"

