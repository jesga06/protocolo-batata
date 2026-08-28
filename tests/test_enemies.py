"""
Testes Unitários dos Inimigos e Spawner — Protocolo: Batata
Valida estatísticas base, cálculo vetorial da IA beeline, dano de contato com
cooldown individual por instância, destruição e o escalonamento do Spawner.
"""

import os
import sys
import math
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.entidades.inimigo_base import InimigoBase
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.jogador import Jogador
from src.sistemas.sistema_spawn import SistemaSpawn
from src.utils.constantes import (
    INIMIGO_PADRAO_HP, INIMIGO_PADRAO_VELOCIDADE,
    INIMIGO_PADRAO_DANO, INIMIGO_PADRAO_COOLDOWN_ATAQUE,
    LARGURA_ARENA, ALTURA_ARENA
)


class TestInimigoPadraoIAEColisao(unittest.TestCase):
    """Testa IA beeline e mecânicas de combate do Inimigo Padrão."""

    def test_estatisticas_iniciais_inimigo_padrao(self):
        e = InimigoPadrao(x=100.0, y=100.0)
        self.assertEqual(e.hp, INIMIGO_PADRAO_HP)
        self.assertEqual(e.hp_max, INIMIGO_PADRAO_HP)
        self.assertEqual(e.velocidade, 100.0)
        self.assertEqual(e.dano_contato, 10)
        self.assertEqual(e.cooldown_contato_max, 0.4)
        self.assertEqual(e.cooldown_contato_atual, 0.0)
        self.assertEqual(e.xp_valor, 5)
        self.assertTrue(e.vivo)

    def test_ia_beeline_direcao_correta(self):
        # Inimigo em (0, 0), Jogador em (100, 0) -> deve andar diretamente para a direita
        e = InimigoPadrao(x=0.0, y=0.0)
        # Centro do inimigo: (14, 14), alvo em (114, 14) -> vetor exato (1.0, 0.0)
        e.update(dt=0.5, pos_alvo=(114.0, 14.0))

        # Em 0.5s a 100px/s, avança 50px no eixo X
        self.assertAlmostEqual(e.x, 50.0)
        self.assertAlmostEqual(e.y, 0.0)

    def test_ia_beeline_diagonal_e_singularidade(self):
        e = InimigoPadrao(x=0.0, y=0.0)
        # Alvo na mesma posição exata (distância zero) não deve gerar NaN ou divisão por zero
        e.update(dt=0.1, pos_alvo=(14.0, 14.0))
        self.assertFalse(math.isnan(e.x))
        self.assertFalse(math.isnan(e.y))

    def test_cooldown_contato_individual_por_instancia(self):
        """Verifica que o cooldown de contato é individual e não global."""
        j = Jogador(x=100.0, y=100.0)
        self.assertEqual(j.hp, 150)

        e1 = InimigoPadrao(x=100.0, y=100.0)
        e2 = InimigoPadrao(x=100.0, y=100.0)

        # 1. Primeiro contato de e1 aplica 10 de dano
        atingiu_e1 = e1.tentar_causar_dano_contato(j)
        self.assertTrue(atingiu_e1)
        self.assertEqual(j.hp, 140)
        self.assertAlmostEqual(e1.cooldown_contato_atual, 0.4)

        # 2. Segundo contato imediato de e1 no mesmo frame é bloqueado pelo cooldown
        atingiu_e1_novamente = e1.tentar_causar_dano_contato(j)
        self.assertFalse(atingiu_e1_novamente)
        self.assertEqual(j.hp, 140)

        # 3. Inimigo e2 possui seu próprio cooldown independente zerado e aplica dano
        self.assertEqual(e2.cooldown_contato_atual, 0.0)
        atingiu_e2 = e2.tentar_causar_dano_contato(j)
        self.assertTrue(atingiu_e2)
        self.assertEqual(j.hp, 130)

        # 4. Avança 0.2s: cooldown de e1 e e2 ainda ativos
        e1.update(dt=0.2, pos_alvo=(100, 100))
        e2.update(dt=0.2, pos_alvo=(100, 100))
        self.assertFalse(e1.tentar_causar_dano_contato(j))
        self.assertEqual(j.hp, 130)

        # 5. Avança mais 0.25s (total 0.45s): cooldowns expiraram e dano volta a ser aplicado
        e1.update(dt=0.25, pos_alvo=(100, 100))
        self.assertEqual(e1.cooldown_contato_atual, 0.0)
        self.assertTrue(e1.tentar_causar_dano_contato(j))
        self.assertEqual(j.hp, 120)

    def test_dano_e_morte_do_inimigo(self):
        e = InimigoPadrao(x=100.0, y=100.0)
        self.assertEqual(e.hp, 40)
        e.receber_dano(20)
        self.assertEqual(e.hp, 20)
        self.assertTrue(e.vivo)
        e.receber_dano(20)
        self.assertEqual(e.hp, 0)
        self.assertFalse(e.vivo)

    def test_dano_com_knockback_vetorial(self):
        e = InimigoPadrao(x=100.0, y=100.0)
        e.receber_dano(10, knockback_vetor=(100.0, 0.0))
        self.assertAlmostEqual(e.x, 100.0)  # Posição imediata não muda bruscamente sem update


