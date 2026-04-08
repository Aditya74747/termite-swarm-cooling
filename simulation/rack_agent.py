"""
Individual rack agent in the stigmergy simulation.
Each rack:
  - Reads its local temperature
  - Deposits a heat signal proportional to excess heat
  - Adjusts its fan speed based on local + neighbour signals
  - Has no knowledge of the global state
"""

import random


class RackAgent:
    TARGET_TEMP = 27.0       # ASHRAE A1 recommended max inlet temp (°C)
    MAX_SIGNAL = 120.0
    MAX_FAN = 100.0

    def __init__(self, rack_id: int, initial_temp: float, load: float = 0.6):
        self.rack_id = rack_id
        self.temperature = initial_temp
        self.load = load             # 0.0–1.0 — simulated compute load
        self.heat_signal = 0.0      # stigmergic pheromone analog
        self.fan_speed = 0.0        # 0–100 %
        self.log = []               # last N events for this rack

    # ------------------------------------------------------------------
    # Core stigmergy step
    # ------------------------------------------------------------------
    def deposit_signal(self, evaporation_rate: float):
        """
        Write to the environment: deposit heat proportional to excess temp.
        Evaporation reduces the signal over time (analog of pheromone decay).
        """
        excess = max(0.0, self.temperature - self.TARGET_TEMP)
        self.heat_signal += excess * 2.5
        self.heat_signal -= evaporation_rate
        self.heat_signal = max(0.0, min(self.MAX_SIGNAL, self.heat_signal))

    def read_and_respond(self, neighbour_signals: list[float]):
        """
        Read the environment: combine own signal with neighbours' signals,
        set fan speed, log significant events.
        """
        nb_avg = sum(neighbour_signals) / len(neighbour_signals) if neighbour_signals else 0.0
        effective_signal = 0.65 * self.heat_signal + 0.35 * nb_avg
        self.fan_speed = min(self.MAX_FAN, effective_signal * 1.9)

    def update_temperature(self, ambient: float, neighbour_temps: list[float]):
        """
        Physics update: heat load, fan cooling, ambient drift, conduction.
        """
        heat_gen = self.load * 0.6                      # heat from servers
        fan_cooling = self.fan_speed * 0.013            # fan removes heat
        ambient_drift = (ambient - self.temperature) * 0.008
        conduction = (
            sum(t - self.temperature for t in neighbour_temps) * 0.02
            if neighbour_temps else 0.0
        )
        noise = (random.random() - 0.5) * 0.08

        self.temperature += heat_gen - fan_cooling + ambient_drift + conduction + noise
        self.temperature = max(ambient - 3, min(70.0, self.temperature))

        # Log notable events
        if self.temperature > 40:
            self._log(f"CRITICAL: {self.temperature:.1f}°C — emergency cooling")
        elif self.temperature > 35:
            self._log(f"WARNING: {self.temperature:.1f}°C")

    def _log(self, msg: str):
        self.log.append(msg)
        if len(self.log) > 5:
            self.log.pop(0)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "id": self.rack_id,
            "temperature": round(self.temperature, 2),
            "heat_signal": round(self.heat_signal, 1),
            "fan_speed": round(self.fan_speed, 1),
            "load": round(self.load, 2),
            "log": self.log[-2:],
        }
