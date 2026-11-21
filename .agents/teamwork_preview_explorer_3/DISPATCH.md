## 2026-08-29T05:36:15Z
Investigate High Score & Meta-Progression Persistence (`data/save.json`, Main Menu display) and Combat Particle Effects / Screen Shake.
Specifically:
1. Examine `data/` directory, `src/cenas/menu_principal.py`, `src/utils/`, and how save data / persistent state is or should be handled cleanly.
2. Examine combat visual feedback: bullet hit sparks, drop collection bursts (gold sparkles for XP, green for heal), rocket/grenade explosions (orange shockwave circles), and screen shake integration (hooked to Config 5 `screen_shake`).
3. Check existing particle/rendering architecture in `src/` to ensure particle emitters are lightweight, performant, and do not drop FPS.
4. Review existing unit test suite in `tests/` (`python -m unittest discover -s tests`) to understand test conventions and what tests will verify persistence and particle systems.
5. Write your comprehensive analysis and recommendations to `.agents/teamwork_preview_explorer_3/handoff.md`.
6. Send a message to caller with a summary of findings and the path to your handoff file.
