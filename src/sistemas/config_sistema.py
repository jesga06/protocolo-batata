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
    ConfiguracaoDef
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

    def definir_valor(self, config_id: str, valor: Any) -> bool:
        """
        Define o valor ativo de uma configuração.
        Configurações de gameplay travadas não podem ter seu valor alterado.
        """
        if config_id in CONFIGURACOES_SISTEMA:
            self.sistema_configs[config_id] = valor
            return True

        if config_id in CONFIGURACOES_GAMEPLAY:
            if config_id not in self.desbloqueadas:
                return False  # Travada no padrão neutro até desbloquear
            self.ativas[config_id] = valor
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

    def to_dict(self) -> dict:
        """Serializa o estado para dicionário JSON."""
        return {
            "desbloqueadas": sorted(list(self.desbloqueadas)),
            "ativas": {k: v for k, v in self.ativas.items()},
            "sistema_configs": {k: v for k, v in self.sistema_configs.items()}
        }

    def from_dict(self, dados: dict):
        """Restaura o estado a partir de um dicionário serializado."""
        if not dados or not isinstance(dados, dict):
            return

        self._inicializar_padroes()

        if "desbloqueadas" in dados and isinstance(dados["desbloqueadas"], (list, set)):
            self.desbloqueadas = set(dados["desbloqueadas"])

        if "ativas" in dados and isinstance(dados["ativas"], dict):
            for k, v in dados["ativas"].items():
                if k in CONFIGURACOES_GAMEPLAY:
                    self.ativas[k] = v

        if "sistema_configs" in dados and isinstance(dados["sistema_configs"], dict):
            for k, v in dados["sistema_configs"].items():
                if k in CONFIGURACOES_SISTEMA:
                    self.sistema_configs[k] = v

    def salvar_arquivo(self, caminho: Optional[str] = None) -> bool:
        """Salva o estado serializado em arquivo JSON."""
        if caminho is None:
            from src.utils.constantes import SAVE_FILE_PATH
            caminho = SAVE_FILE_PATH
        try:
            import os
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

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
                self.from_dict(dados)
                return True
        except Exception:
            pass
        return False
