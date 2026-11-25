"""
Bateria de Testes de Aceite — Refatoração UX (v2.0-experimento) + Bugs Extras + Temas B & C
Cobre:
1. Ocultação progressiva de UI (Loadout, CONQUISTAS vs CONQUISTAS & FIRMWARE, MenuConfigs sem cadeados).
2. Cota 2-4-6 de Firmware, status ATIVO/INATIVO, modal de confirmação no hot-swap (ordem inversa 3->2->1),
   reativação automática e banners dedicados.
3. Reajuste de conquistas (primeiro_overclock_sujo, mestre_chave_inglesa M2 troféu, depurador_escritorio M2 slot)
   e troca automática de pin (mestre_chave_inglesa -> primeiro_overclock_sujo -> remoção).
4. Bugs Extras: indicador de combo (contagem/timer_janela/ESTILO 0x), postura_riposte (raiz+invuln+estocada+stun+perfurante).
5. Tema B (chegada 2 ciclos / 48.000 HP / normalização Mini-Boss Ciclo 1 [750..850]).
6. Tema C (retícula alto-contraste, preferencias_mira sem afetar cota, mira_oculta oculta cursor + homing ao ponteiro).
"""

import os
import sys
import math
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame
pygame.init()
pygame.font.init()
pygame.display.set_mode((1280, 720))

from src.cenas.gameplay import GameplayScene
from src.cenas.menu_principal import MenuPrincipalScene
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.inimigo_blindado import InimigoBlindado
from src.entidades.inimigo_tank import InimigoTank
from src.entidades.projetil import Projetil
from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY, CONFIGURACOES_SISTEMA
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.sistemas.sistema_conquistas import COTAS_SLOTS_FIRMWARE, SistemaConquistas
from src.sistemas.sistema_spawn import SistemaSpawn
from src.ui.hud import HUD
from src.ui.menu_configs import MenuConfigs
from src.ui.menu_conquistas import MenuConquistas
from src.utils import constantes as C


class _FakeKB:
    def __init__(self, down=None, pressed=None):
        self._down = set(down or ())
        self._pressed = set(pressed or ())

    def key_down(self, k):
        return k in self._down

    def key_pressed(self, k):
        return k in self._pressed


class _FakeMouse:
    def __init__(self, pos=(0, 0), down=False, pressed=False):
        self._pos = pos
        self._down = down
        self._pressed = pressed

    def get_position(self):
        return self._pos

    def button_down(self, b):
        return b == 1 and self._down

    def is_button_down(self, b):
        return b == 1 and self._pressed

    def button_pressed(self, b):
        return b == 1 and self._pressed


