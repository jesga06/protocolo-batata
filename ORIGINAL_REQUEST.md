# Original User Request

## Initial Request — 2026-08-28T12:50:14-03:00

Implement the pure logic for Drop items and Scavenger AI selector in `src/sistemas/sistema_drops.py` and `src/sistemas/sistema_scavenger.py`.
Tasks:
1. Create `src/sistemas/sistema_scavenger.py` and `src/sistemas/sistema_drops.py`.
2. Implement pure logic for Drop items: 10s total lifetime, eligible for enemy capture after 1s.
3. Implement Scavenger AI selector: Only 1 enemy globally can capture a drop. Target is selected pseudo-randomly, explicitly EXCLUDING enemies that are too far and EXCLUDING the 3 closest enemies to the drop.
Constraints: DO NOT touch `src/main.py` or core entity files. Create tests in `tests/test_drops_scavenger.py` and verify.
