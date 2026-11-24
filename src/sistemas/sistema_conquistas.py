"""
Sistema de Conquistas & Chips de Firmware — Protocolo: Batata
Gerencia conquistas contínuas, únicas, pins da HUD (0..3), recompensas permanentes
e slots de Chips de Firmware (1..3). Zero imports de src/armas/ ou src/cenas/.
"""

from typing import Any
from src.sistemas.conquistas_dados import (
    CHIPS_FIRMWARE,
    CONQUISTAS_CONTINUAS,
    CONQUISTAS_UNICAS,
)

TIPOS_RECOMPENSA_VALIDOS = (
    "habilidade",
    "configuracao",
    "opcao_config",
    "modificador_run",
    "arma",
    "trofeu",
)


class SistemaConquistas:
    """Controlador de progresso de conquistas, recompensas permanentes e firmware."""

    def __init__(self):
        self.unicas_concluidas: set[str] = set()
        self.continuas: dict[str, dict[str, Any]] = {
            cid: {"valor": 0, "milestones_concluidos": []}
            for cid in CONQUISTAS_CONTINUAS
        }
        self.fixadas: list[str] = ["mestre_chave_inglesa"]
        self.recompensas: dict[str, set[str]] = {
            k: set() for k in TIPOS_RECOMPENSA_VALIDOS
        }
        self.slots_firmware_max: int = 1
        self.modificadores_equipados: list[str] = []

    def possui_recompensa(self, tipo: str, recompensa_id: str) -> bool:
        """Verifica se uma recompensa permanente foi conquistada."""
        if tipo not in self.recompensas:
            return False
        return recompensa_id in self.recompensas[tipo]

    def _conceder_recompensas(self, recompensas: list[tuple[str, str]]) -> None:
        """Aplica uma lista de recompensas (tipo, id) ao estado do jogador."""
        for tipo, rid in recompensas:
            if tipo == "slot_firmware":
                self.slots_firmware_max = min(3, self.slots_firmware_max + 1)
            elif tipo in self.recompensas:
                self.recompensas[tipo].add(rid)

    def _concluir_unica(self, cid: str) -> dict | None:
        """Marca uma conquista única como concluída e retorna sua notificação, se inédita."""
        if cid in self.unicas_concluidas or cid not in CONQUISTAS_UNICAS:
            return None
        cdef = CONQUISTAS_UNICAS[cid]
        self.unicas_concluidas.add(cid)
        self._conceder_recompensas(cdef.recompensas)
        return {
            "id": cid,
            "titulo": cdef.nome,
            "recompensas": list(cdef.recompensas),
        }

    def registrar_evento(
        self,
        evento: str,
        quantidade: int | float = 1,
        contexto: dict | None = None,
    ) -> list[dict]:
        """
        Registra um evento de gameplay, atualiza conquistas contínuas e únicas,
        concede recompensas e retorna apenas as notificações recém-desbloqueadas.
        """
        ctx = contexto or {}
        notificacoes: list[dict] = []

        # 1. Conquistas Contínuas
        inc = max(0, int(quantidade)) if isinstance(quantidade, (int, float)) else 1
        for cid, cdef in CONQUISTAS_CONTINUAS.items():
            if cdef.evento != evento:
                continue
            estado = self.continuas.setdefault(
                cid, {"valor": 0, "milestones_concluidos": []}
            )
            estado["valor"] = int(estado.get("valor", 0)) + inc
            concluidos = estado.setdefault("milestones_concluidos", [])

            for idx, ms in enumerate(cdef.milestones):
                if idx in concluidos:
                    continue
                if estado["valor"] >= ms.meta:
                    concluidos.append(idx)
                    self._conceder_recompensas(ms.recompensas)
                    notificacoes.append(
                        {
                            "id": f"{cid}:m{idx + 1}",
                            "titulo": f"{cdef.nome} — {ms.titulo}",
                            "recompensas": list(ms.recompensas),
                        }
                    )

        # 2. Conquistas Únicas
        candidatas_unicas: list[str] = []

        if evento == "tempo_15fps":
            if float(quantidade) >= 120.0 or float(ctx.get("tempo_15fps", 0.0)) >= 120.0:
                candidatas_unicas.append("monge_tibetano")

        elif evento == "vitoria_boss":
            cores_inv = bool(ctx.get("cores_invertidas", False))
            vsync_off = ctx.get("vsync") == "desligado" or bool(
                ctx.get("vsync_desligado", False)
            )
            if cores_inv and vsync_off:
                candidatas_unicas.append("cabo_vga_solto")
            if int(ctx.get("configs_nao_neutras", 0)) >= 5:
                candidatas_unicas.append("modo_batata_supremo")
            if bool(ctx.get("sem_dano_f3", False)):
                candidatas_unicas.append("intocavel_rh")

        elif evento == "vitoria_sem_dano_f3":
            if bool(ctx.get("sem_dano_f3", True)):
                candidatas_unicas.append("intocavel_rh")

        elif evento in ("miniboss_rapido", "miniboss_abate"):
            if bool(ctx.get("controles_tanque", False)):
                candidatas_unicas.append("blindado_escritorio")
            if bool(ctx.get("fogo_amigo", False)):
                candidatas_unicas.append("auto_sabotagem")

        elif evento == "abate_boliche":
            if int(quantidade) >= 3 or int(ctx.get("abates_golpe", 0)) >= 3:
                candidatas_unicas.append("boliche_corporativo")

        elif evento == "nivel_alcancado":
            nivel = max(int(quantidade), int(ctx.get("nivel", 0)))
            if (
                nivel >= 8
                and bool(ctx.get("hud_desligado", False))
                and bool(ctx.get("iluminacao_ligada", False))
            ):
                candidatas_unicas.append("zero_visao_cem_fe")

        elif evento == "coleta_gc_projeteis":
            apagados = max(int(quantidade), int(ctx.get("projeteis_apagados", 0)))
            if apagados >= 15:
                candidatas_unicas.append("limpeza_de_disco")

        elif evento == "combo_atualizado":
            duracao_s = float(ctx.get("duracao_s", 0.0))
            contagem = max(int(ctx.get("contagem", 0)), int(quantidade) if isinstance(quantidade, (int, float)) else 0)
            if duracao_s >= 45.0 or contagem >= 50:
                candidatas_unicas.append("estilo_corporativo_s")

        elif evento == "parry_streak":
            streak = max(int(quantidade), int(ctx.get("streak", 0)))
            tempo_janela = float(ctx.get("tempo_janela", 0.0))
            if streak >= 5 and tempo_janela <= 12.0:
                candidatas_unicas.append("reset_infinito")

        for u_id in candidatas_unicas:
            notif = self._concluir_unica(u_id)
            if notif is not None:
                notificacoes.append(notif)

        return notificacoes

    def alternar_fixada(self, conquista_id: str) -> bool:
        """Adiciona ou remove uma conquista dos pins da HUD (máximo 3)."""
        if conquista_id in self.fixadas:
            self.fixadas.remove(conquista_id)
            return True
        if conquista_id not in CONQUISTAS_CONTINUAS and conquista_id not in CONQUISTAS_UNICAS:
            return False
        if len(self.fixadas) >= 3:
            return False
        self.fixadas.append(conquista_id)
        return True

    def equipar_firmware(self, chip_id: str) -> bool:
        """Equipa um Chip de Firmware se desbloqueado e houver slot disponível."""
        if chip_id not in CHIPS_FIRMWARE:
            return False
        if not self.possui_recompensa("modificador_run", chip_id):
            return False
        if chip_id in self.modificadores_equipados:
            return False
        if len(self.modificadores_equipados) >= self.slots_firmware_max:
            return False
        self.modificadores_equipados.append(chip_id)
        return True

    def desequipar_firmware(self, chip_id: str) -> bool:
        """Remove um Chip de Firmware equipado."""
        if chip_id in self.modificadores_equipados:
            self.modificadores_equipados.remove(chip_id)
            return True
        return False

    def obter_resumo_fixadas(self) -> list[dict]:
        """Retorna resumo das conquistas fixadas pronto para HUD.desenhar_pins_conquistas()."""
        resumo: list[dict] = []
        for cid in self.fixadas[:3]:
            if cid in CONQUISTAS_CONTINUAS:
                cdef = CONQUISTAS_CONTINUAS[cid]
                estado = self.continuas.get(cid, {"valor": 0, "milestones_concluidos": []})
                atual = int(estado.get("valor", 0))
                concluidos = estado.get("milestones_concluidos", [])
                proxima_meta = cdef.milestones[-1].meta
                concluida = len(concluidos) >= len(cdef.milestones)
                for idx, ms in enumerate(cdef.milestones):
                    if idx not in concluidos:
                        proxima_meta = ms.meta
                        break
                progresso = min(1.0, atual / max(1, proxima_meta))
                resumo.append(
                    {
                        "id": cid,
                        "nome": cdef.nome,
                        "atual": atual,
                        "meta": proxima_meta,
                        "progresso": progresso,
                        "concluida": concluida,
                    }
                )
            elif cid in CONQUISTAS_UNICAS:
                cdef = CONQUISTAS_UNICAS[cid]
                concluida = cid in self.unicas_concluidas
                resumo.append(
                    {
                        "id": cid,
                        "nome": cdef.nome,
                        "atual": 1 if concluida else 0,
                        "meta": 1,
                        "progresso": 1.0 if concluida else 0.0,
                        "concluida": concluida,
                    }
                )
        return resumo

    def to_dict(self) -> dict:
        """Serializa o progresso de conquistas no formato schema v2."""
        return {
            "unicas_concluidas": sorted(list(self.unicas_concluidas)),
            "continuas": {
                cid: {
                    "valor": int(self.continuas.get(cid, {}).get("valor", 0)),
                    "milestones_concluidos": list(
                        self.continuas.get(cid, {}).get("milestones_concluidos", [])
                    ),
                }
                for cid in CONQUISTAS_CONTINUAS
            },
            "fixadas": list(self.fixadas[:3]),
            "recompensas": {
                k: sorted(list(self.recompensas.get(k, set())))
                for k in TIPOS_RECOMPENSA_VALIDOS
            },
            "slots_firmware_max": int(max(1, min(3, self.slots_firmware_max))),
            "modificadores_equipados": list(self.modificadores_equipados),
        }

    def from_dict(self, dados: dict) -> bool:
        """Restaura o estado de conquistas a partir de um dicionário schema v2."""
        if not isinstance(dados, dict):
            return False
        try:
            temp_unicas = {
                uid
                for uid in dados.get("unicas_concluidas", [])
                if isinstance(uid, str) and uid in CONQUISTAS_UNICAS
            }
            temp_continuas: dict[str, dict[str, Any]] = {}
            raw_cont = dados.get("continuas", {})
            for cid, cdef in CONQUISTAS_CONTINUAS.items():
                entry = raw_cont.get(cid, {}) if isinstance(raw_cont, dict) else {}
                val = max(0, int(entry.get("valor", 0))) if isinstance(entry, dict) else 0
                raw_ms = entry.get("milestones_concluidos", []) if isinstance(entry, dict) else []
                ms_validos = [
                    int(m)
                    for m in raw_ms
                    if isinstance(m, int) and 0 <= m < len(cdef.milestones)
                ]
                temp_continuas[cid] = {
                    "valor": val,
                    "milestones_concluidos": sorted(list(set(ms_validos))),
                }

            raw_fixadas = dados.get("fixadas", ["mestre_chave_inglesa"])
            temp_fixadas: list[str] = []
            if isinstance(raw_fixadas, list):
                for fid in raw_fixadas:
                    if (
                        isinstance(fid, str)
                        and (fid in CONQUISTAS_CONTINUAS or fid in CONQUISTAS_UNICAS)
                        and fid not in temp_fixadas
                        and len(temp_fixadas) < 3
                    ):
                        temp_fixadas.append(fid)

            raw_recomp = dados.get("recompensas", {})
            temp_recomp: dict[str, set[str]] = {
                k: set() for k in TIPOS_RECOMPENSA_VALIDOS
            }
            if isinstance(raw_recomp, dict):
                for tipo in TIPOS_RECOMPENSA_VALIDOS:
                    itens = raw_recomp.get(tipo, [])
                    if isinstance(itens, (list, set, tuple)):
                        temp_recomp[tipo] = {str(x) for x in itens if isinstance(x, str)}

            raw_slots = dados.get("slots_firmware_max", 1)
            temp_slots = max(1, min(3, int(raw_slots)))

            raw_equip = dados.get("modificadores_equipados", [])
            temp_equip: list[str] = []
            if isinstance(raw_equip, list):
                for chip_id in raw_equip:
                    if (
                        isinstance(chip_id, str)
                        and chip_id in CHIPS_FIRMWARE
                        and chip_id in temp_recomp["modificador_run"]
                        and chip_id not in temp_equip
                        and len(temp_equip) < temp_slots
                    ):
                        temp_equip.append(chip_id)

            self.unicas_concluidas = temp_unicas
            self.continuas = temp_continuas
            self.fixadas = temp_fixadas
            self.recompensas = temp_recomp
            self.slots_firmware_max = temp_slots
            self.modificadores_equipados = temp_equip
            return True
        except (TypeError, ValueError):
            return False
