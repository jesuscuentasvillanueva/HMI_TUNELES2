from __future__ import annotations

from typing import Dict, List, Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

from .models import TunnelConfig, TunnelData
from .plc_client import BasePLC


class Poller(QObject):
    updated = pyqtSignal(dict)  # Dict[int, TunnelData]
    plc_status_changed = pyqtSignal(bool)
    stop_requested = pyqtSignal()

    def __init__(self, plc: BasePLC, tunnels: List[TunnelConfig], interval_ms: int = 1000):
        super().__init__()
        self.plc = plc
        self.tunnels = tunnels
        self.tunnels_map: Dict[int, TunnelConfig] = {t.id: t for t in tunnels}
        self.interval_ms = int(max(200, interval_ms))
        self._timer: Optional[QTimer] = None
        self._running = False
        self._last_status: Optional[bool] = None

    @pyqtSlot()
    def start(self):
        if self._timer is None:
            self._timer = QTimer()
            self._timer.setInterval(self.interval_ms)
            self._timer.timeout.connect(self._on_tick)
        self._running = True
        self._timer.start()

    @pyqtSlot()
    def stop(self):
        self._running = False
        if self._timer is not None:
            self._timer.stop()

    def _emit_status(self, status: bool):
        if status != self._last_status:
            self._last_status = status
            self.plc_status_changed.emit(status)

    def _on_tick(self):
        try:
            data = self.plc.read_all()
            status = self.plc.is_connected()
            self._emit_status(status)
            if data:
                # Aplicar calibraciones por túnel antes de emitir
                for tid, td in data.items():
                    cfg = self.tunnels_map.get(tid)
                    if cfg and getattr(cfg, "calibrations", None):
                        cal = cfg.calibrations
                        try:
                            td.temp_ambiente = float(td.temp_ambiente) + float(cal.get("temp_ambiente", 0.0))
                            td.temp_pulpa1 = float(td.temp_pulpa1) + float(cal.get("temp_pulpa1", 0.0))
                            td.temp_pulpa2 = float(td.temp_pulpa2) + float(cal.get("temp_pulpa2", 0.0))
                        except Exception:
                            pass
                # Emitir
                self.updated.emit(data)
        except Exception:
            self._emit_status(False)

    @pyqtSlot(int, float)
    def write_setpoint(self, tunnel_id: int, value: float):
        try:
            ok = self.plc.write_setpoint(tunnel_id, value)
            if not ok:
                self._emit_status(False)
        except Exception:
            self._emit_status(False)

    @pyqtSlot(int, bool)
    def write_estado(self, tunnel_id: int, value: bool):
        try:
            ok = self.plc.write_estado(tunnel_id, value)
            if not ok:
                self._emit_status(False)
        except Exception:
            self._emit_status(False)

    @pyqtSlot(int, dict)
    def update_tunnel_tags(self, tunnel_id: int, tags: dict):
        """Actualizar los tags de un túnel en el PLC activo (en caliente)."""
        try:
            if tunnel_id in self.plc.tunnels_map:
                self.plc.tunnels_map[tunnel_id].tags = tags
            if tunnel_id in self.tunnels_map:
                self.tunnels_map[tunnel_id].tags = tags
        except Exception:
            # Si falla, no derribar; el siguiente ciclo reportará estado
            self._emit_status(False)

    @pyqtSlot(int, dict)
    def update_tunnel_calibrations(self, tunnel_id: int, cal: dict):
        """Actualizar calibraciones (offsets) en caliente."""
        try:
            if tunnel_id in self.tunnels_map:
                self.tunnels_map[tunnel_id].calibrations = cal
            if tunnel_id in self.plc.tunnels_map:
                # Mantener en el objeto también
                self.plc.tunnels_map[tunnel_id].calibrations = cal
        except Exception:
            self._emit_status(False)
