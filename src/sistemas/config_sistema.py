"""
Gerenciador de Estado e Persistência de Configurações — Protocolo: Batata
SSOT: CONFIGURACOES.md
Gerencia o desbloqueio progressivo de configurações no Level-Up, seleção de valores ativos,
acesso a modificadores calculados e serialização para persistência em save.json.
"""

import json
from typing import Any, Optional
from src.sistemas.config_dados import (
    CONFIGURACOES_GAMEPLAY, CONFIGURACOES_SISTEMA, TODAS_CONFIGURACOES,
    ConfiguracaoDef, TipoControleConfig
)
from src.sistemas.config_efeitos import calcular_modificadores, ModificadoresGameplay


class GerenciadorConfiguracoes:
    """
    Controlador central de estado do sistema de configurações do jogo.
    """

    def __init__(self):
        self.desbloqueadas: set[str] = set()
        self.ativas: dict[str, Any] = {}
        self.sistema_configs: dict[str, Any] = {}
        self.estatisticas: dict[str, Any] = {
            "high_score": 0,
            "melhor_tempo": 0.0,
            "total_abates": 0,
            "partidas_jogadas": 0,
            "vitorias": 0,
            "historico": [],
            "parries_total": 0,
            "dash_desbloqueado": False
        }

        self._inicializar_padroes()

    def _inicializar_padroes(self):
        """Inicializa os valores de todas as configurações para seus padrões neutros."""
        for cid, cdef in CONFIGURACOES_GAMEPLAY.items():
            self.ativas[cid] = cdef.valor_padrao

        for cid, cdef in CONFIGURACOES_SISTEMA.items():
            self.sistema_configs[cid] = cdef.valor_padrao

    def desbloquear_config(self, config_id: str) -> bool:
        """
        Desbloqueia uma configuração de gameplay para personalização pelo jogador.
        Retorna True se foi um novo desbloqueio.
        """
        if config_id in CONFIGURACOES_GAMEPLAY and config_id not in self.desbloqueadas:
            self.desbloqueadas.add(config_id)
            return True
        return False

    def is_desbloqueada(self, config_id: str) -> bool:
        """Verifica se uma configuração está desbloqueada (configs de sistema são sempre True)."""
        if config_id in CONFIGURACOES_SISTEMA:
            return True
        return config_id in self.desbloqueadas

    @staticmethod
    def _validar_valor_config(cdef: ConfiguracaoDef, valor: Any) -> tuple[bool, Any]:
        """
        Valida se o valor é compatível com a definição da configuração.
        - Sliders: numérico (não booleano) entre 0 e 100.
        - Opções: valor deve constar em cdef.opcoes (ou string equivalente).
        Retorna (valido: bool, valor_normalizado: Any).
        """
        if cdef.tipo == TipoControleConfig.SLIDER:
            if isinstance(valor, (int, float)) and not isinstance(valor, bool) and 0 <= valor <= 100:
                return True, valor
            return False, None

        if cdef.opcoes:
            if valor in cdef.opcoes:
                return True, valor
            if isinstance(valor, (int, float)) and not isinstance(valor, bool) and str(valor) in cdef.opcoes:
                return True, str(valor)
            return False, None

        return True, valor

    def definir_valor(self, config_id: str, valor: Any) -> bool:
        """
        Define o valor ativo de uma configuração.
        Configurações de gameplay travadas não podem ter seu valor alterado.
        Valida se o valor é aceitável segundo a definição (opções válidas ou 0..100 para sliders).
        """
        if config_id in CONFIGURACOES_SISTEMA:
            cdef = CONFIGURACOES_SISTEMA[config_id]
            valido, val_norm = self._validar_valor_config(cdef, valor)
            if not valido:
                return False
            self.sistema_configs[config_id] = val_norm
            return True

        if config_id in CONFIGURACOES_GAMEPLAY:
            if config_id not in self.desbloqueadas:
                return False  # Travada no padrão neutro até desbloquear
            cdef = CONFIGURACOES_GAMEPLAY[config_id]
            valido, val_norm = self._validar_valor_config(cdef, valor)
            if not valido:
                return False
            self.ativas[config_id] = val_norm
            return True

        return False

    def obter_valor(self, config_id: str) -> Any:
        """
        Retorna o valor efetivo da configuração.
        Se estiver travada, retorna estritamente o valor padrão.
        """
        if config_id in CONFIGURACOES_SISTEMA:
            return self.sistema_configs.get(config_id, CONFIGURACOES_SISTEMA[config_id].valor_padrao)

        if config_id in CONFIGURACOES_GAMEPLAY:
            if config_id not in self.desbloqueadas:
                return CONFIGURACOES_GAMEPLAY[config_id].valor_padrao
            return self.ativas.get(config_id, CONFIGURACOES_GAMEPLAY[config_id].valor_padrao)

        return None

    def obter_modificadores(self) -> ModificadoresGameplay:
        """Retorna a estrutura consolidada de modificadores matemáticos calculados."""
        return calcular_modificadores(self.desbloqueadas, self.ativas)

    def obter_bloqueadas(self) -> list[ConfiguracaoDef]:
        """Retorna lista de definições de configurações ainda não desbloqueadas."""
        return [cdef for cid, cdef in CONFIGURACOES_GAMEPLAY.items() if cid not in self.desbloqueadas]

    def obter_desbloqueadas(self) -> list[ConfiguracaoDef]:
        """Retorna lista de definições de configurações já desbloqueadas."""
        return [cdef for cid, cdef in CONFIGURACOES_GAMEPLAY.items() if cid in self.desbloqueadas]

    def obter_estatisticas(self) -> dict:
        """Retorna as estatísticas históricas do jogador."""
        return dict(self.estatisticas)

    def registrar_partida(
        self,
        tempo: float,
        abates: int,
        pontos: int,
        vitoria: bool = False,
        dano_causado: int = 0
    ) -> dict:
        """
        Registra o resultado de uma partida concluída (derrota ou vitória),
        atualiza recordes históricos e persiste em disco.
        """
        novo_recorde_pontos = pontos > self.estatisticas.get("high_score", 0)
        novo_recorde_tempo = tempo > self.estatisticas.get("melhor_tempo", 0.0)

        self.estatisticas["partidas_jogadas"] = self.estatisticas.get("partidas_jogadas", 0) + 1
        self.estatisticas["total_abates"] = self.estatisticas.get("total_abates", 0) + int(abates)

        if vitoria:
            self.estatisticas["vitorias"] = self.estatisticas.get("vitorias", 0) + 1

        if novo_recorde_pontos:
            self.estatisticas["high_score"] = int(pontos)

        if novo_recorde_tempo:
            self.estatisticas["melhor_tempo"] = float(tempo)

        historico = self.estatisticas.setdefault("historico", [])
        registro = {
            "tempo": round(float(tempo), 2),
            "abates": int(abates),
            "pontos": int(pontos),
            "vitoria": bool(vitoria),
            "dano_causado": int(dano_causado),
            "desbloqueadas": len(self.desbloqueadas)
        }
        historico.append(registro)
        if len(historico) > 20:
            self.estatisticas["historico"] = historico[-20:]

        self.salvar_arquivo()

        return {
            "novo_recorde_pontos": novo_recorde_pontos,
            "novo_recorde_tempo": novo_recorde_tempo
        }

    def registrar_parry(self, meta: int = 50) -> tuple[int, bool]:
        """
        Incrementa o total histórico de parries, desbloqueia o Dash permanente ao atingir a meta,
        salva o progresso de forma segura e retorna (novo_total, acabou_de_desbloquear).
        """
        novo_total = int(self.estatisticas.get("parries_total", 0)) + 1
        self.estatisticas["parries_total"] = novo_total

        ja_desbloqueado = bool(self.estatisticas.get("dash_desbloqueado", False))
        acabou_de_desbloquear = False
        if not ja_desbloqueado and novo_total >= int(meta):
            self.estatisticas["dash_desbloqueado"] = True
            acabou_de_desbloquear = True

        self.salvar_arquivo()
        return (novo_total, acabou_de_desbloquear)

    def to_dict(self) -> dict:
        """Serializa o estado para dicionário JSON."""
        return {
            "desbloqueadas": sorted(list(self.desbloqueadas)),
            "ativas": {k: v for k, v in self.ativas.items()},
            "sistema_configs": {k: v for k, v in self.sistema_configs.items()},
            "estatisticas": {
                "high_score": int(self.estatisticas.get("high_score", 0)),
                "melhor_tempo": float(self.estatisticas.get("melhor_tempo", 0.0)),
                "total_abates": int(self.estatisticas.get("total_abates", 0)),
                "partidas_jogadas": int(self.estatisticas.get("partidas_jogadas", 0)),
                "vitorias": int(self.estatisticas.get("vitorias", 0)),
                "historico": list(self.estatisticas.get("historico", [])),
                "parries_total": int(self.estatisticas.get("parries_total", 0)),
                "dash_desbloqueado": bool(self.estatisticas.get("dash_desbloqueado", False))
            }
        }

    def from_dict(self, dados: dict) -> bool:
        """
        Restaura o estado a partir de um dicionário serializado.
        Operação atômica: valida e constrói todo o estado em estruturas temporárias
        antes de atualizar a instância. Em caso de falha ou dados inválidos, a instância
        não fica em estado corrompido.
        """
        if dados is None or not isinstance(dados, dict):
            return False

        try:
            temp_desbloqueadas: set[str] = set()
            temp_ativas: dict[str, Any] = {
                cid: cdef.valor_padrao for cid, cdef in CONFIGURACOES_GAMEPLAY.items()
            }
            temp_sistema: dict[str, Any] = {
                cid: cdef.valor_padrao for cid, cdef in CONFIGURACOES_SISTEMA.items()
            }
            temp_estatisticas: dict[str, Any] = {
                "high_score": 0,
                "melhor_tempo": 0.0,
                "total_abates": 0,
                "partidas_jogadas": 0,
                "vitorias": 0,
                "historico": [],
                "parries_total": 0,
                "dash_desbloqueado": False
            }

            # 1. Filtrar desbloqueadas estritamente contra CONFIGURACOES_GAMEPLAY
            if "desbloqueadas" in dados and isinstance(dados["desbloqueadas"], (list, set, tuple)):
                for item in dados["desbloqueadas"]:
                    if isinstance(item, str) and item in CONFIGURACOES_GAMEPLAY:
                        temp_desbloqueadas.add(item)

            # 2. Validar ativas contra opções válidas de gameplay
            if "ativas" in dados and isinstance(dados["ativas"], dict):
                for k, v in dados["ativas"].items():
                    if k in CONFIGURACOES_GAMEPLAY:
                        cdef = CONFIGURACOES_GAMEPLAY[k]
                        valido, val_norm = self._validar_valor_config(cdef, v)
                        if valido:
                            temp_ativas[k] = val_norm

            # 3. Validar configs de sistema (faixa 0..100 para sliders / opções válidas)
            if "sistema_configs" in dados and isinstance(dados["sistema_configs"], dict):
                for k, v in dados["sistema_configs"].items():
                    if k in CONFIGURACOES_SISTEMA:
                        cdef = CONFIGURACOES_SISTEMA[k]
                        valido, val_norm = self._validar_valor_config(cdef, v)
                        if valido:
                            temp_sistema[k] = val_norm

            # 4. Validar e sanitizar estatísticas com resiliência a tipos incorretos
            if "estatisticas" in dados and isinstance(dados["estatisticas"], dict):
                est = dados["estatisticas"]
                try:
                    temp_estatisticas["high_score"] = int(est.get("high_score", 0))
                except (TypeError, ValueError):
                    temp_estatisticas["high_score"] = 0

                try:
                    temp_estatisticas["melhor_tempo"] = float(est.get("melhor_tempo", 0.0))
                except (TypeError, ValueError):
                    temp_estatisticas["melhor_tempo"] = 0.0

                try:
                    temp_estatisticas["total_abates"] = int(est.get("total_abates", 0))
                except (TypeError, ValueError):
                    temp_estatisticas["total_abates"] = 0

                try:
                    temp_estatisticas["partidas_jogadas"] = int(est.get("partidas_jogadas", 0))
                except (TypeError, ValueError):
                    temp_estatisticas["partidas_jogadas"] = 0

                try:
                    temp_estatisticas["vitorias"] = int(est.get("vitorias", 0))
                except (TypeError, ValueError):
                    temp_estatisticas["vitorias"] = 0

                raw_hist = est.get("historico")
                if isinstance(raw_hist, list):
                    temp_estatisticas["historico"] = [
                        entry for entry in raw_hist if isinstance(entry, dict)
                    ]
                else:
                    temp_estatisticas["historico"] = []

                try:
                    raw_parries = est.get("parries_total", 0)
                    if isinstance(raw_parries, bool):
                        temp_estatisticas["parries_total"] = 0
                    else:
                        temp_estatisticas["parries_total"] = max(0, int(raw_parries))
                except (TypeError, ValueError):
                    temp_estatisticas["parries_total"] = 0

                temp_estatisticas["dash_desbloqueado"] = bool(est.get("dash_desbloqueado", False))

            # Atualização atômica do estado da instância
            self.desbloqueadas = temp_desbloqueadas
            self.ativas = temp_ativas
            self.sistema_configs = temp_sistema
            self.estatisticas = temp_estatisticas
            return True

        except Exception:
            return False

    def salvar_arquivo(self, caminho: Optional[str] = None) -> bool:
        """Salva o estado serializado em arquivo JSON usando gravação atômica."""
        if caminho is None:
            from src.utils.constantes import SAVE_FILE_PATH
            caminho = SAVE_FILE_PATH
        temp_path = None
        try:
            import os
            import tempfile
            if not isinstance(caminho, str) or not caminho.strip():
                return False
            # Bloqueia caminhos inválidos de drives no POSIX (ex: "Z:\\...")
            if os.name != "nt" and len(caminho) > 1 and caminho[1] == ":" and caminho[0].isalpha():
                return False

            caminho_abs = os.path.abspath(caminho)
            dir_path = os.path.dirname(caminho_abs)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            with tempfile.NamedTemporaryFile("w", dir=dir_path, delete=False, encoding="utf-8") as tf:
                temp_path = tf.name
                json.dump(self.to_dict(), tf, indent=2, ensure_ascii=False)
                tf.flush()
                os.fsync(tf.fileno())

            os.replace(temp_path, caminho_abs)
            return True
        except Exception:
            if temp_path is not None:
                try:
                    import os
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except (OSError, IOError):
                    pass
            return False

    def salvar_progresso(self, caminho: Optional[str] = None) -> bool:
        """Alias para salvar_arquivo."""
        return self.salvar_arquivo(caminho)

    def carregar_arquivo(self, caminho: Optional[str] = None) -> bool:
        """Carrega o estado a partir de um arquivo JSON."""
        if caminho is None:
            from src.utils.constantes import SAVE_FILE_PATH
            caminho = SAVE_FILE_PATH
        try:
            import os
            if os.path.isfile(caminho):
                with open(caminho, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                if isinstance(dados, dict):
                    return self.from_dict(dados)
        except (OSError, IOError, json.JSONDecodeError, UnicodeDecodeError):
            pass
        return False

