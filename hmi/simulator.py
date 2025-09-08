from __future__ import annotations

import random
import time
from typing import Dict, List, Union

from .models import PLCConfig, TunnelConfig, TunnelData


class SimulatedPLC:
    def __init__(self, cfg: PLCConfig, tunnels: List[TunnelConfig]):
        self.cfg = cfg
        self.tunnels_map: Dict[int, TunnelConfig] = {t.id: t for t in tunnels}
        # Estado interno simulado
        self.state: Dict[int, Dict[str, Union[float, bool]]] = {}
        for t in tunnels:
            self.state[t.id] = {
                "temp_ambiente": 25.0 + random.uniform(-1.0, 1.0),
                "temp_pulpa1": 20.0 + random.uniform(-1.0, 1.0),
                "temp_pulpa2": 20.0 + random.uniform(-1.0, 1.0),
                "setpoint": 5.0,
                "estado": False,
            }
        self._connected = True
        self._last_error = None
        self._last_update = time.time()

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def _step(self):
        now = time.time()
        dt = min(1.0, now - self._last_update)
        self._last_update = now
        for tid, st in self.state.items():
            amb = float(st["temp_ambiente"])  # ambiente fluctúa lento
            amb += random.uniform(-0.02, 0.02)
            st["temp_ambiente"] = max(-20.0, min(50.0, amb))

            sp = float(st["setpoint"])  # objetivo
            on = bool(st["estado"]) 

            for key in ("temp_pulpa1", "temp_pulpa2"):
                cur = float(st[key])
                target = sp if on else amb
                # dinámica simple de primer orden hacia el objetivo
                tau = 8.0  # constante de tiempo
                alpha = min(1.0, dt / tau)
                noise = random.uniform(-0.05, 0.05)
                new = cur + (target - cur) * alpha + noise
                st[key] = max(-30.0, min(60.0, new))

    def read_all(self) -> Dict[int, TunnelData]:
        if not self._connected:
            self.connect()
        self._step()
        out: Dict[int, TunnelData] = {}
        for tid, tcfg in self.tunnels_map.items():
            st = self.state[tid]
            out[tid] = TunnelData(
                id=tcfg.id,
                name=tcfg.name,
                temp_ambiente=float(st["temp_ambiente"]),
                temp_pulpa1=float(st["temp_pulpa1"]),
                temp_pulpa2=float(st["temp_pulpa2"]),
                setpoint=float(st["setpoint"]),
                estado=bool(st["estado"]),
            )
        return out

    def write_setpoint(self, tunnel_id: int, value: float) -> bool:
        if tunnel_id not in self.state:
            return False
        self.state[tunnel_id]["setpoint"] = float(value)
        return True

    def write_estado(self, tunnel_id: int, value: bool) -> bool:
        if tunnel_id not in self.state:
            return False
        self.state[tunnel_id]["estado"] = bool(value)
        return True

    def last_error(self):
        return self._last_error
