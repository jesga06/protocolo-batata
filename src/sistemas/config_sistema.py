"""
Gerenciador de Estado e Persistência de Configurações — Protocolo: Batata
SSOT: CONFIGURACOES.md
Gerencia o desbloqueio progressivo de configurações no Level-Up, seleção de valores ativos,
exclusividade mútua, conquistas, loadout e serialização limpa no schema v2 em save.json.
"""

import json
from typing import Any, Optional
from src.sistemas.config_dados import (
    CONFIGURACOES_GAMEPLAY,
    CONFIGURACOES_SISTEMA,
    ConfiguracaoDef,
    TipoControleConfig,
)
from src.sistemas.config_efeitos import calcular_modificadores, ModificadoresGameplay
from src.sistemas.sistema_conquistas import SistemaConquistas

SCHEMA_VERSION_ATUAL = 2

ARMAS_LOADOUT_SLOT1 = {"chave_manutencao", "bastao_choque"}
ARMAS_LOADOUT_SLOT2 = {"pistola", "smg_compacta"}
ARMAS_LOADOUT_INICIAIS = {"chave_manutencao", "pistola"}


class GerenciadorConfiguracoes:
    """
    Controlador central de estado do sistema de configurações, conquistas e loadout do jogo.
    """

    def __init__(self):
        self.desbloqueadas: set[str] = set()
        self.ativas: dict[str, Any] = {}
        self.sistema_configs: dict[str, Any] = {}
        self.loadout: dict[str, str] = {
            "slot1": "chave_manutencao",
            "slot2": "pistola",
        }
        self.ultimos_conflitos_resolvidos: list[tuple[str, str]] = []
        self.sistema_conquistas: SistemaConquistas = SistemaConquistas()
        self.estatisticas: dict[str, Any] = self._criar_estatisticas_padrao()

        self._inicializar_padroes()

    @staticmethod
    def _criar_estatisticas_padrao() -> dict[str, Any]:
        return {
            "high_score": 0,
            "melhor_tempo": 0.0,
            "total_abates": 0,
            "partidas_jogadas": 0,
            "vitorias": 0,
            "historico": [],
            "parries_total": 0,
            "dash_desbloqueado": False,
        }

    def _inicializar_padroes(self):
        """Inicializa os valores de todas as configurações para seus padrões neutros."""
        for cid, cdef in CONFIGURACOES_GAMEPLAY.items():
            self.ativas[cid] = cdef.valor_padrao

        for cid, cdef in CONFIGURACOES_SISTEMA.items():
            self.sistema_configs[cid] = cdef.valor_padrao

    def _resetar_para_v2_limpo(self) -> None:
        """Reinicializa todo o estado para os defaults limpos do schema v2."""
        self.desbloqueadas = set()
        self.ativas = {}
        self.sistema_configs = {}
        self.loadout = {"slot1": "chave_manutencao", "slot2": "pistola"}
        self.ultimos_conflitos_resolvidos = []
        self.sistema_conquistas = SistemaConquistas()
        self.estatisticas = self._criar_estatisticas_padrao()
        self._inicializar_padroes()

    def sincronizar_recompensas_conquistas(self) -> None:
        """Sincroniza configurações e estatísticas derivadas de conquistas."""
        for cid in self.sistema_conquistas.recompensas.get("configuracao", set()):
            if cid in CONFIGURACOES_GAMEPLAY:
                self.desbloqueadas.add(cid)
        self.estatisticas["dash_desbloqueado"] = (
            self.sistema_conquistas.possui_recompensa("habilidade", "dash")
        )

    def desbloquear_config(self, config_id: str, via_conquista: bool = False) -> bool:
        """
        Desbloqueia uma configuração de gameplay para personalização pelo jogador.
        Configurações com exclusiva_conquista=True só desbloqueiam via_conquista=True.
        Retorna True se foi um novo desbloqueio.
        """
        if config_id not in CONFIGURACOES_GAMEPLAY:
            return False
        cdef = CONFIGURACOES_GAMEPLAY[config_id]
        if cdef.exclusiva_conquista and not via_conquista:
            return False
        if config_id not in self.desbloqueadas:
            self.desbloqueadas.add(config_id)
            return True
        return False

    def is_desbloqueada(self, config_id: str) -> bool:
        """Verifica se uma configuração está desbloqueada (configs de sistema são sempre True)."""
        if config_id in CONFIGURACOES_SISTEMA:
            return True
        if config_id not in CONFIGURACOES_GAMEPLAY:
            return False
        cdef = CONFIGURACOES_GAMEPLAY[config_id]
        if cdef.exclusiva_conquista:
            return (
                self.sistema_conquistas.possui_recompensa("configuracao", config_id)
                or config_id in self.desbloqueadas
            )
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

    def definir_valor_com_conflitos(
        self, config_id: str, valor: Any
    ) -> tuple[bool, list[tuple[str, str]]]:
        """
        Define o valor ativo de uma configuração, valida desbloqueio de opção
        (desbloqueada_por) e resolve automaticamente exclusividade mútua
        (incompativel_com), retornando (sucesso, lista_conflitos_revertidos).
        """
        if config_id in CONFIGURACOES_SISTEMA:
            cdef = CONFIGURACOES_SISTEMA[config_id]
            valido, val_norm = self._validar_valor_config(cdef, valor)
            if not valido:
                return False, []
            self.sistema_configs[config_id] = val_norm
            return True, []

        if config_id in CONFIGURACOES_GAMEPLAY:
            if not self.is_desbloqueada(config_id):
                return False, []
            cdef = CONFIGURACOES_GAMEPLAY[config_id]
            valido, val_norm = self._validar_valor_config(cdef, valor)
            if not valido:
                return False, []

            opcao = cdef.opcoes.get(str(val_norm))
            if opcao and opcao.desbloqueada_por:
                if ":" in opcao.desbloqueada_por:
                    tipo, rid = opcao.desbloqueada_por.split(":", 1)
                    if not self.sistema_conquistas.possui_recompensa(tipo, rid):
                        return False, []

            self.ativas[config_id] = val_norm

            conflitos: list[tuple[str, str]] = []
            if opcao and opcao.incompativel_com:
                for cid_conf, val_conf in opcao.incompativel_com:
                    if cid_conf in CONFIGURACOES_GAMEPLAY and self.ativas.get(cid_conf) == val_conf:
                        val_neutro = CONFIGURACOES_GAMEPLAY[cid_conf].valor_padrao
                        self.ativas[cid_conf] = val_neutro
                        conflitos.append((cid_conf, str(val_neutro)))

            self.ultimos_conflitos_resolvidos = conflitos
            return True, conflitos

        return False, []

    def definir_valor(self, config_id: str, valor: Any) -> bool:
        """
        Define o valor ativo de uma configuração.
        Preserva assinatura booleana delegando para definir_valor_com_conflitos.
        """
        ok, _ = self.definir_valor_com_conflitos(config_id, valor)
        return ok

    def obter_valor(self, config_id: str) -> Any:
        """
        Retorna o valor efetivo da configuração.
        Se estiver travada, retorna estritamente o valor padrão.
        """
        if config_id in CONFIGURACOES_SISTEMA:
            return self.sistema_configs.get(config_id, CONFIGURACOES_SISTEMA[config_id].valor_padrao)

        if config_id in CONFIGURACOES_GAMEPLAY:
            if not self.is_desbloqueada(config_id):
                return CONFIGURACOES_GAMEPLAY[config_id].valor_padrao
            return self.ativas.get(config_id, CONFIGURACOES_GAMEPLAY[config_id].valor_padrao)

        return None

    def obter_modificadores(self) -> ModificadoresGameplay:
        """Retorna a estrutura consolidada de modificadores matemáticos calculados."""
        efetivas_desbloqueadas = {
            cid for cid in CONFIGURACOES_GAMEPLAY if self.is_desbloqueada(cid)
        }
        return calcular_modificadores(efetivas_desbloqueadas, self.ativas)

    def obter_configs_bloqueadas_level_up(self) -> list[ConfiguracaoDef]:
        """
        Retorna configurações elegíveis para o pool aleatório de Level-Up:
        exclui estritamente configs já desbloqueadas, configs com exclusiva_conquista=True
        e configs cujo requer_desbloqueio ainda não foi conquistado.
        """
        elegiveis: list[ConfiguracaoDef] = []
        for cdef in CONFIGURACOES_GAMEPLAY.values():
            if self.is_desbloqueada(cdef.id):
                continue
            if cdef.exclusiva_conquista:
                continue
            if cdef.requer_desbloqueio is not None:
                tipo, rid = cdef.requer_desbloqueio
                if not self.sistema_conquistas.possui_recompensa(tipo, rid):
                    continue
            elegiveis.append(cdef)
        return elegiveis

    def obter_bloqueadas(self, incluir_exclusivas_conquista: bool = False) -> list[ConfiguracaoDef]:
        """
        Retorna lista de definições de configurações ainda não desbloqueadas.
        Por padrão (incluir_exclusivas_conquista=False) protege o pool do ModalLevelUp.
        """
        if not incluir_exclusivas_conquista:
            return self.obter_configs_bloqueadas_level_up()
        return [
            cdef for cid, cdef in CONFIGURACOES_GAMEPLAY.items()
            if not self.is_desbloqueada(cid)
        ]

    def obter_desbloqueadas(self) -> list[ConfiguracaoDef]:
        """Retorna lista de definições de configurações já desbloqueadas."""
        return [
            cdef for cid, cdef in CONFIGURACOES_GAMEPLAY.items()
            if self.is_desbloqueada(cid)
        ]

    def definir_loadout(self, slot: str, arma_id: str) -> bool:
        """Define a arma equipada no Slot 1 ou Slot 2 validando desbloqueio."""
        if slot == "slot1" and arma_id in ARMAS_LOADOUT_SLOT1:
            if arma_id in ARMAS_LOADOUT_INICIAIS or self.sistema_conquistas.possui_recompensa("arma", arma_id):
                self.loadout["slot1"] = arma_id
                return True
            return False
        if slot == "slot2" and arma_id in ARMAS_LOADOUT_SLOT2:
            if arma_id in ARMAS_LOADOUT_INICIAIS or self.sistema_conquistas.possui_recompensa("arma", arma_id):
                self.loadout["slot2"] = arma_id
                return True
            return False
        return False

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

    def registrar_parry(self, meta: int | None = None) -> tuple[int, bool]:
        """
        Registra um parry via SistemaConquistas, sincroniza estatísticas e
        salva em disco SOMENTE quando houver desbloqueio novo (zero I/O em parries normais).
        """
        notifs = self.sistema_conquistas.registrar_evento("parry", 1)
        self.sincronizar_recompensas_conquistas()

        novo_total = int(
            self.sistema_conquistas.continuas.get("mestre_chave_inglesa", {}).get("valor", 0)
        )
        self.estatisticas["parries_total"] = novo_total
        dash_desb = self.sistema_conquistas.possui_recompensa("habilidade", "dash")
        self.estatisticas["dash_desbloqueado"] = dash_desb

        acabou_de_desbloquear = any(
            any(t == "habilidade" and r == "dash" for t, r in n.get("recompensas", []))
            for n in notifs
        )

        if notifs:
            self.salvar_arquivo()

        return (novo_total, acabou_de_desbloquear)

    def to_dict(self) -> dict:
        """Serializa o estado para dicionário JSON no schema v2."""
        return {
            "schema_version": SCHEMA_VERSION_ATUAL,
            "desbloqueadas": sorted(list(self.desbloqueadas)),
            "ativas": {k: v for k, v in self.ativas.items()},
            "sistema_configs": {k: v for k, v in self.sistema_configs.items()},
            "loadout": {
                "slot1": self.loadout.get("slot1", "chave_manutencao"),
                "slot2": self.loadout.get("slot2", "pistola"),
            },
            "estatisticas": {
                "high_score": int(self.estatisticas.get("high_score", 0)),
                "melhor_tempo": float(self.estatisticas.get("melhor_tempo", 0.0)),
                "total_abates": int(self.estatisticas.get("total_abates", 0)),
                "partidas_jogadas": int(self.estatisticas.get("partidas_jogadas", 0)),
                "vitorias": int(self.estatisticas.get("vitorias", 0)),
                "historico": list(self.estatisticas.get("historico", [])),
                "parries_total": int(self.estatisticas.get("parries_total", 0)),
                "dash_desbloqueado": bool(self.estatisticas.get("dash_desbloqueado", False)),
            },
            "progresso_conquistas": self.sistema_conquistas.to_dict(),
        }

    def from_dict(self, dados: dict) -> bool:
        """
        Restaura o estado a partir de um dicionário serializado (schema v2).
        Saves sem schema_version == 2 ou {} reinicializam de forma limpa no schema v2 e retornam True.
        """
        if dados is None or not isinstance(dados, dict):
            return False

        if dados == {} or dados.get("schema_version") != SCHEMA_VERSION_ATUAL:
            self._resetar_para_v2_limpo()
            return True

        try:
            temp_desbloqueadas: set[str] = set()
            temp_ativas: dict[str, Any] = {
                cid: cdef.valor_padrao for cid, cdef in CONFIGURACOES_GAMEPLAY.items()
            }
            temp_sistema: dict[str, Any] = {
                cid: cdef.valor_padrao for cid, cdef in CONFIGURACOES_SISTEMA.items()
            }
            temp_estatisticas = self._criar_estatisticas_padrao()
            temp_conquistas = SistemaConquistas()

            if "progresso_conquistas" in dados and isinstance(dados["progresso_conquistas"], dict):
                temp_conquistas.from_dict(dados["progresso_conquistas"])

            # 1. Filtrar desbloqueadas estritamente contra CONFIGURACOES_GAMEPLAY
            if "desbloqueadas" in dados and isinstance(dados["desbloqueadas"], (list, set, tuple)):
                for item in dados["desbloqueadas"]:
                    if isinstance(item, str) and item in CONFIGURACOES_GAMEPLAY:
                        cdef = CONFIGURACOES_GAMEPLAY[item]
                        if not cdef.exclusiva_conquista or temp_conquistas.possui_recompensa("configuracao", item):
                            temp_desbloqueadas.add(item)

            for cid in temp_conquistas.recompensas.get("configuracao", set()):
                if cid in CONFIGURACOES_GAMEPLAY:
                    temp_desbloqueadas.add(cid)

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

            # 4. Validar loadout
            temp_loadout = {"slot1": "chave_manutencao", "slot2": "pistola"}
            if "loadout" in dados and isinstance(dados["loadout"], dict):
                s1 = dados["loadout"].get("slot1")
                s2 = dados["loadout"].get("slot2")
                if isinstance(s1, str) and s1 in ARMAS_LOADOUT_SLOT1:
                    if s1 in ARMAS_LOADOUT_INICIAIS or temp_conquistas.possui_recompensa("arma", s1):
                        temp_loadout["slot1"] = s1
                if isinstance(s2, str) and s2 in ARMAS_LOADOUT_SLOT2:
                    if s2 in ARMAS_LOADOUT_INICIAIS or temp_conquistas.possui_recompensa("arma", s2):
                        temp_loadout["slot2"] = s2

            # 5. Validar e sanitizar estatísticas
            if "estatisticas" in dados and isinstance(dados["estatisticas"], dict):
                est = dados["estatisticas"]
                for key, cast_fn, default in (
                    ("high_score", int, 0),
                    ("melhor_tempo", float, 0.0),
                    ("total_abates", int, 0),
                    ("partidas_jogadas", int, 0),
                    ("vitorias", int, 0),
                ):
                    try:
                        temp_estatisticas[key] = cast_fn(est.get(key, default))
                    except (TypeError, ValueError):
                        temp_estatisticas[key] = default

                raw_hist = est.get("historico")
                if isinstance(raw_hist, list):
                    temp_estatisticas["historico"] = [
                        entry for entry in raw_hist if isinstance(entry, dict)
                    ]

                try:
                    raw_parries = est.get("parries_total", 0)
                    if isinstance(raw_parries, bool):
                        temp_estatisticas["parries_total"] = 0
                    else:
                        temp_estatisticas["parries_total"] = max(0, int(raw_parries))
                except (TypeError, ValueError):
                    temp_estatisticas["parries_total"] = 0

                temp_estatisticas["dash_desbloqueado"] = bool(
                    est.get("dash_desbloqueado", False)
                    or temp_conquistas.possui_recompensa("habilidade", "dash")
                )

            # Atualização atômica do estado da instância
            self.desbloqueadas = temp_desbloqueadas
            self.ativas = temp_ativas
            self.sistema_configs = temp_sistema
            self.loadout = temp_loadout
            self.estatisticas = temp_estatisticas
            self.sistema_conquistas = temp_conquistas
            self.ultimos_conflitos_resolvidos = []
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
        """
        Carrega o estado a partir de um arquivo JSON.
        Saves legados (sem schema_version == 2) são sobrescritos de forma limpa no schema v2.
        """
        if caminho is None:
            from src.utils.constantes import SAVE_FILE_PATH
            caminho = SAVE_FILE_PATH
        try:
            import os
            if os.path.isfile(caminho):
                with open(caminho, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                if isinstance(dados, dict):
                    era_v2 = dados.get("schema_version") == SCHEMA_VERSION_ATUAL
                    ok = self.from_dict(dados)
                    if ok and not era_v2:
                        self.salvar_arquivo(caminho)
                    return ok
        except (OSError, IOError, json.JSONDecodeError, UnicodeDecodeError):
            pass
        return False
