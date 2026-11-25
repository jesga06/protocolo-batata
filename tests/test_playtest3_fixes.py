import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

import pygame

from src.armas.lanca_chamas import LancaChamas
from src.armas.pistola import Pistola
from src.armas.smg_compacta import SMGCompacta
from src.cenas.gameplay import GameplayScene
from src.cenas.menu_principal import MenuPrincipalScene
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.jogador import Jogador
from src.entidades.projetil import Projetil
from src.sistemas.config_efeitos import ModificadoresGameplay
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.sistemas.conquistas_dados import CHIPS_FIRMWARE
from src.sistemas.efeitos_combate import ContextoCombate, GerenciadorEfeitosCombate
from src.sistemas.sistema_conquistas import SistemaConquistas
from src.sistemas.sistema_xp import SistemaXP
from src.ui.menu_conquistas import MenuConquistas
from src.utils import constantes


class _TecladoFake:
    def __init__(self, downs=None, pressed=None):
        self._downs = set(downs or ())
        self._pressed = set(pressed or ())

    def key_down(self, k):
        return k in self._downs

    def key_pressed(self, k):
        return k in self._pressed


class _MouseFake:
    def __init__(self, pos=(640.0, 360.0), lmb_down=False, lmb_pressed=False, rmb_down=False):
        self._pos = pos
        self._lmb_down = lmb_down
        self._lmb_pressed = lmb_pressed
        self._rmb_down = rmb_down

    def get_position(self):
        return self._pos

    def button_down(self, b):
        if b == 1:
            return self._lmb_down
        if b == 3:
            return self._rmb_down
        return False

    def button_pressed(self, b):
        if b == 1:
            return self._lmb_pressed
        return False


