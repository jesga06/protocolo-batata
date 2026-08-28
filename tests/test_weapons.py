"""
Testes Unitários de Armas e Projéteis — Protocolo: Batata
Valida cooldowns, disparo de projéteis, física de voo, tempo de vida,
e ataque corpo-a-corpo com repulsão (knockback) nos alvos mais próximos.
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

from src.armas.pistola import Pistola
from src.armas.melee import Melee
from src.entidades.projetil import Projetil
from src.entidades.inimigo_padrao import InimigoPadrao


class TestPistolaEProjetil(unittest.TestCase):
    """Testa a Pistola e a entidade de Projétil."""

    def test_pistola_disparo_e_cooldown(self):
        pistola = Pistola(dano=12, cooldown=0.33, velocidade_projetil=400.0)
        self.assertTrue(pistola.pode_atirar())

        # Disparo em direção ao ponto (500, 300) a partir de (100, 300) -> vetor horizontal (1, 0)
        tiros = pistola.disparar(origem_x=100.0, origem_y=300.0, destino_x=500.0, destino_y=300.0)
        self.assertEqual(len(tiros), 1)

        proj = tiros[0]
        self.assertEqual(proj.x, 100.0)
        self.assertEqual(proj.y, 300.0)
        self.assertAlmostEqual(proj.dir_x, 1.0)
        self.assertAlmostEqual(proj.dir_y, 0.0)
        self.assertEqual(proj.dano, 12)
        self.assertTrue(proj.ativo)

        # Tentativa imediata de disparo deve ser bloqueada pelo cooldown
        self.assertFalse(pistola.pode_atirar())
        tiros_bloqueados = pistola.disparar(100.0, 300.0, 500.0, 300.0)
        self.assertEqual(len(tiros_bloqueados), 0)

        # Atualiza a arma com tempo suficiente para encerrar o cooldown
        pistola.update(0.33)
        self.assertTrue(pistola.pode_atirar())

    def test_projetil_fisica_e_expiracao(self):
        proj = Projetil(
            x=100.0, y=100.0,
            dir_x=0.0, dir_y=1.0,  # Direção para baixo
            velocidade=200.0,
            dano=15,
            tempo_vida=1.0
        )
        self.assertTrue(proj.ativo)

        # Avança 0.5s -> 100px
        proj.update(0.5)
        self.assertEqual(proj.x, 100.0)
        self.assertAlmostEqual(proj.y, 200.0)
        self.assertAlmostEqual(proj.tempo_vida_restante, 0.5)
        self.assertTrue(proj.ativo)

        # Avança mais 0.6s -> tempo de vida total excedido
        proj.update(0.6)
        self.assertLess(proj.tempo_vida_restante, 0.0)
        self.assertFalse(proj.ativo)


class TestMeleeAttack(unittest.TestCase):
    """Testa a arma Melee (Chave de Manutenção) e seu efeito de knockback."""

    def test_melee_atinge_inimigos_no_raio_e_aplica_knockback(self):
        melee = Melee(dano=20, cooldown=0.6, alcance=70.0, knockback_forca=150.0, max_alvos_knockback=2)

        # Cria 3 inimigos a distâncias diferentes da origem (100, 100):
        # Inimigo 1: 30px à direita (dentro do alcance, mais próximo)
        e1 = InimigoPadrao(x=130 - 14, y=100 - 14)
        # Inimigo 2: 50px à esquerda (dentro do alcance, segundo mais próximo)
        e2 = InimigoPadrao(x=50 - 14, y=100 - 14)
        # Inimigo 3: 120px de distância (fora do alcance de 70px)
        e3 = InimigoPadrao(x=220 - 14, y=100 - 14)

        hp_inicial_e1 = e1.hp
        hp_inicial_e2 = e2.hp
        hp_inicial_e3 = e3.hp

        afetados = melee.executar_ataque(origem_x=100.0, origem_y=100.0, lista_inimigos=[e1, e2, e3])

        self.assertEqual(len(afetados), 2)
        self.assertIn(e1, afetados)
        self.assertIn(e2, afetados)
        self.assertNotIn(e3, afetados)

        # e1 e e2 sofreram 20 de dano
        self.assertEqual(e1.hp, hp_inicial_e1 - 20)
        self.assertEqual(e2.hp, hp_inicial_e2 - 20)
        self.assertEqual(e3.hp, hp_inicial_e3)

        # e1 e e2 receberam knockback (max_alvos_knockback = 2)
        # e1 foi empurrado para a direita (vx_knockback > 0)
        self.assertGreater(e1.vx_knockback, 0.0)
        # e2 foi empurrado para a esquerda (vx_knockback < 0)
        self.assertLess(e2.vx_knockback, 0.0)
        # e3 não sofreu knockback
        self.assertEqual(e3.vx_knockback, 0.0)

        # Melee entra em cooldown
        self.assertFalse(melee.pode_atirar())
        repeticao = melee.executar_ataque(100.0, 100.0, [e1])
        self.assertEqual(len(repeticao), 0)


if __name__ == "__main__":
    unittest.main()
