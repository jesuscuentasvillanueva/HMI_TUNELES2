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
                "setpoint": 5.0,             # SP ambiente
                "setpoint_pulpa1": 5.0,      # SP pulpa1
                "setpoint_pulpa2": 5.0,      # SP pulpa2
                "estado": False,
                # Calibraciones en PLC
                "cal_temp_ambiente": 0.0,
                "cal_temp_pulpa1": 0.0,
                "cal_temp_pulpa2": 0.0,
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

            sp = float(st["setpoint"])  # objetivo ambiente
            on = bool(st["estado"]) 

            # Dinámica de P1 y P2 hacia su propio setpoint o ambiente si OFF
            for key, sp_key in (("temp_pulpa1", "setpoint_pulpa1"), ("temp_pulpa2", "setpoint_pulpa2")):
                cur = float(st[key])
                target_sp = float(st[sp_key])
                target = target_sp if on else amb
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
            # Aplicar calibración como lo haría el PLC
            amb = float(st["temp_ambiente"]) + float(st.get("cal_temp_ambiente", 0.0))
            p1 = float(st["temp_pulpa1"]) + float(st.get("cal_temp_pulpa1", 0.0))
            p2 = float(st["temp_pulpa2"]) + float(st.get("cal_temp_pulpa2", 0.0))

            out[tid] = TunnelData(
                id=tcfg.id,
                name=tcfg.name,
                temp_ambiente=amb,
                temp_pulpa1=p1,
                temp_pulpa2=p2,
                setpoint=float(st["setpoint"]),
                setpoint_pulpa1=float(st["setpoint_pulpa1"]),
                setpoint_pulpa2=float(st["setpoint_pulpa2"]),
                estado=bool(st["estado"]),
            )
        return out

    def write_setpoint(self, tunnel_id: int, value: float) -> bool:
        if tunnel_id not in self.state:
            return False
        self.state[tunnel_id]["setpoint"] = float(value)
        return True

    def write_setpoint_p1(self, tunnel_id: int, value: float) -> bool:
        if tunnel_id not in self.state:
            return False
        self.state[tunnel_id]["setpoint_pulpa1"] = float(value)
        return True

    def write_setpoint_p2(self, tunnel_id: int, value: float) -> bool:
        if tunnel_id not in self.state:
            return False
        self.state[tunnel_id]["setpoint_pulpa2"] = float(value)
        return True

    def write_estado(self, tunnel_id: int, value: bool) -> bool:
        if tunnel_id not in self.state:
            return False
        self.state[tunnel_id]["estado"] = bool(value)
        return True

    # Escritura genérica por clave (calibraciones u otros tags REAL/BOOL simulados)
    def write_by_key(self, tunnel_id: int, tag_key: str, value) -> bool:
        if tunnel_id not in self.state:
            return False
        try:
            if tag_key in ("cal_temp_ambiente", "cal_temp_pulpa1", "cal_temp_pulpa2"):
                self.state[tunnel_id][tag_key] = float(value)
                return True
            # fallback: si el estado contiene la clave, actualizar
            if tag_key in self.state[tunnel_id]:
                self.state[tunnel_id][tag_key] = value
                return True
        except Exception:
            return False
        return False

    def last_error(self):
        return self._last_error
