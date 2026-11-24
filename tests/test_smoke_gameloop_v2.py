"""
Smoke Test Headless & Auditoria de Performance v2.0 — Protocolo: Batata
Executa 660+ frames reais de GameplayScene.loop() e GameplayScene.draw() em modo headless,
exercitando:
- Progressão completa de ondas musicais (ANTICIPATION -> HOLD -> ASSAULT_INTRO -> ASSAULT -> Mini-Boss -> Geladeira Tsunami)
- 8 configs não-neutras ativas simultaneamente (vsync, modo_wireframe, latencia_ping, garbage_collector,
  velocidade_inimigos, vida_inimigos, dash_protocolo, dash_rastro)
- Chip de Firmware equipado (medidor_estilo)
- Todas as 4 novas armas (BastaoChoque, SMGCompacta, RifleArco, LancaChamas)
- EntidadeHolograma (sombra e clone_agro)
- Abertura e fechamento do MenuConquistas
- Espião determinístico pós-init garantindo ZERO alocações de fonte (pygame.font.Font / SysFont)
  e ZERO chamadas de I/O em disco (builtins.open) durante frames em regime permanente.
"""

import builtins
import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.armas.bastao_choque import BastaoChoque
from src.armas.lanca_chamas import LancaChamas
from src.armas.rifle_arco import RifleArco
from src.armas.smg_compacta import SMGCompacta
from src.cenas.gameplay import GameplayScene
from src.entidades.holograma import EntidadeHolograma
from src.entidades.inimigo_padrao import InimigoPadrao
from src.sistemas.sistema_musica import SistemaMusica
from src.utils import constantes


