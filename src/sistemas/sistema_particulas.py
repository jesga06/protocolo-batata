"""
Sistema de Partículas e Feedback Visual — Protocolo: Batata
Gerencia efeitos visuais de alta performance:
- Faíscas balísticas de impacto de tiros
- Bursts cintilantes na coleta de drops (XP, cura, caixas)
- Ondas de choque expansivas e detritos de explosões
"""

import math
import random
import pygame


class Particula:
    """Representa uma partícula individual em coordenadas de mundo."""
    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        vida_max: float,
        tamanho_inicial: float,
        tamanho_final: float,
        cor: tuple[int, int, int],
        decaimento_vel: float = 0.92
    ):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.vida_max = max(0.01, float(vida_max))
        self.vida = self.vida_max
        self.tamanho_inicial = float(tamanho_inicial)
        self.tamanho_final = float(tamanho_final)
        self.cor = cor
        self.decaimento_vel = float(decaimento_vel)

    @property
    def viva(self) -> bool:
        return self.vida > 0.0

    @property
    def progresso(self) -> float:
        """Retorna valor de 0.0 (nascimento) a 1.0 (morte)."""
        return 1.0 - (self.vida / self.vida_max)

    def update(self, dt: float):
        self.vida -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= (self.decaimento_vel ** (dt * 60.0))
        self.vy *= (self.decaimento_vel ** (dt * 60.0))

    def obter_tamanho_atual(self) -> float:
        p = self.progresso
        return max(0.5, self.tamanho_inicial + (self.tamanho_final - self.tamanho_inicial) * p)


class OndaChoque:
    """Representa um anel expansivo de onda de choque."""
    def __init__(
        self,
        x: float,
        y: float,
        raio_max: float = 80.0,
        vida_max: float = 0.25,
        cor: tuple[int, int, int] = (255, 140, 30)
    ):
        self.x = float(x)
        self.y = float(y)
        self.raio_max = float(raio_max)
        self.vida_max = max(0.01, float(vida_max))
        self.vida = self.vida_max
        self.cor = cor

    @property
    def viva(self) -> bool:
        return self.vida > 0.0

    @property
    def progresso(self) -> float:
        return 1.0 - (self.vida / self.vida_max)

    def update(self, dt: float):
        self.vida -= dt

    def obter_raio_atual(self) -> float:
        return max(1.0, self.raio_max * (self.progresso ** 0.5))


