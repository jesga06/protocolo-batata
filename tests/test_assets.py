"""
Testes Unitários de Assets, Constantes, Matemática e Inicialização de Cenas
Executável de forma headless sem requerer display gráfico ou dispositivo de áudio.
"""

import os
import sys
import math
import wave
import unittest
from PIL import Image

# Configuração de Ambiente Headless para SDL / Pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.constantes import (
    ASSETS_DIR, ASSET_PATHS, CONFIGURACOES_CATALOGO, CONFIGURACOES_SISTEMA,
    LARGURA_TELA, ALTURA_TELA, JOGADOR_HP_MAX_PADRAO, JOGADOR_VELOCIDADE_PADRAO,
    obter_caminho_asset
)
from src.utils.math_utils import (
    distancia, distancia_sq, normalizar_vetor, vetor_direcao,
    clamp, lerp, colisao_aabb, colisao_circulo, ponto_em_retangulo,
    angulo_radianos, angulo_graus, rotacionar_vetor
)


class TestAssetsExistenciaEDimensoes(unittest.TestCase):
    """Testa se todos os assets PNG e WAV foram gerados corretamente com dimensões válidas."""

    def test_todos_os_assets_do_catalogo_existem(self):
        for chave, caminho_rel in ASSET_PATHS.items():
            caminho_abs = os.path.join(ASSETS_DIR, caminho_rel)
            self.assertTrue(
                os.path.isfile(caminho_abs),
                f"Asset registrado '{chave}' ({caminho_rel}) não existe no disco!"
            )
            self.assertGreater(
                os.path.getsize(caminho_abs), 0,
                f"Arquivo de asset '{caminho_rel}' está vazio (0 bytes)!"
            )

    def test_dimensoes_sprites_jogador(self):
        caminhos_esperados = {
            "sprites/jogador/batata_idle.png": (42, 42),
            "sprites/jogador/batata_walk_sheet.png": (168, 42),
            "sprites/jogador/batata_dano.png": (42, 42),
        }
        for rel_path, dim_esperada in caminhos_esperados.items():
            abs_path = os.path.join(ASSETS_DIR, rel_path)
            with Image.open(abs_path) as img:
                self.assertEqual(img.size, dim_esperada, f"{rel_path} tem dimensões incorretas!")
                self.assertEqual(img.mode, "RGBA", f"{rel_path} deve ter canal alfa RGBA!")

    def test_dimensoes_sprites_inimigos(self):
        caminhos_esperados = {
            "sprites/inimigos/inimigo_padrao.png": (42, 42),
            "sprites/inimigos/inimigo_tank.png": (62, 62),
            "sprites/inimigos/inimigo_rapido.png": (31, 31),
            "sprites/inimigos/inimigo_phasing.png": (42, 42),
            "sprites/inimigos/inimigo_blindado.png": (47, 47),
            "sprites/inimigos/inimigo_ranged.png": (42, 42),
        }
        for rel_path, dim_esperada in caminhos_esperados.items():
            abs_path = os.path.join(ASSETS_DIR, rel_path)
            with Image.open(abs_path) as img:
                self.assertEqual(img.size, dim_esperada, f"{rel_path} tem dimensões incorretas!")

    def test_dimensoes_icones_configs(self):
        icones_dir = os.path.join(ASSETS_DIR, "ui", "icones_configs")
        self.assertTrue(os.path.isdir(icones_dir), "Diretório de ícones de configs não existe!")
        arquivos = [f for f in os.listdir(icones_dir) if f.endswith(".png")]
        self.assertEqual(len(arquivos), 23, "Devem existir exatamente 23 ícones de configuração (20 gameplay + 3 sistema)!")
        for arq in arquivos:
            with Image.open(os.path.join(icones_dir, arq)) as img:
                self.assertEqual(img.size, (32, 32), f"Ícone {arq} deve ser 32x32!")

    def test_arquivos_audio_wav_validos(self):
        sfx_dir = os.path.join(ASSETS_DIR, "audio", "sfx")
        arquivos_sfx = [f for f in os.listdir(sfx_dir) if f.endswith(".wav")]
        self.assertGreaterEqual(len(arquivos_sfx), 18, "Devem existir ao menos 18 arquivos de efeitos sonoros!")

        for arq in arquivos_sfx:
            caminho = os.path.join(sfx_dir, arq)
            with wave.open(caminho, "r") as wav_file:
                self.assertEqual(wav_file.getframerate(), 44100, f"{arq} deve ter taxa de amostragem de 44100Hz!")
                self.assertEqual(wav_file.getsampwidth(), 2, f"{arq} deve ser 16-bit PCM (2 bytes/amostra)!")
                self.assertGreater(wav_file.getnframes(), 0, f"{arq} não possui frames de áudio!")

        musica_path = obter_caminho_asset("musica_fase")
        self.assertTrue(os.path.isfile(musica_path), "Música da fase não encontrada!")
        with wave.open(musica_path, "r") as wav_file:
            self.assertEqual(wav_file.getframerate(), 44100)
            self.assertGreater(wav_file.getnframes() / 44100, 3.0, "Música deve ter mais de 3 segundos de duração!")