class TestSmokeGameloopV2(unittest.TestCase):
    """Simulação headless de 660 frames com auditoria estrita de zero I/O e zero alocação de fonte."""

    def setUp(self):
        if not pygame.get_init():
            pygame.init()
        self._tmpdir = tempfile.TemporaryDirectory()
        self._old_save = constantes.SAVE_FILE_PATH
        constantes.SAVE_FILE_PATH = os.path.join(self._tmpdir.name, "smoke_save.json")

    def tearDown(self):
        constantes.SAVE_FILE_PATH = self._old_save
        self._tmpdir.cleanup()

    def test_660_frames_headless_v2_simulation_and_zero_io_font_audit(self):
        cena = GameplayScene()

        # 1. Ativa 8 configs não-neutras solicitadas + Firmware medidor_estilo
        configs_alvo = {
            "vsync": "desligado",
            "modo_wireframe": "ligado",
            "latencia_ping": "ligado",
            "garbage_collector": "ligado",
            "velocidade_inimigos": "+25%",
            "vida_inimigos": "+50%",
            "dash_protocolo": "sombra_espelho",
            "dash_rastro": "thread_fantasma",
        }
        cena.config_sistema.estatisticas["dash_desbloqueado"] = True
        cena.jogador.dash_desbloqueado = True
        for cid, val in configs_alvo.items():
            # Desbloqueia diretamente no conjunto para cobrir inclusive configs de conquista (latencia_ping)
            cena.config_sistema.desbloqueadas.add(cid)
            if not cena.config_sistema.definir_valor(cid, val):
                cena.config_sistema.ativas[cid] = val

        if cena.sistema_conquistas is not None:
            cena.sistema_conquistas.recompensas.setdefault("modificador_run", set()).add("medidor_estilo")
            if "medidor_estilo" not in cena.sistema_conquistas.modificadores_equipados:
                cena.sistema_conquistas.modificadores_equipados.append("medidor_estilo")

        cena.aplicar_modificadores()

        # Confirma que os modificadores v2.0 foram realmente propagados
        mods = cena.config_sistema.obter_modificadores()
        self.assertTrue(mods.modo_wireframe)
        self.assertTrue(mods.latencia_ping)
        self.assertTrue(mods.garbage_collector)
        self.assertEqual(mods.dash_protocolo, "sombra_espelho")
        self.assertEqual(mods.dash_rastro, "thread_fantasma")

        # Prepara as 4 novas armas v2.0 para rotação durante a simulação
        novas_armas = [
            BastaoChoque(),
            SMGCompacta(),
            RifleArco(),
            LancaChamas(),
        ]
        cena.jogador.armas[0] = novas_armas[0]
        cena.jogador.arma_especial = novas_armas[1]

        # Garante MenuConquistas inicializado antes do espião
        self.assertIsNotNone(cena.menu_conquistas)

        # Espiões determinísticos pós-init
        font_calls = []
        sysfont_calls = []
        open_calls = []

        real_font = pygame.font.Font
        real_sysfont = pygame.font.SysFont
        real_open = builtins.open

        def spy_font(*args, **kwargs):
            font_calls.append(args)
            return real_font(*args, **kwargs)

        def spy_sysfont(*args, **kwargs):
            sysfont_calls.append(args)
            return real_sysfont(*args, **kwargs)

        def spy_open(*args, **kwargs):
            open_calls.append(args[0] if args else "<unknown>")
            return real_open(*args, **kwargs)

        dt = 1.0 / 60.0
        total_frames = 0
        fases_musica_vistas = set()

        with (
            patch("pygame.font.Font", side_effect=spy_font),
            patch("pygame.font.SysFont", side_effect=spy_sysfont),
            patch("builtins.open", side_effect=spy_open),
        ):
            # --- FASE 1 (180 frames): Ondas Musicais (ANTICIPATION -> HOLD -> ASSAULT_INTRO -> ASSAULT),
            # 4 novas armas + EntidadeHolograma ---
            estados_musica = [
                SistemaMusica.ESTADO_ANTICIPATION,
                SistemaMusica.ESTADO_HOLD,
                SistemaMusica.ESTADO_ASSAULT_INTRO,
                SistemaMusica.ESTADO_ASSAULT,
            ]
            cena.hologramas.append(EntidadeHolograma(cena.jogador.x + 40, cena.jogador.y, modo="sombra", duracao=4.0))
            cena.hologramas.append(EntidadeHolograma(cena.jogador.x - 40, cena.jogador.y, modo="clone_agro", duracao=4.0))

            for frame in range(180):
                cena.jogador.hp = cena.jogador.hp_max
                if frame % 45 == 0:
                    estado_alvo = estados_musica[(frame // 45) % len(estados_musica)]
                    cena.sistema_musica.estado = estado_alvo
                    fases_musica_vistas.add(cena.sistema_musica.estado)
                    # Alterna arma especial entre SMGCompacta, RifleArco e LancaChamas
                    arma_esp = novas_armas[1 + ((frame // 45) % 3)]
                    arma_esp.municao_atual = max(10, arma_esp.municao_max)
                    cena.jogador.arma_especial = arma_esp
                    cena.jogador.slot_ativo = 3 if (frame // 45) % 2 == 1 else 1
                    cena.inimigos.append(InimigoPadrao(x=cena.jogador.x + 90, y=cena.jogador.y))

                cena.loop(dt=dt)
                cena.draw()
                total_frames += 1

            # --- FASE 2 (150 frames): Mini-Boss ativo e combate ---
            mini_boss = InimigoPadrao(
                x=cena.jogador.x + 140,
                y=cena.jogador.y,
                is_elite=True,
                nome_elite="MINI-BOSS: SMOKE TEST",
            )
            cena.inimigos.append(mini_boss)
            for _ in range(150):
                cena.jogador.hp = cena.jogador.hp_max
                cena.loop(dt=dt)
                cena.draw()
                total_frames += 1

            # --- FASE 3 (90 frames): Abertura, render e fechamento do MenuConquistas ---
            cena.menu_conquistas.abrir()
            self.assertTrue(cena.menu_conquistas.ativo)
            for frame in range(90):
                if frame == 45:
                    cena.menu_conquistas.aba_atual = 1  # Alterna para aba Firmware
                cena.loop(dt=dt)
                cena.draw()
                total_frames += 1
            cena.menu_conquistas.fechar()
            self.assertFalse(cena.menu_conquistas.ativo)

            # --- FASE 4 (240 frames): Geladeira Tsunami Boss (Cutscene -> FASE1 -> FASE2 -> FASE3) ---
            cena.jogador.nivel = 12
            cena.iniciar_boss_cutscene()
            for frame in range(240):
                cena.jogador.hp = cena.jogador.hp_max
                if frame == 5:
                    cena.boss_cutscene_timer = 2.0  # Whiteout -> Blackout
                elif frame == 10:
                    cena.boss_cutscene_timer = 1.0  # Blackout -> Musica In (spawna Boss)
                elif cena.chefe_final is not None and not cena.chefe_final.intro_concluida:
                    cena.chefe_final.intro_concluida = True
                    cena.chefe_final.estado = "fase1"
                elif frame == 100 and cena.chefe_final is not None:
                    cena.chefe_final.receber_dano(22000)  # <= 70% -> Fase 2
                elif frame == 170 and cena.chefe_final is not None:
                    cena.chefe_final.receber_dano(25000)  # <= 35% -> Fase 3

                cena.loop(dt=dt)
                cena.draw()
                total_frames += 1

        # Verificações finais
        self.assertGreaterEqual(total_frames, 660)
        self.assertEqual(
            fases_musica_vistas,
            {
                SistemaMusica.ESTADO_ANTICIPATION,
                SistemaMusica.ESTADO_HOLD,
                SistemaMusica.ESTADO_ASSAULT_INTRO,
                SistemaMusica.ESTADO_ASSAULT,
            },
        )
        self.assertIsNotNone(cena.chefe_final)
        self.assertEqual(
            len(font_calls),
            0,
            f"Alocação proibida de pygame.font.Font detectada durante o loop: {font_calls}",
        )
        self.assertEqual(
            len(sysfont_calls),
            0,
            f"Alocação proibida de pygame.font.SysFont detectada durante o loop: {sysfont_calls}",
        )
        self.assertEqual(
            len(open_calls),
            0,
            f"Operação proibida de I/O em disco (open) detectada durante o loop: {open_calls}",
        )


if __name__ == "__main__":
    unittest.main()
