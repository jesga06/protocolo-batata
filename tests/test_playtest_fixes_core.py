"""
Testes unitários para as correções de combate core do playtest (fix-combat-core).
"""

import os
import sys
import unittest
from types import SimpleNamespace

import pygame

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.armas.bastao_choque import BastaoChoque
from src.armas.melee import Melee
from src.armas.smg_compacta import SMGCompacta
from src.entidades.inimigo_impressora import InimigoImpressoraTermica
from src.entidades.inimigo_ninja import InimigoNinja
from src.entidades.inimigo_ranged import InimigoRanged
from src.entidades.projetil import Projetil
from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.sistemas.efeitos_combate import ContextoCombate, EfeitoDashRastro, EfeitoInerciaCinetica
from src.sistemas.sistema_musica import SistemaMusica


class _DummySound:
    def __init__(self, duracao=10.0):
        self._duracao = duracao

    def get_length(self):
        return self._duracao


class _DummyChannel:
    def __init__(self):
        self.busy = True
        self.queued = None
        self.played = []
        self.volume = 1.0

    def play(self, sound, loops=0):
        self.played.append((sound, loops))
        self.busy = True
        self.queued = None

    def queue(self, sound):
        self.queued = sound

    def get_queue(self):
        return self.queued

    def get_busy(self):
        return self.busy

    def set_volume(self, v):
        self.volume = v

    def stop(self):
        self.busy = False
        self.queued = None

    def fadeout(self, ms):
        self.busy = False
        self.queued = None


class TestPlaytestFixesCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.surface = pygame.Surface((640, 480))

    def test_projetil_homing_anti_uturn_e_desenhar(self):
        # Homing ativo gira suavemente quando alvo está no cone frontal
        p = Projetil(
            0.0, 0.0, dir_x=1.0, dir_y=0.0, velocidade=200.0,
            dono="inimigo", largura=20, altura=20,
            nao_parriavel=True, homing_ativo=True, homing_taxa_rad=1.6, homing_radar_dot=0.25,
        )
        p.update(0.1, pos_alvo=(200.0, 60.0))
        self.assertTrue(p.homing_ativo)
        self.assertGreater(p.dir_y, 0.0)
        self.assertGreaterEqual(len(p.rastro_posicoes), 1)

        # Alvo atrás do cone frontal (dot < 0.25) desativa homing permanentemente
        p.update(0.1, pos_alvo=(-100.0, 0.0))
        self.assertFalse(p.homing_ativo)
        dir_antes = (p.dir_x, p.dir_y)
        p.update(0.1, pos_alvo=(500.0, 500.0))
        self.assertFalse(p.homing_ativo)
        self.assertEqual((p.dir_x, p.dir_y), dir_antes)

        # Renderização headless dos 4 tipos visuais sem erro
        p_comum = Projetil(100.0, 100.0, dono="inimigo", largura=12, altura=12)
        p_ninja = Projetil(120.0, 100.0, dono="inimigo", largura=20, altura=20, nao_desviavel=True)
        p_imp = Projetil(140.0, 100.0, dono="inimigo", largura=28, altura=28, sobrecarga_termica=True, eh_impressora=True)
        for pr in (p_comum, p, p_ninja, p_imp):
            pr.desenhar(self.surface)

    def test_impressora_marca_eh_impressora(self):
        imp = InimigoImpressoraTermica(0.0, 0.0)
        imp.timer_tiro = imp.cooldown_tiro
        imp.update(0.05, (200.0, 0.0))
        projs = imp.obter_projeteis_pendentes()
        self.assertEqual(len(projs), 1)
        self.assertTrue(projs[0].eh_impressora)
        self.assertTrue(projs[0].sobrecarga_termica)
        self.assertGreaterEqual(projs[0].largura, 28)

    def test_ninja_duelo_windup_e_nao_desviavel(self):
        ninja = InimigoNinja(0.0, 0.0)
        self.assertEqual(ninja.vel_projetil, 380.0)

        # Duelo stage 2 não spawna no frame 0 (Goldilocks fix)
        res = ninja.disparar_contra_ataque_duelo(2, (100.0, 0.0))
        self.assertIsNone(res)
        self.assertEqual(len(ninja.obter_projeteis_pendentes()), 0)
        self.assertGreater(ninja.parry_telegraph_timer, 0.0)

        # Avança 0.10s: ainda em wind-up
        ninja.update(0.10, (100.0, 0.0))
        self.assertEqual(len(ninja.obter_projeteis_pendentes()), 0)

        # Avança mais 0.20s: emite stage 2 a ~470 px/s, 20x20, nao_desviavel=True
        ninja.update(0.20, (100.0, 0.0))
        projs = ninja.obter_projeteis_pendentes()
        self.assertEqual(len(projs), 1)
        self.assertEqual(projs[0].duel_stage, 2)
        self.assertAlmostEqual(projs[0].velocidade, 470.0, places=1)
        self.assertEqual(projs[0].largura, 20)
        self.assertTrue(projs[0].nao_desviavel)
        self.assertTrue(projs[0].homing_ativo)

    def test_ninja_shuriken_homing_progressivo_e_velocidades_preservadas(self):
        ninja = InimigoNinja(0.0, 0.0)
        ninja.timer_tiro = ninja.cooldown_tiro
        ninja.update(0.05, (200.0, 0.0))
        p1 = ninja.obter_projeteis_pendentes()[0]
        self.assertEqual(p1.duel_stage, 1)
        self.assertAlmostEqual(p1.velocidade, 380.0, places=1)
        self.assertTrue(p1.homing_ativo)
        self.assertTrue(p1.nao_desviavel)

        ninja.disparar_contra_ataque_duelo(2, (200.0, 0.0))
        ninja.update(0.30, (200.0, 0.0))
        p2 = ninja.obter_projeteis_pendentes()[0]
        self.assertEqual(p2.duel_stage, 2)
        self.assertAlmostEqual(p2.velocidade, 470.0, places=1)
        self.assertTrue(p2.homing_ativo)
        self.assertGreater(p2.homing_taxa_rad, p1.homing_taxa_rad)
        self.assertLess(p2.homing_radar_dot, p1.homing_radar_dot)

        ninja.disparar_contra_ataque_duelo(3, (200.0, 0.0))
        ninja.update(0.30, (200.0, 0.0))
        p3 = ninja.obter_projeteis_pendentes()[0]
        self.assertEqual(p3.duel_stage, 3)
        self.assertAlmostEqual(p3.velocidade, 560.0, places=1)
        self.assertTrue(p3.homing_ativo)
        self.assertGreater(p3.homing_taxa_rad, p2.homing_taxa_rad)
        self.assertLess(p3.homing_radar_dot, p2.homing_radar_dot)

    def test_ranged_lead_e_modo_homing(self):
        ranged_normal = InimigoRanged(0.0, 0.0, modo_homing=False)
        p_norm = ranged_normal.disparar((200.0, 0.0), vel_alvo=(0.0, 100.0))
        self.assertFalse(p_norm.nao_parriavel)
        self.assertFalse(p_norm.homing_ativo)
        self.assertFalse(p_norm.nao_desviavel)

        ranged_homing = InimigoRanged(0.0, 0.0, modo_homing=True)
        p_hom = ranged_homing.disparar((200.0, 0.0), vel_alvo=(0.0, 100.0))
        self.assertTrue(p_hom.nao_parriavel)
        self.assertTrue(p_hom.homing_ativo)
        self.assertFalse(p_hom.nao_desviavel)
        self.assertEqual(p_hom.largura, 20)

    def test_melee_parry_desacoplado_nao_parriavel_e_duelo(self):
        melee = Melee(alcance=109.0)
        bastao = BastaoChoque(alcance=109.0)
        self.assertEqual(melee.parry_alcance_base, 64.0)
        self.assertEqual(bastao.parry_alcance_base, 58.0)
        self.assertAlmostEqual(melee.parry_alcance, 64.0)

        # Projétil a 85px está dentro de 109px LMB, mas fora de 64px parry
        p_longe = Projetil(85.0, -4.0, dono="inimigo", largura=8, altura=8)
        melee.iniciar_golpe_parry(angulo=0.0)
        self.assertEqual(len(melee.tentar_parry_projeteis(0.0, 0.0, [p_longe], angulo_mira=0.0)), 0)

        # Projétil nao_parriavel dentro do alcance não é refletido e sinaliza bloqueio
        p_np = Projetil(40.0, -4.0, dono="inimigo", largura=20, altura=20, nao_parriavel=True)
        self.assertEqual(len(melee.tentar_parry_projeteis(0.0, 0.0, [p_np], angulo_mira=0.0)), 0)
        self.assertTrue(melee.ultimo_parry_bloqueado_nao_parriavel)
        self.assertEqual(p_np.dono, "inimigo")

        # finalizar_acerto_duelo fecha janela e seta cooldown para 0.08s
        melee.tempo_recarga_restante = 0.5
        melee.finalizar_acerto_duelo()
        self.assertEqual(melee.parry_janela_restante, 0.0)
        self.assertAlmostEqual(melee.tempo_recarga_restante, 0.08)

    def test_smg_compacta_abordagem_b_e_ventilar(self):
        smg = SMGCompacta()
        self.assertEqual(smg.calor_por_tiro, 2.0)
        self.assertEqual(smg.zona_ideal_min, 60.0)
        self.assertEqual(smg.zona_ideal_max, 92.0)
        self.assertEqual(smg.resfriamento_por_seg, 50.0)

        smg.calor_atual = 70.0
        self.assertTrue(smg.em_zona_ideal)
        smg.disparar(0.0, 0.0, 100.0, 0.0)
        self.assertAlmostEqual(smg.tempo_recarga_restante, smg.cooldown * 0.80, places=5)

        smg.ventilar_calor(25.0)
        self.assertAlmostEqual(smg.calor_atual, 47.0, places=3)

    def test_musica_recupera_apos_pause_alt_tab(self):
        from tests.test_sistema_musica import _criar_sistema_teste

        musica, clock, ch_n, _ = _criar_sistema_teste()
        musica.iniciar_partida()
        # Simula fim de anticipation com próximo já enfileirado, mas canal parado por suspensão do SO durante Pause + Alt-Tab
        musica._proximo_enfileirado = SistemaMusica.ESTADO_HOLD
        ch_n._queue = None
        ch_n._busy = False
        clock.avancar(35.6)

        musica.atualizar(tempo_sobrevivencia=35.6, abafado=True, dt=0.016, pausar_transicao=True)
        self.assertTrue(ch_n.get_busy())
        self.assertEqual(musica.estado, SistemaMusica.ESTADO_ANTICIPATION)

    def test_config_ranged_e_tutorial_visto(self):
        nerf = CONFIGURACOES_GAMEPLAY["inimigos_ranged"].opcoes["ligado"].nerf_text.lower()
        self.assertIn("teleguiad", nerf)
        self.assertIn("parri", nerf)

        cfg = GerenciadorConfiguracoes()
        self.assertFalse(cfg.tutorial_visto)
        cfg.marcar_tutorial_visto()
        self.assertTrue(cfg.tutorial_visto)
        dados = cfg.to_dict()
        self.assertTrue(dados["tutorial_visto"])

        cfg2 = GerenciadorConfiguracoes()
        self.assertTrue(cfg2.from_dict(dados))
        self.assertTrue(cfg2.tutorial_visto)

    def test_efeito_dash_rastro_subprocesso_e_listas(self):
        efeito = EfeitoDashRastro("subprocesso_atrasado")
        self.assertIs(efeito.vortices_vacuo, efeito.vortices)
        self.assertEqual(efeito.feixes_subprocesso, [])

        inimigo = SimpleNamespace(x=50.0, y=0.0, largura=32, altura=32, vivo=True, hp=100, atordoado_timer=0.0)
        def _receber_dano(qtd):
            inimigo.hp -= qtd
        inimigo.receber_dano = _receber_dano

        jogador = SimpleNamespace(dash_alcance_mult=1.0, dash_cooldown_restante=0.0)
        ctx = ContextoCombate(cena=None, jogador=jogador, inimigos=[inimigo], projeteis=[], drops=[])

        efeito.ao_dash(ctx, (0.0, 16.0), (120.0, 16.0))
        self.assertEqual(len(efeito.subprocessos_pendentes), 1)

        efeito.ao_tick(ctx, 0.80)
        self.assertEqual(len(efeito.subprocessos_pendentes), 0)
        self.assertEqual(inimigo.hp, 70)
        self.assertAlmostEqual(inimigo.atordoado_timer, 1.1, places=2)
        self.assertEqual(len(efeito.feixes_subprocesso), 1)

    def test_dash_bowling_empurra_lateralmente_atordoa_e_escala_por_hp(self):
        efeito = EfeitoInerciaCinetica(nivel=2)
        jogador = SimpleNamespace(
            x=100.0, y=100.0, largura=42, altura=42,
            dash_ativo_timer=0.18, dash_dir=(1.0, 0.0),
        )
        # Tank logo abaixo do eixo do dash -> empurrado para +Y (lateralmente)
        tank = SimpleNamespace(
            x=115.0, y=110.0, largura=32, altura=32, vivo=True,
            hp=300, hp_max=300, vx_knockback=0.0, vy_knockback=0.0,
            slow_timer=0.0, slow_fator=1.0, atordoado_timer=0.0,
            em_derrapagem_cinetica=False,
        )
        # Segundo inimigo colidindo com o Tank
        alvo = SimpleNamespace(
            x=115.0, y=115.0, largura=32, altura=32, vivo=True,
            hp=500, hp_max=500, vx_knockback=0.0, vy_knockback=0.0,
            _boliche_cd=0.0,
        )
        def _dano_alvo(qtd):
            alvo.hp -= qtd
        alvo.receber_dano = _dano_alvo

        ctx = ContextoCombate(cena=None, jogador=jogador, inimigos=[tank, alvo], projeteis=[], drops=[])
        efeito.ao_dash(ctx, (100.0, 100.0), (200.0, 100.0))
        efeito.ao_tick(ctx, 0.016)

        # Tank foi empurrado lateralmente (perpendicular ao dash em X -> Y positivo), atordoado e virou pino
        self.assertAlmostEqual(tank.vx_knockback, 0.0, places=3)
        self.assertGreater(tank.vy_knockback, 400.0)
        self.assertGreaterEqual(tank.slow_timer, 0.70)
        self.assertEqual(tank.slow_fator, 0.0)
        self.assertTrue(tank.em_derrapagem_cinetica)

        # Dano de colisão em alvo escala com o HP do Tank empurrado (300 * 0.80 = 240 + bônus)
        dano_sofrido = 500 - alvo.hp
        self.assertGreaterEqual(dano_sofrido, 240)


if __name__ == "__main__":
    unittest.main()
