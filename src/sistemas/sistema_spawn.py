"""
Sistema de Spawn de Inimigos — Protocolo: Batata
Gera ondas progressivas de inimigos fora do campo de visão da câmera
com escalonamento de densidade, taxa de spawn e teto populacional suave.
"""

import random
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.inimigo_tank import InimigoTank
from src.entidades.inimigo_rapido import InimigoRapido
from src.entidades.inimigo_phasing import InimigoPhasing
from src.entidades.inimigo_blindado import InimigoBlindado
from src.entidades.inimigo_ranged import InimigoRanged
from src.utils.constantes import (
    SPAWN_INTERVALO_INICIAL, SPAWN_INTERVALO_MINIMO,
    SPAWN_DISTANCIA_OFFSET, SPAWN_MAX_ATIVOS,
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

    def __init__(self, max_ativos: int = SPAWN_MAX_ATIVOS):
        self.tempo_decorrido = 0.0
        self.tempo_elite = 0.0
        self.timer_spawn = 0.0
        self.timer_rush = 0.0
        self.ultimo_minuto_elite = 0
        self.bosses_spawnados_indices = set()
        self.max_ativos = int(max_ativos)

    def intervalo_spawn(self, tempo_s: float) -> float:
        """
        Calcula a taxa de intervalo entre spawns em segundos.
        Nos primeiros 50s, acelera suavemente (0.67x em 0s até 1.0x em 50s) para popular a tela 1280x720.
        """
        base = max(SPAWN_INTERVALO_MINIMO, SPAWN_INTERVALO_INICIAL - 0.012 * float(tempo_s))
        t = max(0.0, float(tempo_s))
        if t < 50.0:
            fator = 0.67 + 0.33 * (t / 50.0)
            return max(SPAWN_INTERVALO_MINIMO, base * fator)
        return base

    def tamanho_lote(self, tempo_s: float) -> int:
        """
        Calcula a quantidade de inimigos gerados por pulso de spawn.
        Fórmula: N_batch(t) = min(14, 2 + floor(t / 20))
        """
        return min(14, 2 + int(float(tempo_s) // 20.0))

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

        # A partir de 25.0s, inclui InimigoRanged quando permitir_ranged=True
        if tempo_s >= 25.0 and permitir_ranged:
            if r < 0.16:
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
            # Mistura avançada
            if r < 0.28:
                return InimigoRapido
            elif r < 0.46:
                return InimigoRanged if permitir_ranged else InimigoPadrao
            elif r < 0.60:
                return InimigoPhasing
            elif r < 0.74:
                return InimigoBlindado
            elif r < 0.80:
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
        possui_elite_vivo: bool = False
    ) -> list:
        """
        Atualiza os cronômetros e gera novos inimigos com arquétipos variados,
        além de agendar o spawn obrigatório de Mini-Bosses (1:00, 2:00, 3:00, 4:00) com trava anti-stacking.
        Aplica multiplicadores de HP e Velocidade da configuração ativa.
        """
        self.tempo_decorrido += dt
        novos_inimigos = []

        # 1. Verificação de Spawn de Mini-Boss Elite (1:00 / 60s, 2:00 / 120s, 3:00 / 180s, 4:00 / 240s) com trava anti-stacking
        if not possui_elite_vivo:
            self.tempo_elite += dt
            for idx_boss, tempo_boss in enumerate(self.HORARIOS_BOSS):
                if self.tempo_elite >= tempo_boss and idx_boss not in self.bosses_spawnados_indices:
                    self.bosses_spawnados_indices.add(idx_boss)
                    self.ultimo_minuto_elite = idx_boss + 1
                    cls_elite, nome_elite = self.obter_arquetipo_elite(idx_boss + 1)
                    if not permitir_ranged and cls_elite == InimigoRanged:
                        cls_elite = InimigoPadrao
                    ex, ey = self.gerar_posicao_spawn(
                        camera_x=camera_x,
                        camera_y=camera_y,
                        view_w=view_w,
                        view_h=view_h,
                        arena_w=arena_w,
                        arena_h=arena_h
                    )
                    boss_elite = cls_elite(x=ex, y=ey, is_elite=True, nome_elite=nome_elite)
                    if idx_boss == 0:
                        boss_elite.hp_max = max(1, int(round(boss_elite.hp_max * 0.40)))
                        boss_elite.hp = boss_elite.hp_max
                    mapa_arq = {
                        1: "impressora_matricial",
                        2: "fonte_generica",
                        3: "roteador_corporativo",
                        4: "nobreak_chumbado"
                    }
                    boss_elite.arquetipo_miniboss = mapa_arq.get(idx_boss + 1, "")
                    if hp_mult != 1.0:
                        boss_elite.hp_max = max(1, int(round(boss_elite.hp_max * hp_mult)))
                        boss_elite.hp = boss_elite.hp_max
                    if vel_mult != 1.0:
                        boss_elite.velocidade *= float(vel_mult)
                    novos_inimigos.append(boss_elite)
                    break

        # 2. Escalonamento temporal a cada 30 segundos (+12% HP, +6% Vel, +8% Dano)
        etapas_30s = int(self.tempo_decorrido // 30.0)
        escala_hp_tempo = 1.0 + 0.12 * etapas_30s
        escala_vel_tempo = 1.0 + 0.06 * etapas_30s
        escala_dano_tempo = 1.0 + 0.08 * etapas_30s
        hp_mult_eff = float(hp_mult) * escala_hp_tempo
        vel_mult_eff = float(vel_mult) * escala_vel_tempo

        def _spawn_regular(cls_arquetipo):
            margem_spawn = 0.0 if cls_arquetipo == InimigoRanged else float(SPAWN_DISTANCIA_OFFSET)
            sx, sy = self.gerar_posicao_spawn(
                camera_x=camera_x,
                camera_y=camera_y,
                view_w=view_w,
                view_h=view_h,
                margem=margem_spawn,
                arena_w=arena_w,
                arena_h=arena_h
            )
            if cls_arquetipo == InimigoRanged:
                sx = clamp(sx, 0.0, max(0.0, arena_w - 42.0))
                sy = clamp(sy, 0.0, max(0.0, arena_h - 42.0))
            novo = cls_arquetipo(x=sx, y=sy)
            if cls_arquetipo == InimigoRanged and permitir_ranged:
                novo.rajada_tripla = True
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

        # 3. Verificação de Lote de Inimigos Regulares
        self.timer_spawn += dt
        intervalo = self.intervalo_spawn(self.tempo_decorrido)
        if self.timer_spawn >= intervalo:
            self.timer_spawn -= intervalo

            vagas_disponiveis = self.max_ativos - (total_inimigos_vivos + len(novos_inimigos))
            if vagas_disponiveis > 0:
                qtd_a_gerar = min(self.tamanho_lote(self.tempo_decorrido), vagas_disponiveis)
                for _ in range(qtd_a_gerar):
                    cls_arquetipo = self.escolher_arquetipo(self.tempo_decorrido, permitir_ranged=permitir_ranged)
                    novos_inimigos.append(_spawn_regular(cls_arquetipo))

        # 4. Rush Waves independentes a cada 45s (sem afetar timer_spawn)
        self.timer_rush += dt
        if self.timer_rush >= self.RUSH_INTERVALO:
            self.timer_rush -= self.RUSH_INTERVALO
            vagas_rush = self.max_ativos - (total_inimigos_vivos + len(novos_inimigos))
            if vagas_rush > 0:
                qtd_rush = min(min(8 + etapas_30s // 2, 12), vagas_rush)
                arquetipos_rush = [InimigoRapido, InimigoPadrao, InimigoPhasing]
                for _ in range(qtd_rush):
                    cls_rush = random.choice(arquetipos_rush)
                    novos_inimigos.append(_spawn_regular(cls_rush))

        return novos_inimigos

