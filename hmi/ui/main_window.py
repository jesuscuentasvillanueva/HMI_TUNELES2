from __future__ import annotations

from typing import Dict, List, Optional

from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QSizePolicy,
    QFrame,
)

from ..config import ConfigManager
from ..models import PLCConfig, TunnelConfig, TunnelData, AppConfig
from .dashboard_view import DashboardView
from .tunnel_detail_view import TunnelDetailView
from .settings_view import SettingsView
from time import strftime, localtime


class MainWindow(QMainWindow):
    request_setpoint = pyqtSignal(int, float)
    request_setpoint_p1 = pyqtSignal(int, float)
    request_setpoint_p2 = pyqtSignal(int, float)
    request_estado = pyqtSignal(int, bool)
    apply_settings = pyqtSignal(object)
    update_tunnel_tags = pyqtSignal(int, dict)
    update_tunnel_calibrations = pyqtSignal(int, dict)

    def __init__(self, tunnels: List[TunnelConfig], initial_plc_connected: bool = False):
        super().__init__()
        self.setWindowTitle("HMI Túneles")
        self.tunnels = tunnels
        self.tunnels_map: Dict[int, TunnelConfig] = {t.id: t for t in tunnels}
        self._last_data: Dict[int, TunnelData] = {}
        self._current_tunnel_id: Optional[int] = None

        # Construcción UI
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # Barra superior en un QFrame para mejor estilado
        top_frame = QFrame()
        top_frame.setObjectName("TopBar")
        top = QHBoxLayout(top_frame)
        top.setContentsMargins(12, 8, 12, 8)
        top.setSpacing(8)

        self.lbl_status = QLabel("PLC: Desconectado")
        self.lbl_status.setObjectName("TopStatusLabel")
        self.lbl_status.setProperty("connected", "false")

        # Reloj y última actualización
        self.lbl_clock = QLabel("")
        self.lbl_clock.setObjectName("ClockLabel")
        self.lbl_update = QLabel("Últ. act.: --:--:--")
        self.lbl_update.setObjectName("UpdateLabel")

        btn_go_dashboard = QPushButton("Tablero")
        btn_go_dashboard.setProperty("size", "lg")
        btn_go_dashboard.setMinimumHeight(44)
        btn_settings = QPushButton("Configuración")
        btn_settings.setProperty("size", "lg")
        btn_settings.setMinimumHeight(44)
        btn_settings.setObjectName("Primary")

        top.addWidget(self.lbl_status)
        top.addSpacing(12)
        top.addWidget(self.lbl_clock)
        top.addSpacing(12)
        top.addWidget(self.lbl_update)
        top.addStretch(1)
        top.addWidget(btn_go_dashboard)
        top.addWidget(btn_settings)

        root.addWidget(top_frame)

        # Contenedor de vistas
        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.view_dashboard = DashboardView(self.tunnels)
        self.view_detail = TunnelDetailView()

        # Settings view con config actual
        self._cfg_manager = ConfigManager()
        cfg = self._cfg_manager.load_or_create_default()
        self.view_settings = SettingsView(cfg.plc)

        self.stack.addWidget(self.view_dashboard)  # index 0
        self.stack.addWidget(self.view_detail)     # index 1
        self.stack.addWidget(self.view_settings)   # index 2
        root.addWidget(self.stack, 1)

        # Señales de navegación
        self.view_dashboard.tunnel_clicked.connect(self._open_detail)
        self.view_detail.back.connect(lambda: self._navigate(0))
        self.view_settings.back.connect(lambda: self._navigate(0))
        btn_go_dashboard.clicked.connect(lambda: self._navigate(0))
        btn_settings.clicked.connect(lambda: self._navigate(2))

        # Reenvío de acciones de detalle hacia afuera
        self.view_detail.request_setpoint.connect(self.request_setpoint)
        self.view_detail.request_estado.connect(self.request_estado)
        self.view_detail.request_setpoint_p1.connect(self.request_setpoint_p1)
        self.view_detail.request_setpoint_p2.connect(self.request_setpoint_p2)
        self.view_detail.update_tunnel_tags.connect(self._on_update_tunnel_tags)
        self.view_detail.update_tunnel_tags.connect(self.update_tunnel_tags)
        self.view_detail.update_tunnel_calibrations.connect(self._on_update_tunnel_calibrations)
        self.view_detail.update_tunnel_calibrations.connect(self.update_tunnel_calibrations)

        # Aplicación de configuración
        self.view_settings.apply_settings.connect(self._apply_settings_and_back)

        # Estado inicial
        self.on_plc_status(initial_plc_connected)
        self._navigate(0)

        # Iniciar reloj en top bar
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)
        self._tick_clock()

    def _navigate(self, idx: int):
        self.stack.setCurrentIndex(idx)
        if idx == 0:
            self._current_tunnel_id = None

    def _open_detail(self, tunnel_id: int):
        self._current_tunnel_id = tunnel_id
        cfg = self.tunnels_map.get(tunnel_id)
        if cfg:
            self.view_detail.set_tunnel(cfg)
            # si hay datos recientes, actualizamos inmediatamente
            if tunnel_id in self._last_data:
                self.view_detail.update_data(self._last_data[tunnel_id])
        self._navigate(1)

    def _apply_settings_and_back(self, plc_cfg: PLCConfig):
        # Emitir hacia main.py para reiniciar PLC/poller
        self.apply_settings.emit(plc_cfg)
        # Refrescar vista de settings con valores (por si main ajusta algo)
        self.view_settings.set_values(plc_cfg)
        # Volver al tablero
        self._navigate(0)

    # Slots públicos para workers
    def on_data_update(self, data: Dict[int, TunnelData]):
        self._last_data = data
        self.view_dashboard.update_data(data)
        # Actualizar sello de tiempo de última actualización
        try:
            self.lbl_update.setText(f"Últ. act.: {strftime('%H:%M:%S', localtime())}")
        except Exception:
            pass
        # Si estamos en el detalle y hay datos del túnel actual, refrescar
        if self._current_tunnel_id and self._current_tunnel_id in data:
            try:
                self.view_detail.update_data(data[self._current_tunnel_id])
            except Exception:
                pass

    def _on_update_tunnel_calibrations(self, tunnel_id: int, cal: dict):
        # Guardar en config.json y en memoria local
        try:
            app_cfg = self._cfg_manager.load_or_create_default()
            for t in app_cfg.tunnels:
                if t.id == tunnel_id:
                    t.calibrations = cal
                    break
            self._cfg_manager.save(app_cfg)
            if tunnel_id in self.tunnels_map:
                self.tunnels_map[tunnel_id].calibrations = cal
        except Exception:
            pass

    def on_plc_status(self, connected: bool):
        if connected:
            self.lbl_status.setText("PLC: Conectado")
            self.lbl_status.setProperty("connected", "true")
        else:
            self.lbl_status.setText("PLC: Desconectado")
            self.lbl_status.setProperty("connected", "false")
        # re-polish to apply QSS based on property
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)

    def _tick_clock(self):
        self.lbl_clock.setText(strftime("%H:%M:%S", localtime()))

    def _on_update_tunnel_tags(self, tunnel_id: int, tags: dict):
        # Actualizar en memoria
        if tunnel_id in self.tunnels_map:
            self.tunnels_map[tunnel_id].tags = tags
        # Persistir en config.json
        try:
            app_cfg = self._cfg_manager.load_or_create_default()
            for t in app_cfg.tunnels:
                if t.id == tunnel_id:
                    t.tags = tags
                    break
            self._cfg_manager.save(app_cfg)
        except Exception:
            pass
