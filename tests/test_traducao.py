"""Testes unitários e validação estrutural do sistema de tradução (i18n)."""

import ast
import json
import os
import pathlib
import string
import unittest

from src.utils import traducao


class TestTraducao(unittest.TestCase):
    def setUp(self):
        traducao.recarregar_traducoes() if os.path.isdir(
            os.path.join(traducao.LOCALES_DIR, traducao.IDIOMA_PADRAO)
        ) else None

    def test_todas_categorias_seguem_schema_contexto_e_placeholders(self):
        pasta = os.path.join(traducao.LOCALES_DIR, traducao.IDIOMA_PADRAO)
        if not os.path.isdir(pasta):
            self.skipTest("Diretório pt_BR ainda não populado.")

        arquivos = sorted(f for f in os.listdir(pasta) if f.endswith(".json"))
        self.assertGreater(len(arquivos), 0)

        formatador = string.Formatter()
        for nome in arquivos:
            caminho = os.path.join(pasta, nome)
            with open(caminho, "r", encoding="utf-8") as arq:
                dados = json.load(arq)

            with self.subTest(arquivo=nome):
                self.assertIn("_meta", dados)
                self.assertIn("placeholders_disponiveis", dados["_meta"])
                self.assertIn("entradas", dados)
                if nome == "dicas.json":
                    self.assertIn("condicoes_disponiveis", dados["_meta"])

                for chave, entrada in dados["entradas"].items():
                    self.assertIn("texto", entrada, f"{nome}:{chave} sem 'texto'")
                    self.assertIn("contexto", entrada, f"{nome}:{chave} sem 'contexto'")
                    self.assertTrue(entrada["contexto"].strip(), f"{nome}:{chave} contexto vazio")
                    self.assertIn("placeholders", entrada, f"{nome}:{chave} sem 'placeholders'")
                    if nome == "dicas.json":
                        self.assertIn("condicoes", entrada, f"{nome}:{chave} sem 'condicoes'")

                    campos_texto = {
                        fname
                        for _, fname, _, _ in formatador.parse(entrada["texto"])
                        if fname is not None
                    }
                    campos_doc = set(entrada["placeholders"].keys())
                    self.assertEqual(
                        campos_texto,
                        campos_doc,
                        f"{nome}:{chave} placeholders no texto {campos_texto} != documentados {campos_doc}",
                    )

    def test_zero_strings_hardcoded_exibidas_ao_usuario_em_src(self):
        ignores = {
            "Arial", "Consolas", "Courier New", "DejaVu Sans", "DejaVu Sans Mono",
            "jetbrainsmono", "firacode", "consolas", "dejavusansmono",
            "notosans", "dejavusans", "liberationsans", "arial",
            "Performance", "Interface", "Controles", "Dificuldade", "Experimental", "Sistema",
            "Toggle", "Grupo", "Slider", "Seletor", "TODAS",
            "Todas", "Contínuas", "Únicas", "Fixadas",
            "Ofensivo", "Defensivo", "Tático", "Mobilidade", "Economia",
            "LEFT", "RIGHT", "UP", "DOWN", "ESC", "ENTER", "RETURN", "SPACE", "TAB", "LSHIFT", "GRAVE",
            "KP1", "KP2", "KP3", "KP_1", "KP_2", "KP_3", "KP_4", "KP_6", "KP4", "KP6", "F1",
            "Ligado", "Nenhum", "ProtocoloBatata", "UTF-8", "utf-8", "RGBA", "RGB",
            "SDL_VIDEODRIVER", "SDL_AUDIODRIVER", "APPDATA", "XDG_DATA_HOME",
            "SAVE_FILE_PATH", "CINZA_TEXTO", "bastão", "Bastão", "rifle de arco", "lança-chamas",
            "~/Library/Application Support/", "Tecla: ",
        }
        erros_dev_arquivos = {"sistema_audio.py", "banner_dicas.py", "constantes.py", "traducao.py"}
        violacoes = []
        src_root = pathlib.Path(traducao._PROJECT_ROOT) / "src"
        for p in sorted(src_root.rglob("*.py")):
            tree = ast.parse(p.read_text(encoding="utf-8"))
            doc_nodes = set()
            print_str_nodes = set()
            for n in ast.walk(tree):
                if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    for stmt in n.body[:2]:
                        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                            doc_nodes.add(stmt.value)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print":
                    for sub in ast.walk(n):
                        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                            print_str_nodes.add(sub)
            for n in ast.walk(tree):
                if n in doc_nodes or n in print_str_nodes:
                    continue
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value.strip()) > 1:
                    v = n.value
                    if v in ignores or "assets/" in v or v.endswith((".png", ".wav", ".json")) or v.startswith("#"):
                        continue
                    if p.name in erros_dev_arquivos and ("Condição" in v or "Sintaxe" in v or "Argumentos" in v or "Especificação" in v or "Largura de amostra" in v or "bytes em" in v or "Asset '" in v or "não encontrado" in v or "Localização" in v or "localização" in v or "Placeholder" in v or "Categoria" in v or "Chave" in v or "Diretório" in v):
                        continue
                    if any(acc in v for acc in "áéíóúãõçÁÉÍÓÚÃÕÇ") or (" " in v and any(c.isalpha() for c in v)):
                        violacoes.append(f"{p.relative_to(src_root)}:{n.lineno}: {v!r}")
        self.assertEqual(violacoes, [], f"Strings hardcoded detectadas em src/: {violacoes}")


if __name__ == "__main__":
    unittest.main()
