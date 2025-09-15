from __future__ import annotations

from typing import Dict, List, Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot
from time import time

from .models import TunnelConfig, TunnelData
from .plc_client import BasePLC


class Poller(QObject):
    updated = pyqtSignal(dict)  # Dict[int, TunnelData]
    plc_status_changed = pyqtSignal(bool)
    plc_error = pyqtSignal(str)
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
        # Seguimiento de tiempo de enfriamiento (inicio del ciclo ON por túnel)
        self._on_since: Dict[int, Optional[float]] = {}

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
        try:
            self.plc.disconnect()
        except Exception:
            pass

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
                # Calcular tiempo de enfriamiento por túnel
                now = time()
                for tid, td in data.items():
                    if td.estado:
                        start = self._on_since.get(tid)
                        if not start:
                            # iniciar ciclo ON ahora
                            self._on_since[tid] = now
                            start = now
                        td.tiempo_enfriamiento = max(0.0, float(now - start))
                    else:
                        # reset si está apagado
                        self._on_since[tid] = None
                        td.tiempo_enfriamiento = 0.0
                self.updated.emit(data)
            if not status:
                # Enviar último error si disponible
                err = self.plc.last_error()
                if err:
                    self.plc_error.emit(str(err))
        except Exception:
            self._emit_status(False)

    @pyqtSlot(int, bool)
    def set_deshielo(self, tunnel_id: int, on: bool):
        """Activa o desactiva deshielo escribiendo un tag de ESTADO (no pulso).
        Orden de preferencia de tag a escribir (BOOL):
          deshielo_mando, deshielo_set, deshielo_onoff, deshielo_activo
        """
        try:
            tags = self.tunnels_map.get(tunnel_id).tags if tunnel_id in self.tunnels_map else {}
        except Exception:
            tags = {}
        try:
            write_key = None
            for k in ("deshielo_mando", "deshielo_set", "deshielo_onoff", "deshielo_activo"):
                if k in tags:
                    write_key = k
                    break
            if write_key is None:
                # No existe tag de estado configurado: intentamos última opción con deshielo_activo
                write_key = "deshielo_activo"
            ok = self.plc.write_by_key(tunnel_id, write_key, bool(on))
            if not ok:
                self._emit_status(False)
                return
        except Exception:
            self._emit_status(False)
            try:
                err = self.plc.last_error()
                if err:
                    self.plc_error.emit(str(err))
            except Exception:
                pass

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
            # Si existen tags de comando por pulso, usarlos
            key = None
            try:
                tags = self.tunnels_map.get(tunnel_id).tags if tunnel_id in self.tunnels_map else {}
            except Exception:
                tags = {}
            if value and tags and "cmd_encender" in tags:
                key = "cmd_encender"
            elif (not value) and tags and "cmd_apagar" in tags:
                key = "cmd_apagar"

            if key:
                ok = self.plc.write_by_key(tunnel_id, key, True)
                if not ok:
                    self._emit_status(False)
                    return
                # Generar pulso: volver a 0 tras 200 ms
                QTimer.singleShot(200, lambda tid=tunnel_id, k=key: self.plc.write_by_key(tid, k, False))
            else:
                # Fallback: escribir directamente el estado booleano
                ok = self.plc.write_estado(tunnel_id, value)
                if not ok:
                    self._emit_status(False)
        except Exception:
            self._emit_status(False)

    @pyqtSlot(int, float)
    def write_setpoint_p1(self, tunnel_id: int, value: float):
        try:
            ok = self.plc.write_setpoint_p1(tunnel_id, value)
            if not ok:
                self._emit_status(False)
        except Exception:
            self._emit_status(False)

    @pyqtSlot(int, float)
    def write_setpoint_p2(self, tunnel_id: int, value: float):
        try:
            ok = self.plc.write_setpoint_p2(tunnel_id, value)
            if not ok:
                self._emit_status(False)
        except Exception:
            self._emit_status(False)

    @pyqtSlot(int)
    def trigger_deshielo(self, tunnel_id: int):
        """Activa un ciclo de deshielo. Preferentemente pulsa el tag cmd_deshielo.
        Fallback: si no existe cmd_deshielo, intenta escribir deshielo_activo True por 30s.
        """
        try:
            tags = self.tunnels_map.get(tunnel_id).tags if tunnel_id in self.tunnels_map else {}
        except Exception:
            tags = {}
        try:
            if tags and "cmd_deshielo" in tags:
                ok = self.plc.write_by_key(tunnel_id, "cmd_deshielo", True)
                if not ok:
                    self._emit_status(False)
                    return
                # pulso corto por seguridad
                QTimer.singleShot(200, lambda tid=tunnel_id: self.plc.write_by_key(tid, "cmd_deshielo", False))
                return
            # Fallback simulado (no recomendable en PLC real): togglear estado
            ok = self.plc.write_by_key(tunnel_id, "deshielo_activo", True)
            if not ok:
                self._emit_status(False)
                return
            QTimer.singleShot(30000, lambda tid=tunnel_id: self.plc.write_by_key(tid, "deshielo_activo", False))
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
            # Intentar escribir a PLC si existen tags de calibración
            for key_src, key_tag in (
                ("temp_ambiente", "cal_temp_ambiente"),
                ("temp_pulpa1", "cal_temp_pulpa1"),
                ("temp_pulpa2", "cal_temp_pulpa2"),
            ):
                try:
                    if key_src in cal:
                        self.plc.write_by_key(tunnel_id, key_tag, float(cal[key_src]))
                except Exception:
                    pass
        except Exception:
            self._emit_status(False)
