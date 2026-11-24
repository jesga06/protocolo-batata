"""
Testes da curva de spawn, tetos táticos, escalada pós-90s e Mini-Bosses rotativos (Onda 1 - W1).
"""

import os
import unittest
from unittest.mock import patch

import pygame

from src.entidades.inimigo_blindado import InimigoBlindado
from src.entidades.inimigo_impressora import InimigoImpressoraTermica
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.inimigo_ranged import InimigoRanged
from src.entidades.inimigo_rapido import InimigoRapido
from src.entidades.inimigo_tank import InimigoTank
from src.sistemas.sistema_spawn import SistemaSpawn
from src.utils.constantes import SPAWN_INTERVALO_INICIAL


class TestExperimentoGameloopSpawn(unittest.TestCase):
    """Valida a curva v2.0 de spawn, tetos táticos, fases musicais e rotação de Mini-Bosses."""

    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()

    def test_intervalo_spawn_sem_aceleracao_legada_067x(self):
        spawner = SistemaSpawn()
        self.assertAlmostEqual(spawner.intervalo_spawn(0.0), float(SPAWN_INTERVALO_INICIAL), places=4)
        self.assertGreaterEqual(spawner.intervalo_spawn(10.0), spawner.intervalo_spawn(30.0))

    def test_calcular_escala_hp_tempo_pos_90s(self):
        spawner = SistemaSpawn()
        self.assertEqual(spawner.calcular_escala_hp_tempo(0.0), 1.0)
        self.assertEqual(spawner.calcular_escala_hp_tempo(45.0), 1.0)
        self.assertEqual(spawner.calcular_escala_hp_tempo(90.0), 1.0)

        s120 = spawner.calcular_escala_hp_tempo(120.0)
        s180 = spawner.calcular_escala_hp_tempo(180.0)
        s270 = spawner.calcular_escala_hp_tempo(270.0)
        s600 = spawner.calcular_escala_hp_tempo(600.0)

        self.assertAlmostEqual(s120, 1.18, places=4)
        self.assertAlmostEqual(s180, 1.54, places=4)
        self.assertAlmostEqual(s270, 2.38, places=4)
        self.assertEqual(s600, 2.5)
        self.assertLess(s120, s180)
        self.assertLess(s180, s270)

    def test_inimigo_ranged_tiro_unico_antes_75s_e_rajada_apos_75s(self):
        spawner = SistemaSpawn()
        spawner.tempo_decorrido = 30.0
        spawner.timer_spawn = 10.0
        with patch.object(spawner, "escolher_arquetipo", return_value=InimigoRanged):
            novos_early = spawner.update(
                dt=0.1,
                camera_x=0.0,
                camera_y=0.0,
                total_inimigos_vivos=0,
                fase_onda="assault",
            )
        ranged_early = [e for e in novos_early if isinstance(e, InimigoRanged)]
        self.assertGreaterEqual(len(ranged_early), 1)
        self.assertTrue(all(not e.rajada_tripla for e in ranged_early))

        # Antes de 75s com forcar_rajada_tripla=True -> ativa rajada tripla
        spawner2 = SistemaSpawn()
        spawner2.tempo_decorrido = 30.0
        spawner2.timer_spawn = 10.0
        with patch.object(spawner2, "escolher_arquetipo", return_value=InimigoRanged):
            novos_forcado = spawner2.update(
                dt=0.1,
                camera_x=0.0,
                camera_y=0.0,
                total_inimigos_vivos=0,
                fase_onda="assault",
                forcar_rajada_tripla=True,
            )
        ranged_forcado = [e for e in novos_forcado if isinstance(e, InimigoRanged)]
        self.assertGreaterEqual(len(ranged_forcado), 1)
        self.assertTrue(all(e.rajada_tripla for e in ranged_forcado))

        # >= 75s -> rajada tripla natural
        spawner3 = SistemaSpawn()
        spawner3.tempo_decorrido = 80.0
        spawner3.timer_spawn = 10.0
        with patch.object(spawner3, "escolher_arquetipo", return_value=InimigoRanged):
            novos_late = spawner3.update(
                dt=0.1,
                camera_x=0.0,
                camera_y=0.0,
                total_inimigos_vivos=0,
                fase_onda="assault",
            )
        ranged_late = [e for e in novos_late if isinstance(e, InimigoRanged)]
        self.assertGreaterEqual(len(ranged_late), 1)
        self.assertTrue(all(e.rajada_tripla for e in ranged_late))

    def test_tetos_taticos_bloqueiam_excesso_e_fazem_fallback_para_manteiga(self):
        caminhos = [
            (InimigoRanged, {"ranged": 4, "impressora": 0, "tank": 0, "ninja": 2}),
            (InimigoImpressoraTermica, {"ranged": 0, "impressora": 2, "tank": 0, "ninja": 2}),
            (InimigoTank, {"ranged": 0, "impressora": 0, "tank": 3, "ninja": 2}),
        ]
        for cls_esp, contagens in caminhos:
            spawner = SistemaSpawn()
            spawner.tempo_decorrido = 90.0
            spawner.timer_spawn = 10.0
            with patch.object(spawner, "escolher_arquetipo", return_value=cls_esp):
                novos = spawner.update(
                    dt=0.1,
                    camera_x=0.0,
                    camera_y=0.0,
                    total_inimigos_vivos=10,
                    fase_onda="assault",
                    contagens_taticas=contagens,
                )
            self.assertGreater(len(novos), 0)
            self.assertFalse(any(isinstance(e, cls_esp) for e in novos))
            self.assertTrue(all(isinstance(e, (InimigoPadrao, InimigoRapido)) for e in novos))

    def test_rotacao_3_minibosses_e_hp_cheio_progressivo_sem_nerf_040x(self):
        spawner = SistemaSpawn()
        self.assertEqual(len(spawner.fila_minibosses_run), 3)
        ids = [item[2] for item in spawner.fila_minibosses_run]
        self.assertEqual(len(set(ids)), 3)
        todos_ids = {item[2] for item in SistemaSpawn.ARQUETIPOS_MINIBOSS_4}
        self.assertTrue(set(ids).issubset(todos_ids))

        # Fila determinística para verificar escalas exatas 1.00x, 1.25x, 1.50x
        fila_fixa = [
            (InimigoRapido, "MINI-BOSS: IMPRESSORA MATRICIAL", "impressora_matricial"),
            (InimigoTank, "MINI-BOSS: FONTE GENÉRICA 500W", "fonte_generica"),
            (InimigoBlindado, "MINI-BOSS: NO-BREAK CHUMBADO", "nobreak_chumbado"),
        ]
        sp = SistemaSpawn(fila_minibosses=fila_fixa)
        hp_base_1 = fila_fixa[0][0](0, 0, is_elite=True).hp_max
        hp_base_2 = fila_fixa[1][0](0, 0, is_elite=True).hp_max
        hp_base_3 = fila_fixa[2][0](0, 0, is_elite=True).hp_max

        # Ciclo 1 -> 1.00x (sem 0.40x!)
        novos1 = sp.update(0.016, 0.0, 0.0, 0, fase_onda="assault", gatilho_assault_intro=True, possui_elite_vivo=False)
        elites1 = [e for e in novos1 if getattr(e, "is_elite", False)]
        self.assertEqual(len(elites1), 1)
        self.assertEqual(elites1[0].hp_max, hp_base_1)
        self.assertEqual(elites1[0].arquetipo_miniboss, "impressora_matricial")

        # Ciclo 2 -> 1.25x
        novos2 = sp.update(0.016, 0.0, 0.0, 0, fase_onda="assault", gatilho_assault_intro=True, possui_elite_vivo=False)
        elites2 = [e for e in novos2 if getattr(e, "is_elite", False)]
        self.assertEqual(len(elites2), 1)
        self.assertEqual(elites2[0].hp_max, int(round(hp_base_2 * 1.25)))
        self.assertEqual(elites2[0].arquetipo_miniboss, "fonte_generica")

        # Ciclo 3 -> 1.50x
        novos3 = sp.update(0.016, 0.0, 0.0, 0, fase_onda="assault", gatilho_assault_intro=True, possui_elite_vivo=False)
        elites3 = [e for e in novos3 if getattr(e, "is_elite", False)]
        self.assertEqual(len(elites3), 1)
        self.assertEqual(elites3[0].hp_max, int(round(hp_base_3 * 1.50)))
        self.assertEqual(elites3[0].arquetipo_miniboss, "nobreak_chumbado")

    def test_modo_calm_nao_spawna_miniboss_nem_rush_e_gatilho_respeita_elite_vivo(self):
        spawner = SistemaSpawn()
        # Avança 120s em modo calm -> zero elites e zero rush waves
        elites_calm = []
        for _ in range(120):
            novos = spawner.update(1.0, 0.0, 0.0, total_inimigos_vivos=0, fase_onda="calm")
            elites_calm.extend([e for e in novos if getattr(e, "is_elite", False)])
        self.assertEqual(len(elites_calm), 0)
        self.assertEqual(len(spawner.bosses_spawnados_indices), 0)

        # gatilho_assault_intro=True com possui_elite_vivo=True dispara Rush Wave, mas NÃO spawna outro Mini-Boss
        novos_bloqueado = spawner.update(
            0.016,
            0.0,
            0.0,
            total_inimigos_vivos=0,
            fase_onda="assault",
            gatilho_assault_intro=True,
            possui_elite_vivo=True,
        )
        self.assertGreaterEqual(len(novos_bloqueado), 6)
        self.assertEqual(len([e for e in novos_bloqueado if getattr(e, "is_elite", False)]), 0)
        self.assertEqual(len(spawner.bosses_spawnados_indices), 0)


if __name__ == "__main__":
    unittest.main()
