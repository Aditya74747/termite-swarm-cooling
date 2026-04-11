"""
DataCenter — orchestrates the rack grid and stigmergy environment.
The 'environment' is just the grid of heat_signal values each agent writes to.
No agent communicates directly with another.
"""

import random
import time
from simulation.rack_agent import RackAgent


class DataCenter:

    def __init__(self, rows: int = 4, cols: int = 6):
        self.rows = rows
        self.cols = cols
        self.n = rows * cols
        self.ambient = 24.0
        self.evaporation_rate = 5.0
        self.tick = 0
        self.start_time = time.time()
        self.history = []        # list of (tick, avg_temp) for sparkline
        self.event_log = []      # global events

        self.racks: list[RackAgent] = []
        self._init_racks()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    def _init_racks(self):
        self.racks = [
            RackAgent(
                rack_id=i,
                initial_temp=self.ambient + random.uniform(0, 5),
                load=random.uniform(0.4, 0.85),
            )
            for i in range(self.n)
        ]

    def reset(self):
        self.tick = 0
        self.history = []
        self.event_log = []
        self._init_racks()
        self._log("Simulation reset — all agents reinitialised")

    # ------------------------------------------------------------------
    # Topology helpers
    # ------------------------------------------------------------------
    def _neighbours(self, i: int) -> list[int]:
        r, c = divmod(i, self.cols)
        nb = []
        if r > 0:            nb.append(i - self.cols)
        if r < self.rows - 1: nb.append(i + self.cols)
        if c > 0:            nb.append(i - 1)
        if c < self.cols - 1: nb.append(i + 1)
        return nb

    # ------------------------------------------------------------------
    # Simulation step  (called every 0.5 s by background thread)
    # ------------------------------------------------------------------
    def step(self):
        self.tick += 1

        # Phase 1 — each agent deposits its heat signal (writes to env)
        for rack in self.racks:
            rack.deposit_signal(self.evaporation_rate)

        # Phase 2 — each agent reads neighbour signals, sets fan speed
        for i, rack in enumerate(self.racks):
            nb_signals = [self.racks[j].heat_signal for j in self._neighbours(i)]
            rack.read_and_respond(nb_signals)

        # Phase 3 — physics update
        for i, rack in enumerate(self.racks):
            nb_temps = [self.racks[j].temperature for j in self._neighbours(i)]
            rack.update_temperature(self.ambient, nb_temps)

        # Record history (every 4 ticks ≈ 2 s)
        if self.tick % 4 == 0:
            avg = sum(r.temperature for r in self.racks) / self.n
            self.history.append({"tick": self.tick, "avg": round(avg, 2)})
            if len(self.history) > 60:
                self.history.pop(0)

        # Global events
        hot_count = sum(1 for r in self.racks if r.temperature > 35)
        if hot_count > 0 and self.tick % 10 == 0:
            self._log(f"Tick {self.tick}: {hot_count} rack(s) above 35 °C — signal cascade active")
        elif self.tick % 40 == 0:
            avg = sum(r.temperature for r in self.racks) / self.n
            self._log(f"Tick {self.tick}: avg {avg:.1f} °C — system stable")

    # ------------------------------------------------------------------
    # Control actions
    # ------------------------------------------------------------------
    def add_hotspot(self, idx: int):
        if 0 <= idx < self.n:
            spike = random.uniform(10, 18)
            self.racks[idx].temperature += spike
            self.racks[idx].load = min(1.0, self.racks[idx].load + 0.2)
            self._log(f"Hotspot +{spike:.1f}°C injected → rack {idx + 1}")

    def random_load_spike(self):
        idx = random.randint(0, self.n - 1)
        self.racks[idx].load = min(1.0, self.racks[idx].load + random.uniform(0.3, 0.5))
        self._log(f"Load spike on rack {idx + 1} (load → {self.racks[idx].load:.2f})")

    def _log(self, msg: str):
        self.event_log.append({"t": self.tick, "msg": msg})
        if len(self.event_log) > 20:
            self.event_log.pop(0)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def get_state(self) -> dict:
        temps = [r.temperature for r in self.racks]
        fans = [r.fan_speed for r in self.racks]
        avg_temp = sum(temps) / self.n
        max_temp = max(temps)
        avg_fan = sum(fans) / self.n
        hot_zones = sum(1 for t in temps if t > 32)
        elapsed = int(time.time() - self.start_time)

        return {
            "tick": self.tick,
            "elapsed": elapsed,
            "ambient": self.ambient,
            "evaporation_rate": self.evaporation_rate,
            "avg_temp": round(avg_temp, 2),
            "max_temp": round(max_temp, 2),
            "avg_fan": round(avg_fan, 1),
            "hot_zones": hot_zones,
            "racks": [r.to_dict() for r in self.racks],
            "history": self.history,
            "event_log": self.event_log[-8:],
        }