class TestConstantesEConfiguracoes(unittest.TestCase):
    """Verifica a integridade do catálogo de configurações conforme CONFIGURACOES.md."""

    def test_total_configs_gameplay(self):
        self.assertEqual(
            len(CONFIGURACOES_CATALOGO), 20,
            "Devem existir exatamente 20 configurações de gameplay no catálogo!"
        )

    def test_total_configs_sistema(self):
        self.assertEqual(
            len(CONFIGURACOES_SISTEMA), 3,
            "Devem existir exatamente 3 configurações de sistema (volume_master, volume_musica, volume_sfx)!"
        )

    def test_estrutura_cada_config_gameplay(self):
        for config_id, config_info in CONFIGURACOES_CATALOGO.items():
            self.assertEqual(config_id, config_info["id"])
            self.assertIn("nome", config_info)
            self.assertIn("categoria", config_info)
            self.assertIn("tipo", config_info)
            self.assertIn("padrao", config_info)
            self.assertIn("opcoes", config_info)
            self.assertIn("icone", config_info)
            self.assertIn("flavor_text", config_info)
            self.assertIn("buffs", config_info)

            # Verifica se o ícone referenciado existe no disco
            icone_path = os.path.join(ASSETS_DIR, config_info["icone"])
            self.assertTrue(
                os.path.isfile(icone_path),
                f"Ícone '{config_info['icone']}' da config '{config_id}' não existe no disco!"
            )


class TestMathUtils(unittest.TestCase):
    """Testa os utilitários matemáticos e funções de colisão."""

    def test_distancia_e_distancia_sq(self):
        self.assertAlmostEqual(distancia(0, 0, 3, 4), 5.0)
        self.assertAlmostEqual(distancia_sq(0, 0, 3, 4), 25.0)
        self.assertAlmostEqual(distancia(10, 10, 10, 10), 0.0)

    def test_normalizar_vetor(self):
        nx, ny = normalizar_vetor(3, 4)
        self.assertAlmostEqual(nx, 0.6)
        self.assertAlmostEqual(ny, 0.8)
        self.assertAlmostEqual(nx * nx + ny * ny, 1.0)

        # Vetor nulo (proteção contra divisão por zero)
        zx, zy = normalizar_vetor(0, 0)
        self.assertEqual((zx, zy), (0.0, 0.0))

    def test_vetor_direcao(self):
        dx, dy = vetor_direcao(0, 0, 10, 0)
        self.assertAlmostEqual(dx, 1.0)
        self.assertAlmostEqual(dy, 0.0)

        dx, dy = vetor_direcao(5, 5, 5, 15)
        self.assertAlmostEqual(dx, 0.0)
        self.assertAlmostEqual(dy, 1.0)

    def test_clamp_e_lerp(self):
        self.assertEqual(clamp(15, 0, 10), 10)
        self.assertEqual(clamp(-5, 0, 10), 0)
        self.assertEqual(clamp(7, 0, 10), 7)

        self.assertAlmostEqual(lerp(0, 100, 0.5), 50.0)
        self.assertAlmostEqual(lerp(10, 20, 0.25), 12.5)

    def test_colisao_aabb(self):
        # Caixas sobrepostas
        self.assertTrue(colisao_aabb(0, 0, 32, 32, 16, 16, 32, 32))
        # Caixas disjuntas
        self.assertFalse(colisao_aabb(0, 0, 32, 32, 50, 50, 32, 32))
        # Caixas que apenas se tocam na borda (sem sobreposição interna)
        self.assertFalse(colisao_aabb(0, 0, 32, 32, 32, 0, 32, 32))

    def test_colisao_circulo(self):
        self.assertTrue(colisao_circulo(0, 0, 10, 15, 0, 10))
        self.assertFalse(colisao_circulo(0, 0, 10, 25, 0, 10))

    def test_ponto_em_retangulo(self):
        self.assertTrue(ponto_em_retangulo(15, 15, 10, 10, 20, 20))
        self.assertFalse(ponto_em_retangulo(5, 5, 10, 10, 20, 20))

    def test_rotacionar_vetor(self):
        rx, ry = rotacionar_vetor(1.0, 0.0, math.radians(90))
        self.assertAlmostEqual(rx, 0.0, places=5)
        self.assertAlmostEqual(ry, 1.0, places=5)


class TestMainHeadlessExecution(unittest.TestCase):
    """Verifica se main.py inicializa e executa frames sem exceções no modo headless."""

    def test_main_executa_frames_sem_crash(self):
        from src.main import main
        try:
            main(limite_frames=5)
        except Exception as e:
            self.fail(f"main(limite_frames=5) falhou com exceção: {e}")


if __name__ == "__main__":
    unittest.main()