class TestPlaytest3Fixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        if not pygame.get_init():
            pygame.init()
        if not pygame.display.get_surface():
            pygame.display.set_mode((1280, 720))

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_save = constantes.SAVE_FILE_PATH
        constantes.SAVE_FILE_PATH = os.path.join(self._tmpdir.name, "save.json")

    def tearDown(self):
        constantes.SAVE_FILE_PATH = self._orig_save
        self._tmpdir.cleanup()

    def test_01_reset_save_sincroniza_menu_conquistas_zero_chips(self):
        menu = MenuPrincipalScene()
        sc = menu.gerenciador_config.sistema_conquistas
        sc.recompensas["modificador_run"].add("gatilho_duplo")
        sc.equipar_firmware("gatilho_duplo")

        menu.opcao_selecionada = 4
        menu._executar_opcao_selecionada()
        menu._executar_opcao_selecionada()

        menu.menu_conquistas.abrir(aba=1)
        for cid in CHIPS_FIRMWARE:
            self.assertFalse(menu.menu_conquistas.sistema_conquistas.possui_recompensa("modificador_run", cid))
        self.assertEqual(menu.menu_conquistas.sistema_conquistas.modificadores_equipados, [])

    def test_02_cadencia_armas_independente_de_fps(self):
        def _simular_tiros(fps: int, duracao_s: float = 1.0) -> int:
            cena = GameplayScene()
            cena.jogador.armas[1] = SMGCompacta()
            cena.jogador.slot_ativo = 2
            cena.gerenciador_config.ativas["auto_fire"] = "ligado"
            cena.gerenciador_config.desbloqueadas.add("auto_fire")
            cena._aguardando_soltar_lmb = False
            cena.mouse = _MouseFake(pos=(900.0, 360.0), lmb_pressed=True)
            cena.teclado = _TecladoFake()
            dt = 1.0 / float(fps)
            passos = int(round(duracao_s / dt))
            total_disparos = 0
            orig_desp = cena._despachar_tiros_arma

            def _contar(arma, tiros, mods):
                nonlocal total_disparos
                total_disparos += len(tiros)
                return orig_desp(arma, tiros, mods)

            cena._despachar_tiros_arma = _contar
            for _ in range(passos):
                cena.jogador.armas[1].update(dt)
                cena._atualizar_disparos_jogador(dt, ModificadoresGameplay(), 1.0, 1.0)
            return total_disparos

        tiros_15 = _simular_tiros(15, 1.1)
        tiros_60 = _simular_tiros(60, 1.1)
        self.assertLessEqual(abs(tiros_15 - tiros_60), 1)
        self.assertGreaterEqual(tiros_15, 10)

        chamas = LancaChamas()
        inim = InimigoPadrao(x=120.0, y=100.0)
        evs = chamas.atualizar_fluxo(0.30, True, 100.0, 100.0, 200.0, 100.0, [inim])
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["dano"], chamas.dano * 2)

    def test_03_monge_tibetano_contador_0_120_e_unlock(self):
        cena = GameplayScene()
        cena.gerenciador_config.desbloqueadas.add("fps_cap")
        cena.gerenciador_config.ativas["fps_cap"] = "15"
        if "monge_tibetano" not in cena.sistema_conquistas.fixadas:
            cena.sistema_conquistas.fixadas = ["monge_tibetano"]

        for _ in range(15):
            cena.loop(dt=1.0 / 15.0)
        resumo = cena.sistema_conquistas.obter_resumo_fixadas()
        monge = next(r for r in resumo if r["id"] == "monge_tibetano")
        self.assertEqual(monge["meta"], 120)
        self.assertGreaterEqual(monge["atual"], 1)

        cena.tempo_15fps_acumulado = 119.5
        cena.loop(dt=0.6)
        self.assertIn("monge_tibetano", cena.sistema_conquistas.unicas_concluidas)

    def test_04_aim_angle_sem_atraso_em_fps_baixo(self):
        jog = Jogador(x=100.0, y=100.0)
        jog.processar_input(_TecladoFake(), _MouseFake(pos=(116.0, 400.0)), dt=1.0 / 15.0, camera=None)
        self.assertAlmostEqual(jog.aim_angle, jog.aim_angle_alvo, places=5)

    def test_05_e_11_dash_teleporte_buffer_e_subprocesso_atrasado(self):
        cena = GameplayScene()
        cena.gerenciador_config.estatisticas["dash_desbloqueado"] = True
        cena.jogador.dash_desbloqueado = True
        cena.gerenciador_config.desbloqueadas.update(("dash_protocolo", "dash_rastro"))
        cena.gerenciador_config.ativas["dash_protocolo"] = "teleporte_buffer"
        cena.gerenciador_config.ativas["dash_rastro"] = "subprocesso_atrasado"
        cena.aplicar_modificadores()

        inim = InimigoPadrao(x=cena.jogador.x + 150.0, y=cena.jogador.y, hp=200)
        hp_antes = inim.hp
        cena.inimigos.append(inim)

        cx0 = cena.jogador.x + cena.jogador.largura * 0.5
        cy0 = cena.jogador.y + cena.jogador.altura * 0.5
        mods = cena.gerenciador_config.obter_modificadores()
        ok = cena._disparar_acao_dash(1.0, 0.0, cx0, cy0, mods)
        self.assertTrue(ok)
        self.assertGreater(cena.jogador.x - (cx0 - cena.jogador.largura * 0.5), 200.0)
        self.assertEqual(cena.jogador.dash_ativo_timer, 0.0)
        hp_pos_teleporte = inim.hp
        self.assertEqual(hp_pos_teleporte, hp_antes - 28)

        ef_dash = cena.efeitos_combate.obter_efeito("dash_rastro")
        self.assertEqual(len(ef_dash.subprocessos_pendentes), 1)
        sp = ef_dash.subprocessos_pendentes[0]
        self.assertGreater(sp["destino"][0] - sp["origem"][0], 200.0)

        ctx = cena._construir_ctx_combate(mods)
        cena.efeitos_combate.disparar_ao_tick(ctx, 0.80)
        self.assertEqual(inim.hp, hp_pos_teleporte - 30)
        self.assertGreater(inim.slow_timer, 0.0)

    def test_06_firmware_wrap_sem_truncamento(self):
        fonte = pygame.font.SysFont("Arial", 11)
        texto = CHIPS_FIRMWARE["canhoes_perimetrais"].descricao
        linhas = MenuConquistas._quebrar_texto_largura(fonte, texto, 330, max_linhas=4)
        self.assertGreaterEqual(len(linhas), 2)
        self.assertEqual(" ".join(linhas), texto)

    def test_07_e_08_garbage_collector_persiste_ram_ao_abrir_configs_e_apaga_projeteis(self):
        cena = GameplayScene()
        cena.gerenciador_config.desbloqueadas.add("garbage_collector")
        cena.gerenciador_config.ativas["garbage_collector"] = "ligado"
        cena.aplicar_modificadores()

        gc = cena.efeitos_combate.obter_efeito("garbage_collector")
        ctx = cena._construir_ctx_combate(cena.gerenciador_config.obter_modificadores())
        cena.efeitos_combate.disparar_ao_tick(ctx, 6.0)
        prog_antes = gc.ram_progresso
        self.assertAlmostEqual(prog_antes, 0.5, places=3)

        cena.aplicar_modificadores()
        self.assertAlmostEqual(cena.efeitos_combate.obter_efeito("garbage_collector").ram_progresso, prog_antes, places=3)

        jx = cena.jogador.x + cena.jogador.largura * 0.5
        jy = cena.jogador.y + cena.jogador.altura * 0.5
        p_longe_mas_na_tela = Projetil(x=jx + 380.0, y=jy, dir_x=-1.0, dir_y=0.0, dono="inimigo")
        cena.projeteis.append(p_longe_mas_na_tela)
        ctx2 = cena._construir_ctx_combate(cena.gerenciador_config.obter_modificadores())
        cena.efeitos_combate.disparar_ao_tick(ctx2, 6.0)
        cena.efeitos_combate.disparar_ao_tick(ctx2, 0.85)
        self.assertFalse(p_longe_mas_na_tela.ativo)

    def test_09_botao_engrenagem_sem_colisao_fantasma_legada(self):
        cena = GameplayScene()
        cena.teclado = _TecladoFake()
        cena.mouse = _MouseFake(pos=(765.0, 30.0), lmb_down=True)
        cena.loop(dt=1.0 / 60.0)
        self.assertFalse(cena.menu_configs.ativo)

        cena.mouse = _MouseFake(pos=(constantes.LARGURA_TELA - 32.0, 30.0), lmb_down=True)
        cena.loop(dt=1.0 / 60.0)
        self.assertTrue(cena.menu_configs.ativo)

    def test_10_xp_bonus_hud_desligado_sem_perda_fracionaria(self):
        sx = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        for _ in range(4):
            sx.adicionar_xp(5, mult_xp=1.25)
        self.assertEqual(sx.xp_total, 25)

    def test_12_firewall_estatico_spawna_em_mira_e_bloqueia_projetil(self):
        cena = GameplayScene()
        cena.gerenciador_config.desbloqueadas.add("efeito_parry")
        cena.gerenciador_config.ativas["efeito_parry"] = "firewall_estatico"
        cena.aplicar_modificadores()

        mods = cena.gerenciador_config.obter_modificadores()
        cx = cena.jogador.x + cena.jogador.largura * 0.5
        cy = cena.jogador.y + cena.jogador.altura * 0.5
        arma_melee = cena._obter_arma_melee()
        ativou = cena._executar_acao_parry(arma_melee, cx, cy, 0.0, mods)
        self.assertTrue(ativou)

        ef_parry = cena.efeitos_combate.obter_efeito("parry_avancado")
        self.assertEqual(len(ef_parry.barreiras_firewall), 1)
        bar = ef_parry.barreiras_firewall[0]
        self.assertAlmostEqual(bar["x"], cx + 56.0, places=2)

        proj = Projetil(x=bar["x"], y=bar["y"], dir_x=-1.0, dir_y=0.0, dono="inimigo")
        cena.projeteis.append(proj)
        ctx = cena._construir_ctx_combate(mods)
        cena.efeitos_combate.disparar_ao_tick(ctx, 0.016)
        self.assertFalse(proj.ativo)

    def test_13_abate_pipeline_b_plus_registra_drop_e_abate(self):
        from src.entidades import InimigoPadrao
        from src.sistemas.efeitos_combate import _aplicar_dano_entidade

        cena = GameplayScene()
        inim = InimigoPadrao(x=100.0, y=100.0, hp=10)
        cena.inimigos.append(inim)
        abates_antes = cena.abates
        ctx = cena._construir_ctx_combate(cena.gerenciador_config.obter_modificadores())

        _aplicar_dano_entidade(inim, 20, ctx=ctx, origem="blink")
        self.assertFalse(inim.vivo)
        self.assertEqual(cena.abates, abates_antes + 1)
        self.assertGreater(len(cena.sistema_drops.drops), 0)

    def test_14_sombra_espelho_render_sem_linhas_nao_levanta_unbound(self):
        from src.sistemas.efeitos_combate import EfeitoDashProtocolo
        from src.entidades.holograma import EntidadeHolograma

        ef = EfeitoDashProtocolo("sombra_espelho")
        ef.sombra_ativa = EntidadeHolograma(x=120.0, y=120.0, modo="sombra", duracao=3.0)
        ef._sombra_parry_timer = 0.2
        surf = pygame.Surface((320, 240))
        ctx = GameplayScene()._construir_ctx_combate(None)
        ef.ao_pos_render_mundo(ctx, surf, camera=None)

    def test_15_ninja_vulnerabilidade_e_chaves_assets_e_config_ativa(self):
        from src.entidades.inimigo_ninja import InimigoNinja
        from src.utils.constantes import ASSET_PATHS
        from src.ui.banner_dicas import _config_esta_ativa

        ninja = InimigoNinja(x=100.0, y=100.0, hp=200)
        self.assertEqual(ninja.receber_dano(20, fonte="melee"), 0)
        self.assertEqual(ninja.receber_dano(20, fonte="projetil_efeito"), 0)
        self.assertGreater(ninja.receber_dano(20, fonte="railgun"), 0)
        self.assertGreater(ninja.receber_dano(20, fonte="rifle_arco_direto"), 0)
        self.assertGreater(ninja.receber_dano(20, fonte="lanca_chamas"), 0)

        self.assertIn("jogador_idle", ASSET_PATHS)
        self.assertIn("sfx_levelup", ASSET_PATHS)
        self.assertIn("arma_smg_compacta", ASSET_PATHS)

        cena = GameplayScene()
        cena.gerenciador_config.desbloqueadas.add("modo_wireframe")
        cena.gerenciador_config.ativas["modo_wireframe"] = "ligado"
        self.assertTrue(_config_esta_ativa(cena.gerenciador_config, "modo_wireframe"))

    def test_16_ventoinha_preserva_alcance_lmb_e_conquistas_nivel_e_streak(self):
        cena = GameplayScene()
        alc_base = float(cena._obter_arma_melee().alcance)
        cena.gerenciador_config.desbloqueadas.add("efeito_parry")
        cena.gerenciador_config.ativas["efeito_parry"] = "ventoinha_360"
        cena.aplicar_modificadores()
        self.assertAlmostEqual(float(cena._obter_arma_melee().alcance), alc_base, places=2)

        cena.gerenciador_config.desbloqueadas.update({"hud", "iluminacao"})
        cena.gerenciador_config.ativas["hud"] = "desligado"
        cena.gerenciador_config.ativas["iluminacao"] = "ligado"
        cena._ao_subir_nivel(8)
        self.assertIn("zero_visao_cem_fe", cena.sistema_conquistas.unicas_concluidas)

    def test_17_audio_sfx_volume_armas_explosao_e_sintetizadores(self):
        from PPlay.sound import SoundManager
        from src.armas.pistola import Pistola
        from src.armas.melee import Melee
        from src.armas.minigun import Minigun
        from src.armas.shotgun import Shotgun
        from src.armas.rifle_assalto import RifleAssalto
        from src.armas.lanca_foguetes import LancaFoguetes
        from src.armas.lanca_granadas import LancaGranadas
        from src.armas.railgun import Railgun
        from src.armas.smg_compacta import SMGCompacta
        from src.armas.rifle_arco import RifleArco
        from src.armas.lanca_chamas import LancaChamas
        from src.armas.bastao_choque import BastaoChoque
        from src.cenas.gameplay_combate import GameplayCombateMixin
        from src.sistemas.sistema_audio import GerenciadorAudio

        # 1. SoundManager deve receber escala 0..100 (100% -> 1.0, nunca 0.01)
        cena = GameplayScene()
        cena.config_sistema.definir_valor("volume_master", 100)
        cena.config_sistema.definir_valor("volume_sfx", 100)
        cena.aplicar_modificadores()
        self.assertAlmostEqual(SoundManager._volume_sfx, 1.0, places=2)

        # 2. Todas as 12 armas (inclusive Pistola/"Padrão de Fábrica") devem mapear para SFX
        self.assertEqual(GameplayCombateMixin._obter_sfx_arma(Pistola()), "sfx_tiro_pistola")
        for cls_arma in (
            Pistola, Melee, Minigun, Shotgun, RifleAssalto,
            LancaFoguetes, LancaGranadas, Railgun, SMGCompacta,
            RifleArco, LancaChamas, BastaoChoque,
        ):
            self.assertIsNotNone(
                GameplayCombateMixin._obter_sfx_arma(cls_arma()),
                f"{cls_arma.__name__} retornou SFX None",
            )

        # 3. GerenciadorAudio gera pool de explosão e sintetiza dash, arco elétrico e lança-chamas
        audio = GerenciadorAudio(inicializar_automaticamente=True)
        if audio.mixer_disponivel:
            self.assertIn("explosao", audio.pool_pitch)
            self.assertGreaterEqual(len(audio.pool_pitch["explosao"]), 1)
            self.assertIsNotNone(audio._som_dash)
            self.assertIsNotNone(audio._som_arco_eletrico)
            self.assertIsNotNone(audio._som_lanca_chamas)
            self.assertEqual(len(audio._sons_lanca_chamas), 4)

    def test_18_particulas_lanca_chamas_alcance_e_densidade(self):
        import math
        from src.sistemas.sistema_particulas import SistemaParticulas

        sp = SistemaParticulas()
        alcance = 195.0
        arco_graus = 55.0
        meio_arco_rad = math.radians(arco_graus * 0.5)
        sp.emitir_jato_chamas(0.0, 0.0, 0.0, alcance, arco_graus, dt=1.0 / 60.0)
        # Densidade equilibrada: 2..4 partículas por frame a 60 FPS (meio-termo entre 1 e 6)
        self.assertGreaterEqual(len(sp.particulas), 2)
        self.assertLessEqual(len(sp.particulas), 4)

        # Simula vida completa de um lote de partículas e verifica encaixe exato no cone de dano
        sp.limpar()
        distancias = []
        for _ in range(20):
            sp.emitir_jato_chamas(0.0, 0.0, 0.0, alcance, arco_graus, dt=1.0 / 60.0)
        for p in list(sp.particulas):
            t_sim = 0.0
            dt = 1.0 / 120.0
            while p.viva and t_sim < 1.0:
                p.update(dt)
                t_sim += dt
            dist = math.hypot(p.x, p.y)
            ang = abs(math.atan2(p.y, p.x))
            self.assertLessEqual(dist, alcance * 1.05)
            self.assertLessEqual(ang, meio_arco_rad + 1e-3)
            distancias.append(dist)

        dist_media = sum(distancias) / max(1, len(distancias))
        self.assertGreaterEqual(dist_media, alcance * 0.80)
        self.assertLessEqual(dist_media, alcance * 1.02)

    def test_19_modo_wireframe_hitboxes_e_cores_tiros_especiais(self):
        from src.entidades.inimigo_padrao import InimigoPadrao
        from src.entidades.projetil import Projetil
        from src.cenas.gameplay_render import GameplayRenderMixin

        cena = GameplayScene()
        cena.gerenciador_config.desbloqueadas.add("modo_wireframe")
        cena.gerenciador_config.ativas["modo_wireframe"] = "ligado"
        mods = cena.gerenciador_config.obter_modificadores()
        self.assertTrue(mods.modo_wireframe)

        inim = InimigoPadrao(200.0, 200.0)
        bw, bh = inim.largura, inim.altura
        p_jog = Projetil(100.0, 100.0, 1.0, 0.0, largura=8, altura=8, dono="jogador")
        p_inim = Projetil(120.0, 120.0, -1.0, 0.0, largura=10, altura=10, dono="inimigo")
        p_shuriken = Projetil(140.0, 140.0, -1.0, 0.0, dono="inimigo", nao_desviavel=True)
        p_imp = Projetil(160.0, 160.0, -1.0, 0.0, dono="inimigo", eh_impressora=True)
        p_parry = Projetil(180.0, 180.0, 1.0, 0.0, dono="jogador", refletido_parry=True)

        cena.inimigos = [inim]
        cena.projeteis = [p_jog, p_inim, p_shuriken, p_imp, p_parry]
        cena._sincronizar_hitboxes_wireframe(mods)

        self.assertEqual(inim.largura, int(round(bw * 1.30)))
        self.assertEqual(inim.altura, int(round(bh * 1.30)))
        self.assertEqual(p_jog.largura, int(round(8 * 1.35)))
        self.assertEqual(p_inim.largura, int(round(10 * 1.35)))

        # Cores distintas para tiros especiais no wireframe
        cor_comum_inim = GameplayRenderMixin._cor_wireframe_projetil(p_inim)
        cor_shuriken = GameplayRenderMixin._cor_wireframe_projetil(p_shuriken)
        cor_imp = GameplayRenderMixin._cor_wireframe_projetil(p_imp)
        cor_parry = GameplayRenderMixin._cor_wireframe_projetil(p_parry)
        self.assertEqual(len({cor_comum_inim, cor_shuriken, cor_imp, cor_parry}), 4)


if __name__ == "__main__":
    unittest.main()
