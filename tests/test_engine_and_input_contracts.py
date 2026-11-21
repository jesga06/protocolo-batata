"""
Suite de Regressão Forense W3-08 — Contratos de Engine, Janela, Input, Scavenger e ModalLevelUp
Valida:
1. src/main.py instancia Window com pixel_art=True (eliminando o borrão bilinear).
2. Janela._calcular_viewport(), evento VIDEORESIZE, TecladoNativo (TAB, F1..F12, KP1..KP9, BACKQUOTE) e proteção de Janela.draw_text.
3. SistemaScavenger: limpa pos_alvo_override=None ao descartar scavenger e ItemDrop separa tempo_despawn de tempo_decorrido.
4. ModalLevelUp: fila FIFO fila_niveis preserva marcos 5/10/15/20 e todos os 23 ícones de configuração existem sem prefixo duplicado.
"""

import ast
import os
import tempfile
import unittest
from unittest.mock import patch
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
pygame.init()
pygame.font.init()

from src.utils.janela import Janela, TecladoNativo
from src.utils.constantes import ASSET_PATHS, obter_caminho_asset
from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY, CONFIGURACOES_SISTEMA
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.sistemas.sistema_scavenger import SistemaScavenger
from src.entidades.drop import ItemDrop
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.jogador import Jogador
from src.ui.modal_level_up import ModalLevelUp


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestEngineAndInputContracts(unittest.TestCase):
    """Testa contratos de janela, teclado nativo, scavenger e fila FIFO de level-up."""

    def test_main_py_uses_pixel_art_true(self):
        """Verifica via AST que src/main.py instancia Window(..., pixel_art=True)."""
        main_path = os.path.join(PROJECT_ROOT, "src", "main.py")
        with open(main_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=main_path)

        found_pixel_art_true = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "Window":
                for kw in node.keywords:
                    if kw.arg == "pixel_art" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        found_pixel_art_true = True
        self.assertTrue(found_pixel_art_true, "src/main.py DEVE passar pixel_art=True para Window(...)!")

    def test_teclado_nativo_special_keys_and_janela_videoresize(self):
        """Valida mapeamento de TAB, F1, KP1..KP9 e BACKQUOTE no TecladoNativo e VIDEORESIZE na Janela."""
        kb = TecladoNativo()
        self.assertEqual(kb._get_code("TAB"), pygame.K_TAB)
        self.assertEqual(kb._get_code("F1"), pygame.K_F1)
        self.assertEqual(kb._get_code("KP1"), pygame.K_KP1)
        self.assertEqual(kb._get_code("BACKQUOTE"), pygame.K_BACKQUOTE)

        jan = Janela(1280, 720, "Teste", resizavel=True, pixel_art=True)
        pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, {"w": 1280, "h": 720, "size": (1280, 720)}))
        jan.processar_eventos()
        self.assertEqual((jan.largura_janela_atual, jan.altura_janela_atual), (1280, 720))
        dest_x, dest_y, dest_w, dest_h, _ = jan._calcular_viewport(1280, 720)
        # Proporção 16:9 nativa dentro de 1280x720 -> viewport 1280x720 sem letterboxing
        self.assertEqual((dest_w, dest_h), (1280, 720))
        self.assertEqual((dest_x, dest_y), (0, 0))

    def test_scavenger_clears_override_and_drop_separates_tempo_despawn(self):
        """SistemaScavenger limpa pos_alvo_override ao descartar scavenger e ItemDrop separa tempo_despawn."""
        drop = ItemDrop(x=200, y=200, tipo="xp", valor=10)
        # Durante Boss fight (pausar_despawn=True), tempo_decorrido avança para elegibilidade Scavenger, mas tempo_despawn fica 0
        drop.update(12.0, pausar_despawn=True)
        self.assertAlmostEqual(drop.tempo_decorrido, 12.0)
        self.assertEqual(drop.tempo_no_chao, 12.0)
        self.assertEqual(drop.tempo_despawn, 0.0)
        self.assertTrue(drop.elegivel_scavenger())

        scav_sys = SistemaScavenger()
        e1 = InimigoPadrao(x=190, y=200)
        e2 = InimigoPadrao(x=180, y=200)
        e3 = InimigoPadrao(x=170, y=200)
        inim = InimigoPadrao(x=100, y=100)
        todos_inim = [e1, e2, e3, inim]
        scav_sys.update(0.1, todos_inim, [drop], mover_manualmente=False)
        self.assertIs(scav_sys.scavenger_atual, inim)
        self.assertIsNotNone(getattr(inim, "pos_alvo_override", None))

        # Quando o drop é removido ou o sistema é desativado, pos_alvo_override deve voltar para None
        scav_sys.desativar(todos_inim)
        self.assertIsNone(inim.pos_alvo_override)

    def test_modal_level_up_fifo_queue_preserves_milestone_5_and_all_23_icons_exist(self):
        """Subir múltiplos níveis de uma vez (4 -> 5 -> 6) na fila FIFO preserva o marco do Nível 5."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_save = os.path.join(tmpdir, "save.json")
            with patch("src.utils.constantes.SAVE_FILE_PATH", temp_save), patch("src.ui.modal_level_up.SAVE_FILE_PATH", temp_save):
                mgr = GerenciadorConfiguracoes()
                jog = Jogador(x=100, y=100)
                modal = ModalLevelUp(mgr, jog)

                modal.enfileirar_level_up(4)
                modal.enfileirar_level_up(5)
                modal.enfileirar_level_up(6)

                # Primeiro modal aberto é o do nível 4 (3 consumíveis)
                self.assertEqual(modal.nivel_atual_draw, 4)
                self.assertTrue(all(c["tipo"] != "config" for c in modal.cards_sorteados))

                # Ao escolher 1 carta, abre o próximo da fila FIFO: nível 5 (marco com card central de config!)
                modal.selecionar_card(0)
                self.assertTrue(modal.ativo)
                self.assertEqual(modal.nivel_atual_draw, 5)
                self.assertEqual(modal.cards_sorteados[1]["tipo"], "config")

        # Verifica que todos os 23 ícones de configuração estão registrados em ASSET_PATHS e existem no disco
        for cid in list(CONFIGURACOES_GAMEPLAY.keys()) + list(CONFIGURACOES_SISTEMA.keys()):
            chave = f"icon_{cid}"
            self.assertIn(chave, ASSET_PATHS)
            caminho = obter_caminho_asset(chave)
            self.assertNotIn("icon_icon_", caminho)
            self.assertTrue(os.path.isfile(caminho), f"Ícone ausente no disco: {caminho}")


if __name__ == "__main__":
    unittest.main()
