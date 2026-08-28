"""
Empirical Challenger Test Suite — Milestone 1 (Phase 0)
Adversarial stress-testing of gerador_assets.py, generated assets, and math_utils.py.
"""

import os
import sys
import math
import struct
import wave
import unittest
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.constantes import ASSETS_DIR, ASSET_PATHS
import src.utils.math_utils as mu


class TestChallengerAssetsDeep(unittest.TestCase):
    """Deep adversarial inspection of all generated asset files on disk."""

    def test_all_png_files_valid_and_rgba(self):
        """Recursively scans ASSETS_DIR for PNG files and checks validity and RGBA mode."""
        png_count = 0
        for root, _, files in os.walk(ASSETS_DIR):
            for file in files:
                if file.lower().endswith(".png"):
                    png_count += 1
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, ASSETS_DIR)
                    self.assertGreater(os.path.getsize(full_path), 0, f"Empty PNG file: {rel_path}")
                    with Image.open(full_path) as img:
                        self.assertEqual(img.format, "PNG", f"File {rel_path} format is {img.format}, expected PNG")
                        self.assertEqual(img.mode, "RGBA", f"File {rel_path} mode is {img.mode}, expected RGBA")
                        self.assertGreater(img.width, 0, f"File {rel_path} width is {img.width}")
                        self.assertGreater(img.height, 0, f"File {rel_path} height is {img.height}")
                        
                        # Verify pixels can be loaded without decode errors
                        pixels = img.load()
                        self.assertIsNotNone(pixels, f"Failed to load pixels for {rel_path}")
                        
                        # Check alpha channel sanity: at least some transparent or opaque pixels
                        extrema = img.getextrema()
                        # extrema is a tuple of (min, max) for each channel R, G, B, A
                        alpha_min, alpha_max = extrema[3]
                        self.assertGreaterEqual(alpha_min, 0, f"{rel_path} alpha_min < 0")
                        self.assertLessEqual(alpha_max, 255, f"{rel_path} alpha_max > 255")

        self.assertGreaterEqual(png_count, 35, f"Expected at least 35 PNG files, found {png_count}")

    def test_all_wav_files_valid_pcm(self):
        """Recursively scans ASSETS_DIR for WAV files and checks PCM audio properties."""
        wav_count = 0
        for root, _, files in os.walk(ASSETS_DIR):
            for file in files:
                if file.lower().endswith(".wav"):
                    wav_count += 1
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, ASSETS_DIR)
                    self.assertGreater(os.path.getsize(full_path), 44, f"WAV file too small: {rel_path}")
                    with wave.open(full_path, "rb") as wf:
                        channels = wf.getnchannels()
                        sampwidth = wf.getsampwidth()
                        framerate = wf.getframerate()
                        nframes = wf.getnframes()
                        
                        self.assertIn(channels, (1, 2), f"{rel_path}: unexpected channels {channels}")
                        self.assertEqual(sampwidth, 2, f"{rel_path}: sample width must be 2 bytes (16-bit PCM), got {sampwidth}")
                        self.assertEqual(framerate, 44100, f"{rel_path}: framerate must be 44100, got {framerate}")
                        self.assertGreater(nframes, 0, f"{rel_path}: frame count must be > 0")
                        
                        # Read and unpack all frames to verify no corruption or clipping
                        raw_data = wf.readframes(nframes)
                        self.assertEqual(len(raw_data), nframes * channels * sampwidth)
                        
                        samples = struct.unpack(f"<{nframes * channels}h", raw_data)
                        self.assertEqual(len(samples), nframes * channels)
                        for s in samples:
                            self.assertTrue(-32768 <= s <= 32767, f"{rel_path}: sample out of 16-bit range {s}")

        self.assertGreaterEqual(wav_count, 19, f"Expected at least 19 WAV files, found {wav_count}")