class TestSistemaSpawn(unittest.TestCase):
    def test_escalonamento_intervalo_e_lote(self):
        spawner = SistemaSpawn()
        # t = 0s
        self.assertAlmostEqual(spawner.intervalo_spawn(0.0), 2.0)
        self.assertEqual(spawner.tamanho_lote(0.0), 1)

        # t = 50s -> 2.0 - 0.012 * 50 = 1.40s, lote = min(8, 1 + 2) = 3
        self.assertAlmostEqual(spawner.intervalo_spawn(50.0), 1.40)
        self.assertEqual(spawner.tamanho_lote(50.0), 3)

        # t = 100s -> 2.0 - 0.012 * 100 = 0.80s, lote = min(8, 1 + 4) = 5
        self.assertAlmostEqual(spawner.intervalo_spawn(100.0), 0.80)
        self.assertEqual(spawner.tamanho_lote(100.0), 5)

    def test_spawner_gera_inimigos_e_respeita_teto(self):
        spawner = SistemaSpawn(max_ativos=5)
        # Avança 2.1s para disparar o primeiro pulso
        gerados = spawner.update(
            dt=2.1,
            camera_x=0.0,
            camera_y=0.0,
            total_inimigos_vivos=0
        )
        self.assertGreaterEqual(len(gerados), 1)
        for inim in gerados:
            self.assertIsInstance(inim, InimigoBase)
            # Verifica que foram gerados dentro dos limites da arena
            self.assertGreaterEqual(inim.x, 0.0)
            self.assertLessEqual(inim.x, LARGURA_ARENA - inim.largura)
            self.assertGreaterEqual(inim.y, 0.0)
            self.assertLessEqual(inim.y, ALTURA_ARENA - inim.altura)

        # Se total_vivos >= max_ativos, spawner não deve gerar ninguém
        gerados_bloqueados = spawner.update(
            dt=5.0,
            camera_x=0.0,
            camera_y=0.0,
            total_inimigos_vivos=5
        )
        self.assertEqual(len(gerados_bloqueados), 0)

    def test_spawner_posicoes_fora_da_camera(self):
        """Verifica que todas as posições geradas pelo spawner estão fora do viewport visível."""
        spawner = SistemaSpawn()
        cam_x, cam_y = 200.0, 150.0
        view_w, view_h = 800.0, 600.0
        margem = 60.0

        for _ in range(50):
            sx, sy = spawner.gerar_posicao_spawn(
                camera_x=cam_x, camera_y=cam_y,
                view_w=view_w, view_h=view_h,
                margem=margem
            )
            # A coordenada deve estar fora da caixa [cam_x, cam_x + view_w] x [cam_y, cam_y + view_h]
            fora_horizontal = (sx < cam_x) or (sx > cam_x + view_w)
            fora_vertical = (sy < cam_y) or (sy > cam_y + view_h)
            self.assertTrue(
                fora_horizontal or fora_vertical,
                f"Coordenada ({sx}, {sy}) foi gerada DENTRO da visão da câmera!"
            )

    def test_inimigo_knockback_e_decaimento(self):
        """Verifica que o knockback é aplicado e decai com o tempo."""
        e = InimigoPadrao(x=100.0, y=100.0)
        e.aplicar_knockback(dir_x=1.0, dir_y=0.0, forca=200.0)
        self.assertEqual(e.vx_knockback, 200.0)

        # Avança 0.5s -> knockback deve decair suavemente em direção a 0
        e.update(dt=0.5, pos_alvo=(100, 100))
        self.assertLess(e.vx_knockback, 50.0)
        self.assertGreaterEqual(e.vx_knockback, 0.0)

    def test_spawner_tempo_extremo(self):
        """Verifica que tempo extremo (ex: 30 minutos) não estoura limites."""
        spawner = SistemaSpawn(max_ativos=60)
        self.assertEqual(spawner.intervalo_spawn(1800.0), 0.50)
        self.assertEqual(spawner.tamanho_lote(1800.0), 8)


if __name__ == "__main__":
    unittest.main()
