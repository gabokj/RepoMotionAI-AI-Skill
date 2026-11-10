"""Suíte de Testes Automatizados da Evolução Audiovisual RepoMotion AI.         
"""
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.audiovisual import config
from pipeline.audiovisual import script
from pipeline.audiovisual import storyboard
from pipeline.audiovisual import narration
from pipeline.audiovisual import music
from pipeline.audiovisual import audio_mix
from pipeline.audiovisual import music_fit
from pipeline.audiovisual import qa
from pipeline import sfx_kit

class TestAudiovisualEvolution(unittest.TestCase):

    def test_script_generation_and_validation(self):
        evidence = {
            "project_name": "RepoMotion AI",
            "description": "Criação de vídeos comerciais automatizados",
            "features": ["Síntese musical procedural", "Sincronia audiovisual quadro a quadro"]
        }
        scr = script.generate_script(evidence, duration_s=15.0, content_type="ad")
        self.assertEqual(len(scr.scenes), 3)
        self.assertLessEqual(scr.total_speech_duration_s, scr.target_duration_s + 1.0)
        
        warnings = script.validate_script(scr)
        self.assertEqual(len(warnings), 0, f"Avisos inesperados: {warnings}")

    def test_narration_normalization_and_ssml(self):
        text = "O app usa IA, APIs e CSS para renderizar a 60 FPS."
        norm = narration.normalize_text_for_speech(text)
        self.assertIn("I Á", norm)
        self.assertIn("A Pê Ís", norm)
        self.assertIn("Cê Esse Esse", norm)
        
        ssml = narration.generate_ssml(text, "commercial_premium")
        self.assertTrue(ssml.startswith("<speak"))
        self.assertIn("<prosody", ssml)

    def test_music_planning_and_styles(self):
        brief = music.MusicBrief(
            duration_s=15.0,
            product="RepoMotion",
            objective="anúncio",
            emotion="moderno, refinado e confiante",
            content_type="ad"
        )
        plan = music.plan_music(brief)
        self.assertIn("prompt", plan)
        self.assertIn("bpm", plan)
        self.assertIn("style", plan)
        self.assertIn("sections", plan)
        self.assertIn("Suitable for commercial advertising", plan["prompt"])

    def test_sfx_kit_synthesis(self):
        track = sfx_kit.Track(dur_s=4.0, seed=42)
        bpm = track.score([
            {"start_frame": 0, "end_frame": 120, "section": "intro", "energy": 0.3},
            {"start_frame": 120, "end_frame": 240, "section": "main", "energy": 0.7}
        ], style="modern_advertising")
        self.assertGreater(bpm, 0)
        sig = track.music_mix()
        self.assertEqual(sig.shape[1], 2) # estéreo
        self.assertEqual(len(sig), round(4.0 * 48000))

    def test_audio_mix_and_ducking(self):
        sr = 48000
        dur_s = 4.0
        n = round(dur_s * sr)
        t = np.arange(n) / sr
        
        # Cria fala simulada (senoide harmônica audível nos gates BS.1770: 1.0s a 3.0s)
        voice = np.zeros((n, 2))
        voice[round(1.0*sr):round(3.0*sr), 0] = np.sin(2 * np.pi * 300 * t[:round(2.0*sr)]) * 0.4
        voice[round(1.0*sr):round(3.0*sr), 1] = voice[round(1.0*sr):round(3.0*sr), 0]
        
        # Música de fundo
        music_sig = np.sin(2 * np.pi * 440 * t)[:, None] * 0.2
        music_sig = np.repeat(music_sig, 2, axis=1)
        
        mixed, report = audio_mix.mix_tracks(
            voice=voice,
            music=music_sig,
            sr=sr,
            duration_s=dur_s,
            target_lufs=-14.0
        )
        
        self.assertEqual(len(mixed), n)
        self.assertAlmostEqual(report["lufs"], -14.0, delta=1.5)
        self.assertLessEqual(report["true_peak_db"], -0.5)

    def test_music_adaptation_fit(self):
        sr = 48000
        short_music = np.ones((round(2.0 * sr), 2)) * 0.1
        adapted = music_fit.adapt_music_to_duration(short_music, target_duration_s=5.0, sr=sr)
        self.assertEqual(len(adapted), round(5.0 * sr))

    def test_qa_evaluation(self):
        sr = 48000
        test_audio = np.random.uniform(-0.1, 0.1, (round(2.0 * sr), 2))
        res = qa.evaluate_audio_quality(test_audio, sr=sr, target_lufs=-14.0)
        self.assertIn("status", res)
        self.assertIn("lufs", res)
        self.assertIn("true_peak_db", res)

if __name__ == "__main__":
    unittest.main()
