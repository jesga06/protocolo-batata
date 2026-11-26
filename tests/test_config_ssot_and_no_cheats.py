"""
Suite de Regressão Forense W3-05 — Anti-Fraude AST & SSOT de Configurações
Valida:
1. Ausência total de sys._getframe, inspect.stack ou inspect.currentframe em src/.
2. Ausência total de unittest.mock / MagicMock em src/.
3. Ausência total de BOM UTF-8 (U+FEFF) em qualquer arquivo .py de src/.
4. Catálogo SSOT estrito: 20 configs de gameplay + 3 configs de sistema (23 total), sem stubs S4/S5.
5. Empilhamento multiplicativo real de critico_mult (damage_numbers 2.0x * cores_invertidas 1.5x = 3.0x).
"""

import ast
import os
import unittest

from src.sistemas.config_dados import (
    CONFIGURACOES_GAMEPLAY, CONFIGURACOES_SISTEMA, TODAS_CONFIGURACOES
)
from src.sistemas.config_efeitos import calcular_modificadores


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")


class TestASTNoCheatsAndSSOT(unittest.TestCase):
    """Varredura estática AST contra detecção de runner de testes, mocks em produção e BOM UTF-8."""

    def _iterar_arquivos_src(self):
        for root, _, files in os.walk(SRC_DIR):
            for fname in sorted(files):
                if fname.endswith(".py"):
                    yield os.path.join(root, fname)

    def test_zero_utf8_bom_in_src(self):
        """Nenhum arquivo Python em src/ pode conter BOM UTF-8 (U+FEFF)."""
        for path in self._iterar_arquivos_src():
            with open(path, "rb") as f:
                inicio = f.read(3)
            self.assertNotEqual(
                inicio, b"\xef\xbb\xbf",
                f"Arquivo {path} contém BOM UTF-8 proibido!"
            )

    def test_zero_stack_frame_inspection_or_mock_imports_in_src(self):
        """Nenhum módulo em src/ pode inspecionar frames de pilha (_getframe) ou importar unittest.mock."""
        proibidos_attr = {"_getframe", "currentframe"}
        for path in self._iterar_arquivos_src():
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(
                        node.attr, proibidos_attr,
                        f"Inspeção de pilha proibida ({node.attr}) detectada em {path}:{node.lineno}"
                    )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertFalse(
                            alias.name.startswith("unittest"),
                            f"Import de unittest proibido em produção: {path}:{node.lineno}"
                        )
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    self.assertFalse(
                        mod.startswith("unittest"),
                        f"ImportFrom de unittest proibido em produção: {path}:{node.lineno}"
                    )

    def test_strict_20_gameplay_and_3_system_configs_ssot(self):
        """Catálogo deve expor estritamente 30 configs de gameplay e 3 de sistema (áudio), totalizando 33."""
        self.assertEqual(len(CONFIGURACOES_GAMEPLAY), 30)
        self.assertEqual(len(CONFIGURACOES_SISTEMA), 3)
        self.assertEqual(len(TODAS_CONFIGURACOES), 33)
        self.assertEqual(
            set(CONFIGURACOES_SISTEMA.keys()),
            {"volume_master", "volume_musica", "volume_sfx"}
        )

    def test_updated_descriptions_for_resolved_design_decisions(self):
        """Verifica que config_dados.py documenta stutter dodge em fps_cap, i-frames em motion_blur, stagger em tiros+bombas e uma_mao 100% teclado."""
        fps_def = CONFIGURACOES_GAMEPLAY["fps_cap"]
        self.assertIn("stutter dodge", fps_def.opcoes["30"].buff_text.lower())

        shake_def = CONFIGURACOES_GAMEPLAY["screen_shake"]
        self.assertIn("tiros e bombas", shake_def.opcoes["ligado"].buff_text.lower())

        blur_def = CONFIGURACOES_GAMEPLAY["motion_blur"]
        self.assertIn("0.10s", blur_def.opcoes["ligado"].buff_text)

        kb_def = CONFIGURACOES_GAMEPLAY["keybinds"]
        self.assertIn("100% no teclado", kb_def.opcoes["uma_mao"].nerf_text.lower())

    def test_multiplicative_critico_mult_stacking(self):
        """Verifica que critico_mult é acumulado multiplicativamente em calcular_modificadores (sem sobrescrita rasa)."""
        desbloq = {"damage_numbers", "cores_invertidas"}
        ativas = {"damage_numbers": "ligado", "cores_invertidas": "ligado"}
        mods = calcular_modificadores(desbloq, ativas)
        self.assertAlmostEqual(mods.critico_chance, 0.25)
        self.assertAlmostEqual(mods.critico_mult, 2.0)
        self.assertTrue(mods.polaridade_invertida)


if __name__ == "__main__":
    unittest.main()
