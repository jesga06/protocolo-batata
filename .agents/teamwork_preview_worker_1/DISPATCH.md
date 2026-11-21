## 2026-08-29T05:39:35Z
Implement all Phase 6 features for 'Protocolo: Batata':
1. `src/sistemas/config_sistema.py`: statistics schema, persistence, `obter_estatisticas()`, `registrar_partida()`.
2. `src/cenas/menu_principal.py`: display High Score & Best Time badge.
3. `src/entidades/inimigo_base.py`: `is_elite`, `nome_elite`, stats boost (3x HP, 10x score, 50 XP), pulsing purple/gold aura render.
4. `src/sistemas/sistema_spawn.py`: minute-based elite boss scheduling every 60s with `obter_arquetipo_elite(minuto)`.
5. `src/sistemas/sistema_drops.py`: elite drops (+50 XP cluster, guaranteed weapon crate, guaranteed equipment crate).
6. `src/ui/hud.py`: `HUD.desenhar_barra_boss(...)` top-screen 400x12px at y=78.
7. `src/sistemas/sistema_particulas.py`: `SistemaParticulas` class (sparks, bursts, shockwaves, debris, cap 300).
8. `src/utils/constantes.py`: `TEMPO_VITORIA = 600.0`.
9. `src/cenas/gameplay.py`: `dano_total_causado`, particles integration, screen shake config hook, boss bar rendering, 10-minute victory sequence at 600.0s, victory overlay without emojis, game over / victory `registrar_partida`.
10. Comprehensive unit tests: `test_persistence.py`, `test_particles_screenshake.py`, `test_elite_bosses_and_waves.py`, `test_vitoria_stats.py`.
11. Run all unit tests to confirm 100% pass rate.
12. Handoff report and parent notification.