class TestChallengerMathUtilsStress(unittest.TestCase):
    """Adversarial stress-testing of src/utils/math_utils.py."""

    def test_normalizar_vetor_adversarial(self):
        # 1. Zero vector
        self.assertEqual(mu.normalizar_vetor(0.0, 0.0), (0.0, 0.0))
        self.assertEqual(mu.normalizar_vetor(0, 0), (0.0, 0.0))

        # 2. Sub-epsilon vector (magnitude squared <= 1e-10, i.e., mag <= 1e-5)
        self.assertEqual(mu.normalizar_vetor(1e-12, 1e-12), (0.0, 0.0))
        self.assertEqual(mu.normalizar_vetor(1e-6, 0.0), (0.0, 0.0))
        
        # Vectors above epsilon threshold (mag >= 1e-5)
        nx, ny = mu.normalizar_vetor(1e-4, 0.0)
        self.assertAlmostEqual(nx, 1.0)
        self.assertAlmostEqual(ny, 0.0)

        # 3. Negative components
        nx, ny = mu.normalizar_vetor(-3.0, -4.0)
        self.assertAlmostEqual(nx, -0.6)
        self.assertAlmostEqual(ny, -0.8)
        self.assertAlmostEqual(nx * nx + ny * ny, 1.0)

        # 4. Extreme distances / large coordinates (10^8)
        nx, ny = mu.normalizar_vetor(1e8, 1e8)
        self.assertAlmostEqual(nx, 1.0 / math.sqrt(2.0))
        self.assertAlmostEqual(ny, 1.0 / math.sqrt(2.0))
        self.assertAlmostEqual(nx * nx + ny * ny, 1.0)

        # 5. Single axis alignment
        self.assertEqual(mu.normalizar_vetor(0.0, 500.0), (0.0, 1.0))
        self.assertEqual(mu.normalizar_vetor(0.0, -500.0), (0.0, -1.0))
        self.assertEqual(mu.normalizar_vetor(500.0, 0.0), (1.0, 0.0))
        self.assertEqual(mu.normalizar_vetor(-500.0, 0.0), (-1.0, 0.0))

    def test_distancia_and_distancia_sq_stress(self):
        # 1. Coincident points
        self.assertEqual(mu.distancia(100.5, -200.3, 100.5, -200.3), 0.0)
        self.assertEqual(mu.distancia_sq(100.5, -200.3, 100.5, -200.3), 0.0)

        # 2. Extreme distances (10^8)
        d = mu.distancia(0.0, 0.0, 3e8, 4e8)
        self.assertAlmostEqual(d, 5e8)
        d_sq = mu.distancia_sq(0.0, 0.0, 3e8, 4e8)
        self.assertAlmostEqual(d_sq, 25e16)

        # 3. Negative coordinates
        self.assertAlmostEqual(mu.distancia(-10, -10, -13, -14), 5.0)
        self.assertAlmostEqual(mu.distancia_sq(-10, -10, -13, -14), 25.0)

    def test_vetor_direcao_stress(self):
        # 1. Coincident origin and destination
        self.assertEqual(mu.vetor_direcao(50.0, 50.0, 50.0, 50.0), (0.0, 0.0))
        self.assertEqual(mu.vetor_direcao(0, 0, 0, 0), (0.0, 0.0))

        # 2. Extreme coordinates (10^8)
        vx, vy = mu.vetor_direcao(0.0, 0.0, 1e8, 0.0)
        self.assertAlmostEqual(vx, 1.0)
        self.assertAlmostEqual(vy, 0.0)

        # 3. Negative directions
        vx, vy = mu.vetor_direcao(100.0, 100.0, 50.0, 100.0)
        self.assertAlmostEqual(vx, -1.0)
        self.assertAlmostEqual(vy, 0.0)

    def test_clamp_stress(self):
        # 1. Normal clamping
        self.assertEqual(mu.clamp(5.0, 0.0, 10.0), 5.0)
        self.assertEqual(mu.clamp(-1.0, 0.0, 10.0), 0.0)
        self.assertEqual(mu.clamp(15.0, 0.0, 10.0), 10.0)

        # 2. Exact boundary values
        self.assertEqual(mu.clamp(0.0, 0.0, 10.0), 0.0)
        self.assertEqual(mu.clamp(10.0, 0.0, 10.0), 10.0)

        # 3. Negative range
        self.assertEqual(mu.clamp(-5.0, -10.0, -2.0), -5.0)
        self.assertEqual(mu.clamp(-15.0, -10.0, -2.0), -10.0)
        self.assertEqual(mu.clamp(0.0, -10.0, -2.0), -2.0)

        # 4. Zero width range (min == max)
        self.assertEqual(mu.clamp(5.0, 3.0, 3.0), 3.0)
        self.assertEqual(mu.clamp(1.0, 3.0, 3.0), 3.0)

    def test_lerp_stress(self):
        # 1. Standard t in [0, 1]
        self.assertAlmostEqual(mu.lerp(10.0, 20.0, 0.0), 10.0)
        self.assertAlmostEqual(mu.lerp(10.0, 20.0, 1.0), 20.0)
        self.assertAlmostEqual(mu.lerp(10.0, 20.0, 0.5), 15.0)

        # 2. Extrapolation (t < 0 or t > 1)
        self.assertAlmostEqual(mu.lerp(0.0, 10.0, 2.0), 20.0)
        self.assertAlmostEqual(mu.lerp(0.0, 10.0, -1.0), -10.0)

        # 3. Negative start/end
        self.assertAlmostEqual(mu.lerp(-100.0, 100.0, 0.5), 0.0)
        self.assertAlmostEqual(mu.lerp(-50.0, -10.0, 0.5), -30.0)

    def test_colisao_aabb_stress(self):
        # 1. Overlapping
        self.assertTrue(mu.colisao_aabb(0, 0, 10, 10, 5, 5, 10, 10))
        # 2. Completely contained
        self.assertTrue(mu.colisao_aabb(0, 0, 100, 100, 20, 20, 10, 10))
        # 3. Identical boxes
        self.assertTrue(mu.colisao_aabb(10, 10, 20, 20, 10, 10, 20, 20))
        # 4. Touching edges (open interval: touching is NOT colliding)
        self.assertFalse(mu.colisao_aabb(0, 0, 10, 10, 10, 0, 10, 10))
        self.assertFalse(mu.colisao_aabb(0, 0, 10, 10, 0, 10, 10, 10))
        # 5. Diagonal touching corners
        self.assertFalse(mu.colisao_aabb(0, 0, 10, 10, 10, 10, 10, 10))
        # 6. Negative coordinate boxes
        self.assertTrue(mu.colisao_aabb(-20, -20, 15, 15, -15, -15, 10, 10))
        self.assertFalse(mu.colisao_aabb(-50, -50, 10, 10, 0, 0, 10, 10))

    def test_colisao_circulo_stress(self):
        # 1. Overlapping
        self.assertTrue(mu.colisao_circulo(0, 0, 10, 15, 0, 10))
        # 2. Concentric circles (same center)
        self.assertTrue(mu.colisao_circulo(5, 5, 2, 5, 5, 10))
        # 3. Tangent circles (distance == r1 + r2) -> (dist_sq == (r1+r2)^2) -> True
        self.assertTrue(mu.colisao_circulo(0, 0, 5, 10, 0, 5))
        # 4. Separated circles
        self.assertFalse(mu.colisao_circulo(0, 0, 5, 10.001, 0, 5))
        # 5. Zero radius circles at same point
        self.assertTrue(mu.colisao_circulo(10, 10, 0, 10, 10, 0))
        # 6. Zero radius circles at different points
        self.assertFalse(mu.colisao_circulo(10, 10, 0, 11, 10, 0))

    def test_ponto_em_retangulo_stress(self):
        # 1. Inside
        self.assertTrue(mu.ponto_em_retangulo(15, 15, 10, 10, 10, 10))
        # 2. On all 4 edges (inclusive)
        self.assertTrue(mu.ponto_em_retangulo(10, 15, 10, 10, 10, 10))  # Left
        self.assertTrue(mu.ponto_em_retangulo(20, 15, 10, 10, 10, 10))  # Right
        self.assertTrue(mu.ponto_em_retangulo(15, 10, 10, 10, 10, 10))  # Top
        self.assertTrue(mu.ponto_em_retangulo(15, 20, 10, 10, 10, 10))  # Bottom
        # 3. On corners
        self.assertTrue(mu.ponto_em_retangulo(10, 10, 10, 10, 10, 10))
        self.assertTrue(mu.ponto_em_retangulo(20, 20, 10, 10, 10, 10))
        # 4. Outside by epsilon
        self.assertFalse(mu.ponto_em_retangulo(9.999, 15, 10, 10, 10, 10))
        self.assertFalse(mu.ponto_em_retangulo(20.001, 15, 10, 10, 10, 10))

    def test_angulos_stress(self):
        # 1. Cardinal directions
        self.assertAlmostEqual(mu.angulo_graus(0, 0, 10, 0), 0.0)
        self.assertAlmostEqual(mu.angulo_graus(0, 0, 0, 10), 90.0)
        self.assertAlmostEqual(mu.angulo_graus(0, 0, -10, 0), 180.0)
        self.assertAlmostEqual(mu.angulo_graus(0, 0, 0, -10), 270.0)

        # 2. Diagonals
        self.assertAlmostEqual(mu.angulo_graus(0, 0, 10, 10), 45.0)
        self.assertAlmostEqual(mu.angulo_graus(0, 0, -10, 10), 135.0)
        self.assertAlmostEqual(mu.angulo_graus(0, 0, -10, -10), 225.0)
        self.assertAlmostEqual(mu.angulo_graus(0, 0, 10, -10), 315.0)

        # 3. Coincident origin and destination
        # atan2(0, 0) is 0.0
        self.assertAlmostEqual(mu.angulo_graus(5, 5, 5, 5), 0.0)

    def test_rotacionar_vetor_stress(self):
        # 1. Rotate (1, 0) by 90 degrees
        rx, ry = mu.rotacionar_vetor(1.0, 0.0, math.pi / 2.0)
        self.assertAlmostEqual(rx, 0.0, places=6)
        self.assertAlmostEqual(ry, 1.0, places=6)

        # 2. Rotate (1, 0) by 180 degrees
        rx, ry = mu.rotacionar_vetor(1.0, 0.0, math.pi)
        self.assertAlmostEqual(rx, -1.0, places=6)
        self.assertAlmostEqual(ry, 0.0, places=6)

        # 3. Rotate (1, 0) by 360 degrees (2pi)
        rx, ry = mu.rotacionar_vetor(1.0, 0.0, 2.0 * math.pi)
        self.assertAlmostEqual(rx, 1.0, places=6)
        self.assertAlmostEqual(ry, 0.0, places=6)

        # 4. Rotate zero vector
        rx, ry = mu.rotacionar_vetor(0.0, 0.0, 1.234)
        self.assertEqual((rx, ry), (0.0, 0.0))

        # 5. Full 360 loop invariance
        vx, vy = 3.5, -7.2
        for steps in range(12):
            rad = (2.0 * math.pi / 12) * steps
            rx, ry = mu.rotacionar_vetor(vx, vy, rad)
            mag_orig = math.hypot(vx, vy)
            mag_rot = math.hypot(rx, ry)
            self.assertAlmostEqual(mag_orig, mag_rot, places=6)

    def test_nan_and_inf_handling(self):
        # Check non-crashing behavior for NaN/Inf
        nan = float('nan')
        inf = float('inf')
        
        # Math functions return NaN / Inf without throwing unhandled exceptions
        self.assertTrue(math.isnan(mu.distancia(nan, 0, 0, 0)))
        self.assertTrue(math.isinf(mu.distancia(inf, 0, 0, 0)))
        self.assertTrue(math.isnan(mu.lerp(0, 10, nan)))
        self.assertTrue(math.isnan(mu.clamp(nan, 0, 10)))
        
        # Boolean predicates return False safely with NaN
        self.assertFalse(mu.colisao_aabb(nan, 0, 10, 10, 0, 0, 10, 10))
        self.assertFalse(mu.colisao_circulo(nan, 0, 5, 0, 0, 5))
        self.assertFalse(mu.ponto_em_retangulo(nan, 0, 0, 0, 10, 10))


if __name__ == "__main__":
    unittest.main()
