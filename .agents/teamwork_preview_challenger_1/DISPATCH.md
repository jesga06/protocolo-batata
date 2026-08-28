## 2026-08-28T19:13:16Z
Adversarially challenge and stress-test the implementation of R1, R2, and R3 in Protocolo: Batata.

Read:
- `c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\ORIGINAL_REQUEST.md`
- `c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\architecture_cache.md`
- `c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\CONFIGURACOES.md`
- `c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_worker_1\handoff.md`

Perform empirical stress testing:
1. Boundary conditions for melee 45° cone:
   - Target at angle 22.4° (hit) vs 22.6° (miss).
   - Angle wrap-around across [-pi, +pi] boundary (aim at -179° and enemy at +179° -> delta is 2° -> must hit).
   - Radial reach at 83.9px (hit) vs 84.1px (miss).
   - 10 enemies inside cone: all 10 receive 10 damage, but only the 2 closest receive 360 px/s knockback.
2. XP & Drop boundary cases:
   - Awarding 500 XP in one go from level 1 properly increments multiple levels sequentially without losing residual XP.
   - Drop lifetime at 9.9s (active) vs 10.05s (expired).
   - Scavenger grace period at 0.9s (ineligible) vs 1.05s (eligible).
3. Configuration Multiplier stress testing:
   - Test all 20 gameplay configurations enabled simultaneously at extreme values -> check that math does not overflow, NaN, or crash, and matches exact expected products.
   - Test that locked configurations never apply active buffs.
4. Run full test suite: `.\.venv\Scripts\python.exe -m unittest discover tests`.

Write stress test results and verdict (APPROVE or REQUEST_CHANGES) to handoff.md and send message back to parent.