class TestUxRefactorPlaytest3(unittest.TestCase):
    def setUp(self):
        self.screen = pygame.Surface((1280, 720))

    def test_01_save_zerado_ocultacao_progressiva_ui(self):
        with patch.object(GerenciadorConfiguracoes, "carregar_arquivo", return_value=True):
            menu_pr = MenuPrincipalScene()

        cfg = menu_pr.gerenciador_config
        cfg.from_dict({})
        menu_pr._sincronizar_rotulos_menu()

        self.assertEqual(menu_pr.opcoes[2], "CONQUISTAS [F]")
        self.assertFalse(menu_pr._possui_loadout_alternativo())
        self.assertFalse(menu_pr._possui_firmware_desbloqueado())

        menu_conq = MenuConquistas(cfg, cfg.sistema_conquistas, em_jogo=False)
        menu_conq.abrir(aba=1)
        self.assertEqual(menu_conq.aba_atual, 0)
        self.assertFalse(menu_conq.possui_firmware_desbloqueado())
        menu_conq.update(0.016, teclado=_FakeKB(down={"TAB"}), mouse=_FakeMouse())
        self.assertEqual(menu_conq.aba_atual, 0)
        menu_conq.draw(self.screen)

        menu_cfg = MenuConfigs(cfg, em_jogo=False)
        menu_cfg.abrir()
        menu_cfg.draw(self.screen)
        self.assertEqual(len(cfg.desbloqueadas), 0)
        self.assertEqual(cfg.sistema_conquistas.fixadas, ["mestre_chave_inglesa"])

    def test_02_15_parries_revela_loadout_e_troca_pin_automatico(self):
        with patch.object(GerenciadorConfiguracoes, "carregar_arquivo", return_value=True):
            menu_pr = MenuPrincipalScene()

        cfg = menu_pr.gerenciador_config
        cfg.from_dict({})
        notifs = cfg.sistema_conquistas.registrar_evento("parry", 15)
        self.assertTrue(any("mestre_chave_inglesa:m1" == n["id"] for n in notifs))
        self.assertTrue(cfg.sistema_conquistas.possui_recompensa("arma", "smg_compacta"))
        self.assertEqual(cfg.sistema_conquistas.fixadas, ["primeiro_overclock_sujo"])

        menu_pr._sincronizar_rotulos_menu()
        self.assertTrue(menu_pr._possui_loadout_alternativo())
        self.assertEqual(menu_pr.opcoes[2], "CONQUISTAS [F]")
        menu_pr.draw()

    def test_03_primeiro_overclock_sujo_e_depurador_m2_slots(self):
        sc = SistemaConquistas()
        sc.registrar_evento("parry", 15)
        self.assertEqual(sc.fixadas, ["primeiro_overclock_sujo"])

        # Mini-Boss com apenas 1 config não-neutra NÃO conclui primeiro_overclock_sujo
        sc.registrar_evento("miniboss_rapido", 1, {"configs_nao_neutras": 1, "superaqueceu": False})
        self.assertNotIn("primeiro_overclock_sujo", sc.unicas_concluidas)

        # Com >= 2 configs e < 60s conclui, libera gatilho_duplo e limpa pin automático
        notifs = sc.registrar_evento("miniboss_rapido", 1, {"configs_nao_neutras": 2, "superaqueceu": False})
        self.assertIn("primeiro_overclock_sujo", sc.unicas_concluidas)
        self.assertTrue(sc.possui_recompensa("modificador_run", "gatilho_duplo"))
        self.assertNotIn("primeiro_overclock_sujo", sc.fixadas)
        self.assertTrue(any(n["id"] == "primeiro_overclock_sujo" for n in notifs))

        # mestre_chave_inglesa M2 (50 parries) concede trofeu reflexo_metalico
        sc.registrar_evento("parry", 35)
        self.assertTrue(sc.possui_recompensa("trofeu", "reflexo_metalico"))

        # depurador_escritorio: 250 abates -> 1 slot; 1500 abates -> 2 slots + adrenalina_overclock
        sc.registrar_evento("abate", 250)
        self.assertEqual(sc.slots_firmware_max, 1)
        sc.registrar_evento("abate", 1250)
        self.assertEqual(sc.slots_firmware_max, 2)
        self.assertTrue(sc.possui_recompensa("modificador_run", "adrenalina_overclock"))

    def test_04_cota_246_hotswap_modal_banners_e_reativacao(self):
        with patch.object(GerenciadorConfiguracoes, "salvar_arquivo", return_value=True):
            cena = GameplayScene()
            cfg = cena.gerenciador_config
            cfg.from_dict({})
            for cid in ("fps_cap", "zoom", "hud", "vsync", "movimento_mouse", "fogo_amigo"):
                cfg.desbloquear_config(cid)

            sc = cfg.sistema_conquistas
            sc.slots_firmware_max = 3
            for chip in ("gatilho_duplo", "adrenalina_overclock", "reset_voraz"):
                sc.recompensas["modificador_run"].add(chip)
                sc.equipar_firmware(chip)

            # Equipar abaixo da cota (0 configs -> 0 ativos; UI mostra INATIVO)
            self.assertEqual(sc.obter_firmwares_ativos(0), [])
            self.assertEqual(len(sc.obter_firmwares_inativos(0)), 3)
            menu_conq = MenuConquistas(cfg, sc, em_jogo=False)
            menu_conq.abrir(aba=1)
            menu_conq.draw(self.screen)

            # Ativa 6 configs -> ativa os 3 slots e registra handlers
            for cid, val in (
                ("fps_cap", "30"),
                ("zoom", "75%"),
                ("hud", "desligado"),
                ("vsync", "desligado"),
                ("movimento_mouse", "ligado"),
                ("fogo_amigo", "ligado"),
            ):
                cfg.definir_valor_com_conflitos(cid, val)
            cena.aplicar_modificadores()
            self.assertIsNotNone(cena.efeitos_combate.obter_efeito("gatilho_duplo"))
            self.assertIsNotNone(cena.efeitos_combate.obter_efeito("adrenalina_overclock"))
            self.assertIsNotNone(cena.efeitos_combate.obter_efeito("reset_voraz"))

            # Desligar fogo_amigo cai de 6 -> 5 e exige confirmação no modal (Slot 3 -> reset_voraz)
            cena.menu_configs.abrir()
            cena.banners_desbloqueio.clear()
            aplicou = cena.menu_configs.alterar_valor_gameplay("fogo_amigo", "desligado")
            self.assertFalse(aplicou)
            pend = cena.menu_configs._confirmacao_pendente
            self.assertIsNotNone(pend)
            self.assertEqual([c[0] for c in pend["chips"]], ["reset_voraz"])

            # Desenha modal com zero erro; ESC cancela preservando estado
            cena.menu_configs.draw(self.screen)
            cena.menu_configs.update(0.016, teclado=_FakeKB(down={"ESC"}), mouse=_FakeMouse())
            self.assertIsNone(cena.menu_configs._confirmacao_pendente)
            self.assertEqual(cfg.obter_valor("fogo_amigo"), "ligado")
            self.assertIsNotNone(cena.efeitos_combate.obter_efeito("reset_voraz"))

            # Confirmar por ENTER aplica desativação e enfileira banner dedicado
            cena.menu_configs.alterar_valor_gameplay("fogo_amigo", "desligado")
            cena.menu_configs.update(0.016, teclado=_FakeKB(down={"RETURN"}), mouse=_FakeMouse())
            self.assertEqual(cfg.obter_valor("fogo_amigo"), "desligado")
            self.assertIsNone(cena.efeitos_combate.obter_efeito("reset_voraz"))
            self.assertTrue(any(b["titulo"] == "FIRMWARE DESATIVADO" for b in cena.banners_desbloqueio))

            # Desligar hud (5 -> 4, mantém Slot 2 ativo), depois desligar vsync (4 -> 3 -> abre modal Slot 2!)
            self.assertTrue(cena.menu_configs.alterar_valor_gameplay("hud", "ligado"))
            self.assertIsNotNone(cena.efeitos_combate.obter_efeito("adrenalina_overclock"))
            self.assertFalse(cena.menu_configs.alterar_valor_gameplay("vsync", "ligado"))
            self.assertEqual([c[0] for c in cena.menu_configs._confirmacao_pendente["chips"]], ["adrenalina_overclock"])
            cena.menu_configs.update(0.016, teclado=_FakeKB(down={"RETURN"}), mouse=_FakeMouse())
            self.assertIsNone(cena.efeitos_combate.obter_efeito("adrenalina_overclock"))

            # Religar hud (3 -> 4) reativa Slot 2 automaticamente sem modal + banner de reativação
            cena.banners_desbloqueio.clear()
            self.assertTrue(cena.menu_configs.alterar_valor_gameplay("hud", "desligado"))
            self.assertIsNotNone(cena.efeitos_combate.obter_efeito("adrenalina_overclock"))
            self.assertTrue(any(b["titulo"] == "FIRMWARE REATIVADO" for b in cena.banners_desbloqueio))

    def test_05_postura_riposte(self):
        # Postura Riposte: flag correta + janela 0.45 + parry 360 na hitbox da batata + firewall apenas na parede
        cena = GameplayScene()
        cena.gerenciador_config.desbloquear_config("precisao_parry")
        cena.gerenciador_config.sistema_conquistas.recompensas["opcao_config"].add("precisao_parry:postura_riposte")
        ok_prec, _ = cena.gerenciador_config.definir_valor_com_conflitos("precisao_parry", "postura_riposte")
        self.assertTrue(ok_prec)
        cena.aplicar_modificadores()
        melee = cena._obter_arma_melee()
        self.assertTrue(getattr(melee, "parry_modo_postura_riposte", False))
        self.assertAlmostEqual(melee.parry_duracao, 0.45)

        jx = cena.jogador.x + cena.jogador.largura * 0.5
        jy = cena.jogador.y + cena.jogador.altura * 0.5
        alvo_linha = InimigoPadrao(x=jx + 160.0, y=jy - 14.0)
        alvo_linha.hp = 120
        alvo_linha.hp_max = 120
        cena.inimigos = [alvo_linha]
        proj_frente = Projetil(x=jx + 12.0, y=jy, dir_x=-1.0, dir_y=0.0, dono="inimigo", dano=20)
        proj_tras = Projetil(x=jx - 22.0, y=jy, dir_x=1.0, dir_y=0.0, dono="inimigo", dano=20)
        proj_longe = Projetil(x=jx + 65.0, y=jy, dir_x=-1.0, dir_y=0.0, dono="inimigo", dano=20)
        cena.projeteis = [proj_frente, proj_tras, proj_longe]

        cena._executar_acao_parry(melee, jx, jy, 0.0, cena.gerenciador_config.obter_modificadores())
        self.assertAlmostEqual(cena.jogador.enraizado_timer, 0.45)
        self.assertAlmostEqual(cena.jogador.riposte_invuln_timer, 0.45)
        self.assertEqual(proj_frente.dono, "jogador")
        self.assertEqual(proj_tras.dono, "jogador")
        self.assertEqual(proj_longe.dono, "inimigo")
        self.assertTrue(proj_frente.perfurante)
        self.assertGreaterEqual(proj_frente.perfuracoes_restantes, 3)
        self.assertLess(alvo_linha.hp, 120)
        self.assertGreaterEqual(getattr(alvo_linha, "slow_timer", 0.0), 1.5)
        self.assertEqual(getattr(alvo_linha, "slow_fator", 1.0), 0.0)

        # Firewall Estatico bloqueia apenas na parede (segmento), nao no circulo ao redor
        cena.gerenciador_config.desbloquear_config("efeito_parry")
        cena.gerenciador_config.definir_valor_com_conflitos("efeito_parry", "firewall_estatico")
        cena.aplicar_modificadores()
        ef_parry = cena.efeitos_combate.obter_efeito("parry_avancado")
        ef_parry.barreiras_firewall = [{"x": jx + 56.0, "y": jy, "ang": 0.0, "raio": 65.0, "tempo": 2.0, "duracao": 2.0}]
        p_na_parede = Projetil(x=jx + 56.0, y=jy + 20.0, dir_x=-1.0, dir_y=0.0, dono="inimigo")
        # Dentro do antigo circulo (distancia 40 do centro da parede), porem distante perpendicularmente da linha!
        p_fora_parede = Projetil(x=jx + 20.0, y=jy, dir_x=0.0, dir_y=1.0, dono="inimigo")
        cena.projeteis = [p_na_parede, p_fora_parede]
        cena.efeitos_combate.disparar_ao_tick(
            cena._construir_ctx_combate(cena.gerenciador_config.obter_modificadores()),
            0.016,
        )
        self.assertFalse(p_na_parede.ativo)
        self.assertTrue(p_fora_parede.ativo)

    def test_06_miniboss_ciclo1_normalizado_para_todos_arquetipos(self):
        for cls_mb, nome_mb, arq_id in SistemaSpawn.ARQUETIPOS_MINIBOSS_4:
            sp = SistemaSpawn(fila_minibosses=[(cls_mb, nome_mb, arq_id), (InimigoBlindado, "MB2", "nobreak_chumbado")])
            novos = sp.update(0.016, 0.0, 0.0, 0, fase_onda="assault", gatilho_assault_intro=True, possui_elite_vivo=False)
            elites = [e for e in novos if getattr(e, "is_elite", False)]
            self.assertEqual(len(elites), 1)
            self.assertGreaterEqual(elites[0].hp_max, 750)
            self.assertLessEqual(elites[0].hp_max, 850)

    def test_07_tema_c_mira_alto_contraste_preferencias_e_mira_oculta(self):
        cfg = GerenciadorConfiguracoes()
        self.assertEqual(len(CONFIGURACOES_SISTEMA), 3)
        self.assertEqual(cfg.contar_configs_nao_neutras(), 0)
        cfg.definir_preferencias_mira(cor="ouro", escala=1.5)
        # Preferência estética NÃO altera cota!
        self.assertEqual(cfg.contar_configs_nao_neutras(), 0)

        cfg.desbloquear_config("mira_oculta")
        cfg.definir_valor_com_conflitos("mira_oculta", "ligado")
        self.assertEqual(cfg.contar_configs_nao_neutras(), 1)
        mods = cfg.obter_modificadores()
        self.assertTrue(mods.mira_oculta_homing)

        cena = GameplayScene()
        cena.gerenciador_config = cfg
        cena.aplicar_modificadores()
        cena._ultimo_mouse_mundo = (cena.jogador.x + 100.0, cena.jogador.y + 180.0)
        tiro = Projetil(x=cena.jogador.x, y=cena.jogador.y, dir_x=1.0, dir_y=0.0, velocidade=300.0, dono="jogador")
        cena._despachar_tiros_arma(cena.jogador.obter_arma_ativa(), [tiro], mods)
        self.assertTrue(tiro.homing_ativo)
        self.assertTrue(tiro.homing_alvo_cursor)
        dir_y_antes = tiro.dir_y
        cena._atualizar_fisica_projeteis(0.05, mods, False, cena.jogador.x, cena.jogador.y)
        self.assertGreater(tiro.dir_y, dir_y_antes)
        cena.draw()

    def test_08_ventoinha_360_timer_parry_e_barras_hud_limpas(self):
        from src.armas.smg_compacta import SMGCompacta
        from src.armas.rifle_arco import RifleArco
        cena = GameplayScene()
        cena.gerenciador_config.desbloquear_config("efeito_parry")
        cena.gerenciador_config.definir_valor_com_conflitos("efeito_parry", "ventoinha_360")
        cena.aplicar_modificadores()
        melee = cena._obter_arma_melee()
        self.assertTrue(melee.parry_modo_ventoinha)
        self.assertAlmostEqual(melee.parry_alcance_mult, 0.75)
        self.assertAlmostEqual(melee.ultimo_parry_cd_total, 6.5)

        jx = cena.jogador.x + cena.jogador.largura * 0.5
        jy = cena.jogador.y + cena.jogador.altura * 0.5
        # Inimigo atrás do jogador (180 graus fora do cone frontal) + projétil parriável e não-parriável
        inim_tras = InimigoPadrao(x=jx - 75.0, y=jy - 14.0)
        inim_tras.hp = 50
        inim_tras.hp_max = 50
        cena.inimigos = [inim_tras]
        p_parriavel = Projetil(x=jx - 70.0, y=jy, dir_x=1.0, dir_y=0.0, dono="inimigo")
        p_amarelo = Projetil(x=jx - 60.0, y=jy, dir_x=1.0, dir_y=0.0, dono="inimigo", nao_parriavel=True)
        cena.projeteis = [p_parriavel, p_amarelo]

        # Ativação em 0° acerta 360° sem punição de whiff e registra 2º corte aos 0.30s
        ok = cena._executar_acao_parry(melee, jx, jy, 0.0, cena.gerenciador_config.obter_modificadores())
        self.assertTrue(ok)
        self.assertAlmostEqual(melee.tempo_recarga_restante, 6.5)
        self.assertFalse(p_parriavel.ativo)
        self.assertTrue(p_amarelo.ativo)
        self.assertEqual(inim_tras.hp, 18)  # 50 - 32 do 1o corte 360

        melee.atualizar(0.20)
        self.assertAlmostEqual(melee.tempo_recarga_restante, 6.5)  # zero penalidade de whiff!

        ctx_tick = cena._construir_ctx_combate(cena.gerenciador_config.obter_modificadores())
        abates_antes = cena.abates
        cena.efeitos_combate.disparar_ao_tick(ctx_tick, 0.32)
        self.assertFalse(inim_tras.vivo)
        self.assertEqual(cena.abates, abates_antes + 1)

        # HUD Painel Vitais + barras sob Cleiton (Pistola / SMG / RifleArco) sem barra amarela estática
        cena.janela.screen = self.screen
        cena.camera.x = 0.0
        cena.camera.y = 0.0
        cena.jogador.x = 100.0
        cena.jogador.y = 100.0
        cena.jogador.dash_desbloqueado = False
        melee.tempo_recarga_restante = 0.0
        base_y = int(cena.jogador.y + cena.jogador.altura + 5.0)
        cx_p = int(cena.jogador.x + cena.jogador.largura / 2.0)

        self.screen.fill((0, 0, 0))
        cena.jogador.selecionar_slot(2)
        cena._desenhar_hp_in_world()
        # Pistola sem barra amarela estática
        self.assertEqual(self.screen.get_at((cx_p, base_y + 8))[:3], (0, 0, 0))

        # SMG usa o próprio espaço da barra de munição para calor
        cena.jogador.armas[1] = SMGCompacta()
        cena.jogador.selecionar_slot(2)
        self.screen.fill((0, 0, 0))
        cena._desenhar_hp_in_world()
        self.assertNotEqual(self.screen.get_at((cx_p, base_y + 8))[:3], (0, 0, 0))

        cena.jogador.equipar_arma_especial(RifleArco())
        cena.jogador.selecionar_slot(3)
        cena._desenhar_hp_in_world()
        melee.tempo_recarga_restante = 3.2
        cena._desenhar_hp_in_world()
        cena.hud.desenhar_painel_vitais(self.screen, cena.jogador, visivel=True, arma_melee=melee)


if __name__ == "__main__":
    unittest.main()
