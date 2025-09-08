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
                # Convertir TunnelData a dict serializable si fuera necesario; aquí lo pasamos tal cual
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
