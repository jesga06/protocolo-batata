"""
Sistema de Spawn de Inimigos — Protocolo: Batata
Gera ondas progressivas de inimigos fora do campo de visão da câmera
com escalonamento de densidade, taxa de spawn e teto populacional suave.
"""

import random
from typing import Optional
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.inimigo_tank import InimigoTank
from src.entidades.inimigo_rapido import InimigoRapido
from src.entidades.inimigo_phasing import InimigoPhasing
from src.entidades.inimigo_blindado import InimigoBlindado
from src.entidades.inimigo_ranged import InimigoRanged
from src.entidades.inimigo_impressora import InimigoImpressoraTermica
from src.entidades.inimigo_ninja import InimigoNinja
from src.utils import constantes as _const
from src.utils.constantes import (
    SPAWN_INTERVALO_INICIAL, SPAWN_INTERVALO_MINIMO,
    SPAWN_DISTANCIA_OFFSET, SPAWN_MAX_ATIVOS,
    NINJA_MAX_ATIVOS, NINJA_COOLDOWN_SPAWN,
    LARGURA_TELA, ALTURA_TELA,
    LARGURA_ARENA, ALTURA_ARENA
)
from src.utils.math_utils import clamp


class SistemaSpawn:
    """
    Controlador do surgimento de inimigos na arena ao redor do jogador.
    """
    HORARIOS_BOSS = [60.0, 120.0, 180.0, 240.0]
    RUSH_INTERVALO = 45.0
    ARQUETIPOS_MINIBOSS_4 = (
        (InimigoRapido, "MINI-BOSS: IMPRESSORA MATRICIAL", "impressora_matricial"),
        (InimigoTank, "MINI-BOSS: FONTE GENÉRICA 500W", "fonte_generica"),
        (InimigoPhasing, "MINI-BOSS: ROTEADOR CORPORATIVO", "roteador_corporativo"),
        (InimigoBlindado, "MINI-BOSS: NO-BREAK CHUMBADO", "nobreak_chumbado"),
    )

    def __init__(
        self,
        max_ativos: int = SPAWN_MAX_ATIVOS,
        fila_minibosses: Optional[list[tuple[type, str, str]]] = None,
    ):
        self.tempo_decorrido = 0.0
        self.tempo_elite = 0.0
        self.timer_spawn = 0.0
        self.timer_rush = 0.0
        self.timer_ninja_cd = 0.0
        self.ultimo_minuto_elite = 0
        self.bosses_spawnados_indices = set()
        self._burst_inicial_feito = False
        self.max_ativos = int(max_ativos)
        if fila_minibosses is not None:
            self.fila_minibosses_run = list(fila_minibosses)
        else:
            qtd_ciclos = max(1, int(getattr(_const, "MINIBOSS_CICLOS_RUN", 3)))
            self.fila_minibosses_run = random.sample(
                list(self.ARQUETIPOS_MINIBOSS_4),
                min(qtd_ciclos, len(self.ARQUETIPOS_MINIBOSS_4)),
            )

    def intervalo_spawn(self, tempo_s: float) -> float:
        """
        Calcula a taxa de intervalo entre spawns em segundos (curva suave linear até o mínimo).
        """
        t = max(0.0, float(tempo_s))
        return max(SPAWN_INTERVALO_MINIMO, 1.55 - 0.008 * t)

    def calcular_escala_hp_tempo(self, tempo_s: float) -> float:
        """
        Mantém HP base (1.0x) até 90s para early game responsivo e escala progressivamente
        após 90s até o teto de 2.5x.
        """
        t = float(tempo_s)
        if t <= 90.0:
            return 1.0
        etapas_pos90 = (t - 90.0) / 30.0
        etapas_pos180 = max(0.0, (t - 180.0) / 30.0)
        return min(2.5, 1.0 + 0.18 * etapas_pos90 + 0.10 * etapas_pos180)

    def tamanho_lote(self, tempo_s: float) -> int:
        """
        Calcula a quantidade de inimigos gerados por pulso de spawn (3 no início, crescendo até 6).
        """
        t = max(0.0, float(tempo_s))
        return min(6, 3 + int(t // 45.0))

    def obter_arquetipo_elite(self, boss_idx: int) -> tuple[type, str]:
        """
        Retorna o par (classe_inimigo, nome_boss) correspondente à ordem de chefes da partida,
        alinhado com o CATALOGO_ARQUITETURAL.md.
        """
        catalogo = {
            1: (InimigoRapido, "MINI-BOSS: IMPRESSORA MATRICIAL"),
            2: (InimigoTank, "MINI-BOSS: FONTE GENÉRICA 500W"),
            3: (InimigoPhasing, "MINI-BOSS: ROTEADOR CORPORATIVO"),
            4: (InimigoBlindado, "MINI-BOSS: NO-BREAK CHUMBADO"),
            5: (InimigoRanged, "MINI-BOSS: PROJETOR CORPORATIVO"),
            6: (InimigoTank, "MINI-BOSS: SERVIDOR RACK 42U"),
            7: (InimigoPhasing, "MINI-BOSS: SWITCH DE REDE FANTASMA"),
            8: (InimigoBlindado, "MINI-BOSS: COFRE DIGITAL BLINDADO"),
            9: (InimigoRanged, "MINI-BOSS: SCANNER LASER INDUSTRIAL"),
        }
        if boss_idx in catalogo:
            return catalogo[boss_idx]
        return (InimigoTank, f"MINI-BOSS: AUDITORIA INTERMINÁVEL MK-{boss_idx}")

    def escolher_arquetipo(self, tempo_s: float, permitir_ranged: bool = True):
        """
        Seleciona a classe do inimigo a ser gerado com base no tempo de sobrevivência.
        Rampa mais agressiva: Rápido aos 15s, Ranged aos 25s, Phasing/Blindado aos 45s.
        """
        if tempo_s < 15.0:
            return InimigoPadrao

        r = random.random()

        # A partir de 25.0s, inclui InimigoRanged quando permitir_ranged=True (-50% frequência)
        if tempo_s >= 25.0 and permitir_ranged:
            if r < 0.08:
                return InimigoRanged

        if tempo_s < 45.0:
            # Padrão e Rápido
            return InimigoRapido if r < 0.32 else InimigoPadrao
        elif tempo_s < 75.0:
            # Padrão, Rápido, Phasing, Blindado
            if r < 0.32:
                return InimigoRapido
            elif r < 0.48:
                return InimigoPhasing
            elif r < 0.64:
                return InimigoBlindado
            return InimigoPadrao
        else:
            # Mistura avançada (inclui Impressora Térmica aos 60s+, Ranged reduzido em 50%)
            if r < 0.25:
                return InimigoRapido
            elif r < 0.335:
                return InimigoRanged if permitir_ranged else InimigoPadrao
            elif r < 0.52:
                return InimigoImpressoraTermica if permitir_ranged else InimigoPadrao
            elif r < 0.64:
                return InimigoPhasing
            elif r < 0.78:
                return InimigoBlindado
            elif r < 0.84:
                return InimigoTank
            return InimigoPadrao

    def gerar_posicao_spawn(
        self,
        camera_x: float,
        camera_y: float,
        view_w: float = float(LARGURA_TELA),
        view_h: float = float(ALTURA_TELA),
        margem: float = float(SPAWN_DISTANCIA_OFFSET),
        arena_w: float = float(LARGURA_ARENA),
        arena_h: float = float(ALTURA_ARENA)
    ) -> tuple[float, float]:
        """
        Gera uma coordenada (x, y) no anel perimetral imediatamente fora da visão da câmera.
        """
        borda = random.choice(["topo", "base", "esquerda", "direita"])

        if borda == "topo":
            x = random.uniform(camera_x - margem, camera_x + view_w + margem)
            y = camera_y - margem
        elif borda == "base":
            x = random.uniform(camera_x - margem, camera_x + view_w + margem)
            y = camera_y + view_h + margem
        elif borda == "esquerda":
            x = camera_x - margem
            y = random.uniform(camera_y - margem, camera_y + view_h + margem)
        else:  # direita
            x = camera_x + view_w + margem
            y = random.uniform(camera_y - margem, camera_y + view_h + margem)

        # Clampa suavemente na margem exterior da arena
        x = clamp(x, -margem, arena_w + margem)
        y = clamp(y, -margem, arena_h + margem)
        return x, y

    def update(
        self,
        dt: float,
        camera_x: float,
        camera_y: float,
        total_inimigos_vivos: int,
        view_w: float = float(LARGURA_TELA),
        view_h: float = float(ALTURA_TELA),
        arena_w: float = float(LARGURA_ARENA),
        arena_h: float = float(ALTURA_ARENA),
        hp_mult: float = 1.0,
        vel_mult: float = 1.0,
        permitir_ranged: bool = True,
        possui_elite_vivo: bool = False,
        ninjas_vivos: int = 0,
        fase_onda: Optional[str] = None,
        gatilho_assault_intro: bool = False,
        contagens_taticas: Optional[dict[str, int]] = None,
        forcar_rajada_tripla: bool = False,
    ) -> list:
        """
        Atualiza os cronômetros e gera novos inimigos com arquétipos variados,
        tetos táticos simultâneos, escalada de HP pós-90s e Mini-Bosses com HP cheio.
        """
        self.tempo_decorrido += dt
        novos_inimigos = []

        escalas_miniboss = tuple(getattr(_const, "MINIBOSS_ESCALA_HP_CICLOS", (1.0, 1.25, 1.50)))
        max_ranged = int(getattr(_const, "SPAWN_MAX_RANGED", 4)) * (2 if forcar_rajada_tripla else 1)
        max_impressora = int(getattr(_const, "SPAWN_MAX_IMPRESSORA", 2))
        max_tank = int(getattr(_const, "SPAWN_MAX_TANK", 3))
        mult_calm = max(0.05, float(getattr(_const, "SPAWN_MULT_FASE_CALM", 0.60)))
        mult_assault = max(0.05, float(getattr(_const, "SPAWN_MULT_FASE_ASSAULT", 1.30)))
        tempo_rajada = float(getattr(_const, "SPAWN_TEMPO_RANGED_RAJADA", 75.0))

        base_cont = contagens_taticas or {}
        cont_local = {
            "ranged": int(base_cont.get("ranged", 0)),
            "impressora": int(base_cont.get("impressora", 0)),
            "tank": int(base_cont.get("tank", 0)),
            "ninja": int(base_cont.get("ninja", ninjas_vivos)),
        }

        def _spawn_miniboss(cls_elite, nome_elite: str, arq_id: str, ciclo_idx: int):
            if not permitir_ranged and cls_elite == InimigoRanged:
                cls_elite = InimigoPadrao
            ex, ey = self.gerar_posicao_spawn(
                camera_x=camera_x,
                camera_y=camera_y,
                view_w=view_w,
                view_h=view_h,
                arena_w=arena_w,
                arena_h=arena_h,
            )
            boss_elite = cls_elite(x=ex, y=ey, is_elite=True, nome_elite=nome_elite)
            boss_elite.arquetipo_miniboss = arq_id
            boss_elite.hp_max = max(int(boss_elite.hp_max), 700)
            boss_elite.hp = boss_elite.hp_max
            escala_ciclo = float(escalas_miniboss[min(ciclo_idx, len(escalas_miniboss) - 1)])
            escala_total = escala_ciclo * float(hp_mult)
            if escala_total != 1.0:
                boss_elite.hp_max = max(1, int(round(boss_elite.hp_max * escala_total)))
                boss_elite.hp = boss_elite.hp_max
            if vel_mult != 1.0:
                boss_elite.velocidade *= float(vel_mult)
            return boss_elite

        # 1. Spawn de Mini-Boss Elite
        if gatilho_assault_intro:
            if not possui_elite_vivo and len(self.bosses_spawnados_indices) < len(self.fila_minibosses_run):
                ciclo_idx = len(self.bosses_spawnados_indices)
                self.bosses_spawnados_indices.add(ciclo_idx)
                self.ultimo_minuto_elite = ciclo_idx + 1
                cls_elite, nome_elite, arq_id = self.fila_minibosses_run[ciclo_idx]
                novos_inimigos.append(_spawn_miniboss(cls_elite, nome_elite, arq_id, ciclo_idx))
        elif fase_onda is None and not possui_elite_vivo:
            # Modo standalone/compatibilidade (sem FSM musical)
            self.tempo_elite += dt
            mapa_arq = {
                1: "impressora_matricial",
                2: "fonte_generica",
                3: "roteador_corporativo",
                4: "nobreak_chumbado",
            }
            for idx_boss, tempo_boss in enumerate(self.HORARIOS_BOSS):
                if self.tempo_elite >= tempo_boss and idx_boss not in self.bosses_spawnados_indices:
                    self.bosses_spawnados_indices.add(idx_boss)
                    self.ultimo_minuto_elite = idx_boss + 1
                    cls_elite, nome_elite = self.obter_arquetipo_elite(idx_boss + 1)
                    arq_id = mapa_arq.get(idx_boss + 1, "")
                    novos_inimigos.append(_spawn_miniboss(cls_elite, nome_elite, arq_id, idx_boss))
                    break

        # 2. Escalonamento temporal a cada 30s + escalada real de HP pós-90s
        etapas_30s = int(self.tempo_decorrido // 30.0)
        etapas_late = max(0, int((self.tempo_decorrido - 120.0) // 30.0))
        escala_vel_tempo = 1.0 + 0.06 * etapas_30s + 0.02 * etapas_late
        escala_dano_tempo = 1.0 + 0.08 * etapas_30s + 0.04 * etapas_late
        hp_mult_eff = float(hp_mult) * self.calcular_escala_hp_tempo(self.tempo_decorrido)
        vel_mult_eff = float(vel_mult) * escala_vel_tempo

        def _aplicar_teto_tatico(cls_arquetipo):
            if cls_arquetipo == InimigoRanged and cont_local["ranged"] >= max_ranged:
                return random.choice((InimigoPadrao, InimigoRapido))
            if cls_arquetipo == InimigoImpressoraTermica and cont_local["impressora"] >= max_impressora:
                return random.choice((InimigoPadrao, InimigoRapido))
            if cls_arquetipo == InimigoTank and cont_local["tank"] >= max_tank:
                return random.choice((InimigoPadrao, InimigoRapido))
            return cls_arquetipo

        def _spawn_regular(cls_arquetipo):
            cls_arquetipo = _aplicar_teto_tatico(cls_arquetipo)
            if cls_arquetipo == InimigoRanged:
                cont_local["ranged"] += 1
            elif cls_arquetipo == InimigoImpressoraTermica:
                cont_local["impressora"] += 1
            elif cls_arquetipo == InimigoTank:
                cont_local["tank"] += 1
            elif cls_arquetipo == InimigoNinja:
                cont_local["ninja"] += 1

            eh_ranged = cls_arquetipo in (InimigoRanged, InimigoImpressoraTermica)
            margem_spawn = 0.0 if eh_ranged else float(SPAWN_DISTANCIA_OFFSET)
            sx, sy = self.gerar_posicao_spawn(
                camera_x=camera_x,
                camera_y=camera_y,
                view_w=view_w,
                view_h=view_h,
                margem=margem_spawn,
                arena_w=arena_w,
                arena_h=arena_h,
            )
            if eh_ranged:
                sx = clamp(sx, 0.0, max(0.0, arena_w - 48.0))
                sy = clamp(sy, 0.0, max(0.0, arena_h - 48.0))
            novo = cls_arquetipo(x=sx, y=sy)
            if cls_arquetipo == InimigoRanged:
                novo.rajada_tripla = bool(forcar_rajada_tripla or self.tempo_decorrido >= tempo_rajada)
            if hp_mult_eff != 1.0:
                novo.hp_max = max(1, int(round(novo.hp_max * hp_mult_eff)))
                novo.hp = novo.hp_max
            if vel_mult_eff != 1.0:
                novo.velocidade *= vel_mult_eff
            if escala_dano_tempo != 1.0:
                if hasattr(novo, "dano_contato"):
                    novo.dano_contato = max(1, int(round(novo.dano_contato * escala_dano_tempo)))
                if hasattr(novo, "dano_projetil"):
                    novo.dano_projetil = max(1, int(round(novo.dano_projetil * escala_dano_tempo)))
            return novo

        def _escolher_calm():
            if self.tempo_decorrido < 15.0:
                return InimigoPadrao
            r = random.random()
            if self.tempo_decorrido >= 25.0 and permitir_ranged and r < 0.08:
                return InimigoRanged
            return InimigoRapido if r < 0.32 else InimigoPadrao

        # 2b. Burst inicial de boas-vindas (evita arena vazia nos primeiros segundos)
        if not self._burst_inicial_feito:
            self._burst_inicial_feito = True
            vagas_burst = self.max_ativos - (total_inimigos_vivos + len(novos_inimigos))
            qtd_burst = min(6, max(0, vagas_burst))
            for _ in range(qtd_burst):
                novos_inimigos.append(_spawn_regular(random.choice((InimigoPadrao, InimigoRapido))))

        # 3. Verificação de Lote de Inimigos Regulares
        self.timer_spawn += dt
        intervalo = self.intervalo_spawn(self.tempo_decorrido)
        if fase_onda == "calm":
            intervalo_efetivo = intervalo / mult_calm
        elif fase_onda == "assault":
            intervalo_efetivo = intervalo / mult_assault
        else:
            intervalo_efetivo = intervalo

        if self.timer_spawn >= intervalo_efetivo:
            self.timer_spawn -= intervalo_efetivo

            vagas_disponiveis = self.max_ativos - (total_inimigos_vivos + len(novos_inimigos))
            if vagas_disponiveis > 0:
                qtd_a_gerar = min(self.tamanho_lote(self.tempo_decorrido), vagas_disponiveis)
                for _ in range(qtd_a_gerar):
                    if fase_onda == "calm":
                        cls_arquetipo = _escolher_calm()
                    else:
                        cls_arquetipo = self.escolher_arquetipo(self.tempo_decorrido, permitir_ranged=permitir_ranged)
                    novos_inimigos.append(_spawn_regular(cls_arquetipo))

        # 4. Rush Waves (gatilho imediato em ASSAULT_INTRO ou periódico no modo standalone)
        if gatilho_assault_intro:
            vagas_rush = self.max_ativos - (total_inimigos_vivos + len(novos_inimigos))
            if vagas_rush > 0:
                qtd_rush = min(min(6 + etapas_30s // 3, 8), vagas_rush)
                arquetipos_rush = (InimigoRapido, InimigoPadrao)
                for _ in range(qtd_rush):
                    novos_inimigos.append(_spawn_regular(random.choice(arquetipos_rush)))
        elif fase_onda != "calm":
            self.timer_rush += dt
            intervalo_rush = 35.0 if self.tempo_decorrido >= 150.0 else self.RUSH_INTERVALO
            if self.timer_rush >= intervalo_rush:
                self.timer_rush -= intervalo_rush
                vagas_rush = self.max_ativos - (total_inimigos_vivos + len(novos_inimigos))
                if vagas_rush > 0:
                    qtd_rush = min(min(6 + etapas_30s // 3, 8), vagas_rush)
                    arquetipos_rush = [InimigoRapido, InimigoPadrao, InimigoPhasing]
                    for _ in range(qtd_rush):
                        cls_rush = random.choice(arquetipos_rush)
                        novos_inimigos.append(_spawn_regular(cls_rush))

        # 5. InimigoNinja (máximo 2 ativos, mínimo 20s entre spawns)
        if self.timer_ninja_cd > 0.0:
            self.timer_ninja_cd = max(0.0, self.timer_ninja_cd - dt)
        if (
            self.tempo_decorrido >= 75.0
            and int(cont_local["ninja"]) < NINJA_MAX_ATIVOS
            and self.timer_ninja_cd <= 0.0
            and (self.max_ativos - (total_inimigos_vivos + len(novos_inimigos))) > 0
        ):
            self.timer_ninja_cd = float(NINJA_COOLDOWN_SPAWN)
            novos_inimigos.append(_spawn_regular(InimigoNinja))

        return novos_inimigos