class SistemaParticulas:
    """
    Gerenciador global de partículas com teto rígido de instâncias e rendering otimizado.
    """
    MAX_PARTICULAS = 300

    def __init__(self):
        self.particulas: list[Particula] = []
        self.ondas_choque: list[OndaChoque] = []

    def limpar(self):
        """Descarta todas as partículas e ondas ativas."""
        self.particulas.clear()
        self.ondas_choque.clear()

    def emitir_faiscas(
        self,
        x: float,
        y: float,
        dir_x: float = 0.0,
        dir_y: float = 0.0,
        cor: tuple[int, int, int] = (255, 220, 100),
        qtd: int = 6
    ):
        """
        Emite faíscas balísticas direcionais ao atingir um alvo.
        """
        base_ang = math.atan2(dir_y, dir_x) if (dir_x != 0 or dir_y != 0) else random.uniform(0, 2 * math.pi)

        for _ in range(qtd):
            if len(self.particulas) >= self.MAX_PARTICULAS:
                self.particulas.pop(0)

            # Cone de espalhamento de ~90 graus
            ang = base_ang + random.uniform(-0.8, 0.8)
            vel = random.uniform(120.0, 320.0)
            vx = math.cos(ang) * vel
            vy = math.sin(ang) * vel
            vida = random.uniform(0.10, 0.22)
            tam_ini = random.uniform(2.5, 4.0)

            p = Particula(
                x=x,
                y=y,
                vx=vx,
                vy=vy,
                vida_max=vida,
                tamanho_inicial=tam_ini,
                tamanho_final=0.5,
                cor=cor,
                decaimento_vel=0.88
            )
            self.particulas.append(p)

    def emitir_burst_drop(self, x: float, y: float, tipo: str = "xp"):
        """
        Emite partículas cintilantes ascendentes ao coletar um drop.
        """
        mapa_cores = {
            "xp": (255, 215, 0),         # Dourado
            "cura": (50, 230, 90),        # Verde
            "arma": (255, 140, 0),        # Laranja
            "equipamento": (175, 75, 255),# Roxo
            "config": (0, 220, 255)       # Ciano
        }
        cor = mapa_cores.get(tipo, (255, 255, 255))
        qtd = 12 if tipo in ("arma", "equipamento") else 8

        for _ in range(qtd):
            if len(self.particulas) >= self.MAX_PARTICULAS:
                self.particulas.pop(0)

            ang = random.uniform(-math.pi * 0.8, -math.pi * 0.2)  # Direção preferencialmente para cima
            vel = random.uniform(60.0, 160.0)
            vx = math.cos(ang) * vel + random.uniform(-20, 20)
            vy = math.sin(ang) * vel
            vida = random.uniform(0.20, 0.40)
            tam_ini = random.uniform(3.0, 5.0)

            p = Particula(
                x=x + random.uniform(-6, 6),
                y=y + random.uniform(-6, 6),
                vx=vx,
                vy=vy,
                vida_max=vida,
                tamanho_inicial=tam_ini,
                tamanho_final=0.0,
                cor=cor,
                decaimento_vel=0.94
            )
            self.particulas.append(p)

    def emitir_onda_choque(
        self,
        x: float,
        y: float,
        raio_max: float = 80.0,
        cor: tuple[int, int, int] = (255, 140, 30)
    ):
        """
        Cria uma onda de choque radial expansiva.
        """
        self.ondas_choque.append(OndaChoque(x=x, y=y, raio_max=raio_max, vida_max=0.28, cor=cor))

    def emitir_debris(
        self,
        x: float,
        y: float,
        cor: tuple[int, int, int] = (200, 120, 50),
        qtd: int = 10
    ):
        """
        Emite fragmentos de detritos em todas as direções para explosões.
        """
        for _ in range(qtd):
            if len(self.particulas) >= self.MAX_PARTICULAS:
                self.particulas.pop(0)

            ang = random.uniform(0, 2 * math.pi)
            vel = random.uniform(80.0, 260.0)
            vx = math.cos(ang) * vel
            vy = math.sin(ang) * vel
            vida = random.uniform(0.20, 0.45)
            tam_ini = random.uniform(2.0, 4.5)

            p = Particula(
                x=x,
                y=y,
                vx=vx,
                vy=vy,
                vida_max=vida,
                tamanho_inicial=tam_ini,
                tamanho_final=0.5,
                cor=cor,
                decaimento_vel=0.90
            )
            self.particulas.append(p)

    def update(self, dt: float):
        """
        Atualiza física e tempo de vida de todas as partículas e ondas.
        """
        for p in self.particulas:
            p.update(dt)
        self.particulas = [p for p in self.particulas if p.viva]

        for oc in self.ondas_choque:
            oc.update(dt)
        self.ondas_choque = [oc for oc in self.ondas_choque if oc.viva]

    def desenhar(self, janela, camera=None):
        """
        Renderiza todas as partículas e ondas de choque na tela virtual.
        """
        screen = janela.screen

        # 1. Renderiza ondas de choque
        for oc in self.ondas_choque:
            tx = camera.transform_x(oc.x) if camera else oc.x
            ty = camera.transform_y(oc.y) if camera else oc.y

            if tx < -100 or tx > janela.largura + 100 or ty < -100 or ty > janela.altura + 100:
                continue

            raio = oc.obter_raio_atual()
            alpha = int(max(0, 255 * (1.0 - oc.progresso)))
            dim = int(raio * 2 + 10)

            if dim > 0 and alpha > 5:
                try:
                    surf_oc = pygame.Surface((dim, dim), pygame.SRCALPHA)
                    cx = dim // 2
                    cy = dim // 2
                    cor_rgba = (oc.cor[0], oc.cor[1], oc.cor[2], alpha)
                    largura_linha = max(1, int(3 * (1.0 - oc.progresso)))
                    pygame.draw.circle(surf_oc, cor_rgba, (cx, cy), int(raio), width=largura_linha)
                    screen.blit(surf_oc, (int(tx - cx), int(ty - cy)))
                except Exception:
                    pass

        # 2. Renderiza partículas
        for p in self.particulas:
            tx = camera.transform_x(p.x) if camera else p.x
            ty = camera.transform_y(p.y) if camera else p.y

            if tx < -20 or tx > janela.largura + 20 or ty < -20 or ty > janela.altura + 20:
                continue

            tam = p.obter_tamanho_atual()
            if tam > 0:
                pygame.draw.circle(screen, p.cor, (int(tx), int(ty)), max(1, int(tam)))
