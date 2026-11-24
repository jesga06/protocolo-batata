import os
import unittest

import pygame

from src.armas.lanca_chamas import LancaChamas
from src.armas.shotgun import Shotgun
from src.armas.smg_compacta import SMGCompacta
from src.entidades.inimigo_rapido import InimigoRapido
from src.entidades.projetil import Projetil
from src.equipamentos.drone_combate import DroneCombate
from src.sistemas.efeitos_combate import (
    ContextoCombate,
    EfeitoDashRastro,
    obter_bandas_vsync_y,
)
from src.sistemas.sistema_particulas import SistemaParticulas
from src.sistemas.sistema_spawn import SistemaSpawn


class _AlvoKnockbackStub:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.largura = 28
        self.altura = 28
        self.vivo = True
        self.knockbacks: list[tuple[float, float, float]] = []
        self.danos: list[int] = []

    def receber_dano(self, dano: int, **kwargs):
        self.danos.append(int(dano))

    def aplicar_knockback(self, dx: float, dy: float, forca: float = 0.0):
        self.knockbacks.append((float(dx), float(dy), float(forca)))


class TestPlaytest2Balance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()

    def test_smg_compacta_aquece_segurando_gatilho_e_resfria_ao_soltar(self):
        smg = SMGCompacta()
        self.assertGreater(smg.atraso_resfriamento, smg.cooldown)
        self.assertEqual(smg.calor_por_tiro, 2.0)
        self.assertEqual(smg.resfriamento_por_seg, 50.0)

        # Simula 30 disparos contínuos (~3.3s segurando o gatilho)
        for _ in range(30):
            self.assertTrue(smg.pode_atirar())
            smg.disparar(0.0, 0.0, 100.0, 0.0)
            # Avança exatamente o tempo de recarga entre tiros
            smg.update(smg.tempo_recarga_restante)

        self.assertFalse(smg.superaquecida)
        self.assertTrue(smg.em_zona_ideal)
        self.assertGreaterEqual(smg.calor_atual, 60.0)
        self.assertLessEqual(smg.calor_atual, 92.0)

        # Soltar o gatilho por 0.35s (> atraso_resfriamento=0.24s) reduz o calor
        calor_antes = smg.calor_atual
        smg.update(0.35)
        self.assertLess(smg.calor_atual, calor_antes)

    def test_lanca_chamas_dps_balanceado(self):
        lc = LancaChamas()
        self.assertEqual(lc.dano, 5)
        self.assertAlmostEqual(lc.intervalo_tick, 0.14, places=5)
        dps = lc.dano / lc.intervalo_tick
        self.assertGreater(dps, 30.0)
        self.assertLess(dps, 40.0)

    def test_knockback_tiros_reduzido_75_por_cento(self):
        # 1. Projetil explosivo: direto 87.5, radial 70.0
        alvo_direto = _AlvoKnockbackStub(100.0, 100.0)
        alvo_radial = _AlvoKnockbackStub(140.0, 100.0)
        proj = Projetil(
            x=100.0,
            y=100.0,
            dir_x=1.0,
            dir_y=0.0,
            velocidade=300.0,
            dano=20,
            tempo_vida=1.0,
            explosivo=True,
            raio_explosao=120.0,
        )
        proj.explodir([alvo_direto, alvo_radial], alvo_direto=alvo_direto)
        self.assertEqual(len(alvo_direto.knockbacks), 1)
        self.assertAlmostEqual(alvo_direto.knockbacks[0][2], 87.5, places=3)
        self.assertEqual(len(alvo_radial.knockbacks), 1)
        self.assertAlmostEqual(alvo_radial.knockbacks[0][2], 70.0, places=3)

        # 2. Shotgun pellets: 10.5
        sg = Shotgun()
        pellets = sg.disparar(0.0, 0.0, 100.0, 0.0)
        self.assertGreater(len(pellets), 0)
        self.assertTrue(all(abs(p.knockback_forca - 10.5) < 1e-4 for p in pellets))

        # 3. Drone de combate: 9.0
        drone = DroneCombate(0.0, 0.0)
        alvo_drone = _AlvoKnockbackStub(120.0, 0.0)
        tiros_drone = drone.disparar_no_alvo(alvo_drone)
        self.assertGreater(len(tiros_drone), 0)
        self.assertTrue(all(abs(p.knockback_forca - 9.0) < 1e-4 for p in tiros_drone))

    def test_particulas_parry_toast_condicional_e_jato_chamas(self):
        sp = SistemaParticulas()

        # Golpe RMB vazio (mostrar_texto=False) não deve emitir texto "PARRY!"
        sp.adicionar_arco_parry(50.0, 50.0, 0.0, mostrar_texto=False, cor=(120, 220, 255))
        self.assertEqual(len(sp.arcos_parry), 1)
        self.assertEqual(sp.arcos_parry[0].cor, (120, 220, 255))
        self.assertFalse(any(t.texto == "PARRY!" for t in sp.textos_dano))

        # Parry real (mostrar_texto=True) emite texto "PARRY!"
        sp.adicionar_arco_parry(50.0, 50.0, 0.0, mostrar_texto=True)
        self.assertTrue(any(t.texto == "PARRY!" for t in sp.textos_dano))

        # Jato de chamas cria partículas leves
        qtd_antes = len(sp.particulas)
        sp.emitir_jato_chamas(100.0, 100.0, 0.0, alcance=195.0, arco_graus=55.0)
        self.assertGreater(len(sp.particulas), qtd_antes)

    def test_spawn_burst_inicial_densidade_e_piso_hp_miniboss(self):
        fila = [
            (InimigoRapido, "MINI-BOSS: IMPRESSORA MATRICIAL", "impressora_matricial"),
            (InimigoRapido, "MINI-BOSS: IMPRESSORA MATRICIAL", "impressora_matricial"),
            (InimigoRapido, "MINI-BOSS: IMPRESSORA MATRICIAL", "impressora_matricial"),
        ]
        spawner = SistemaSpawn(fila_minibosses=fila)
        self.assertAlmostEqual(spawner.intervalo_spawn(0.0), 1.55, places=4)
        self.assertEqual(spawner.tamanho_lote(0.0), 3)
        self.assertEqual(spawner.tamanho_lote(180.0), 6)

        # Primeiro update gera burst inicial de 6 inimigos fodder
        novos = spawner.update(0.016, 0.0, 0.0, total_inimigos_vivos=0)
        self.assertEqual(len(novos), 6)

        # Segundo update imediato não repete burst inicial
        novos2 = spawner.update(0.016, 0.0, 0.0, total_inimigos_vivos=6)
        self.assertEqual(len(novos2), 0)

        # Mini-Boss Impressora Matricial respeita piso de 700 HP (700 / 875 / 1050)
        e1 = [
            e for e in spawner.update(0.016, 0.0, 0.0, 6, fase_onda="assault", gatilho_assault_intro=True)
            if getattr(e, "is_elite", False)
        ]
        self.assertEqual(e1[0].hp_max, 700)
        e2 = [
            e for e in spawner.update(0.016, 0.0, 0.0, 6, fase_onda="assault", gatilho_assault_intro=True)
            if getattr(e, "is_elite", False)
        ]
        self.assertEqual(e2[0].hp_max, 875)
        e3 = [
            e for e in spawner.update(0.016, 0.0, 0.0, 6, fase_onda="assault", gatilho_assault_intro=True)
            if getattr(e, "is_elite", False)
        ]
        self.assertEqual(e3[0].hp_max, 1050)

    def test_vacuo_io_e_bandas_vsync(self):
        efeito = EfeitoDashRastro("vacuo_io")
        ctx = ContextoCombate(cena=None, jogador=None, inimigos=[], projeteis=[], drops=[])
        efeito.ao_dash(ctx, (0.0, 0.0), (120.0, 80.0))
        self.assertEqual(len(efeito.vortices), 1)
        self.assertAlmostEqual(efeito.vortices[0]["raio"], 95.0, places=3)
        self.assertAlmostEqual(efeito.vortices[0]["tempo"], 2.5, places=3)

        y1, y2 = obter_bandas_vsync_y(100.0, 720.0)
        self.assertAlmostEqual(y1, 100.0, places=3)
        self.assertAlmostEqual(y2, 460.0, places=3)

        y3, y4 = obter_bandas_vsync_y(800.0, 720.0)
        self.assertAlmostEqual(y3, 80.0, places=3)
        self.assertAlmostEqual(y4, 440.0, places=3)


if __name__ == "__main__":
    unittest.main()
