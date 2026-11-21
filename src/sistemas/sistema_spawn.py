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

    def __init__(self, max_ativos: int = SPAWN_MAX_ATIVOS):
        self.tempo_decorrido = 0.0
        self.tempo_elite = 0.0
        self.timer_spawn = 0.0
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
        Fórmula: N_batch(t) = min(8, 1 + floor(t / 25))
        """
        return min(8, 1 + int(float(tempo_s) // 25.0))

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
        Distribuição suavizada com Tank reduzido para 5% dos spawns avançados.
        A partir de 35s inclui InimigoRanged nativamente (12% sem permitir_ranged, 25% com permitir_ranged).
        """
        if tempo_s < 25.0:
            return InimigoPadrao

        r = random.random()

        # A partir de 35.0s, inclui InimigoRanged quando permitir_ranged=True
        if tempo_s >= 35.0 and permitir_ranged:
            if r < 0.15:
                return InimigoRanged

        if tempo_s < 55.0:
            # Padrão e Rápido
            return InimigoRapido if r < 0.25 else InimigoPadrao
        elif tempo_s < 90.0:
            # Padrão, Rápido, Phasing, Blindado
            if r < 0.30:
                return InimigoRapido
            elif r < 0.45:
                return InimigoPhasing
            elif r < 0.60:
                return InimigoBlindado
            return InimigoPadrao
        else:
            # Mistura avançada
            if r < 0.25:
                return InimigoRapido
            elif r < 0.43:
                return InimigoRanged if permitir_ranged else InimigoPadrao
            elif r < 0.57:
                return InimigoPhasing
            elif r < 0.70:
                return InimigoBlindado
            elif r < 0.75:
                return InimigoTank  # Apenas 5% relativo
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

        # 2. Verificação de Lote de Inimigos Regulares
        self.timer_spawn += dt
        intervalo = self.intervalo_spawn(self.tempo_decorrido)
        if self.timer_spawn >= intervalo:
            self.timer_spawn -= intervalo

            vagas_disponiveis = self.max_ativos - (total_inimigos_vivos + len(novos_inimigos))
            if vagas_disponiveis > 0:
                qtd_a_gerar = min(self.tamanho_lote(self.tempo_decorrido), vagas_disponiveis)
                for _ in range(qtd_a_gerar):
                    cls_arquetipo = self.escolher_arquetipo(self.tempo_decorrido, permitir_ranged=permitir_ranged)
                    # Manter InimigoRanged dentro dos limites da arena para garantir stand-off e linha de tiro
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
                    if hp_mult != 1.0:
                        novo.hp_max = max(1, int(round(novo.hp_max * hp_mult)))
                        novo.hp = novo.hp_max
                    if vel_mult != 1.0:
                        novo.velocidade *= float(vel_mult)
                    novos_inimigos.append(novo)

        return novos_inimigos

