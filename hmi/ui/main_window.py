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
from ..models import PLCConfig, TunnelConfig, TunnelData
from .dashboard_view import DashboardView
from .tunnel_detail_view import TunnelDetailView
from .settings_view import SettingsView
from time import strftime, localtime


class MainWindow(QMainWindow):
    request_setpoint = pyqtSignal(int, float)
    request_estado = pyqtSignal(int, bool)
    apply_settings = pyqtSignal(object)

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
        btn_settings = QPushButton("Configuración")
        btn_settings.setObjectName("Primary")

        # Toggle de densidad
        self.btn_density = QPushButton("Denso")
        self.btn_density.setObjectName("DensityToggle")
        self.btn_density.setCheckable(True)

        top.addWidget(self.lbl_status)
        top.addSpacing(12)
        top.addWidget(self.lbl_clock)
        top.addSpacing(12)
        top.addWidget(self.lbl_update)
        top.addStretch(1)
        top.addWidget(btn_go_dashboard)
        top.addWidget(btn_settings)
        top.addWidget(self.btn_density)

        root.addWidget(top_frame)

        # Contenedor de vistas
        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.view_dashboard = DashboardView(self.tunnels)
        self.view_detail = TunnelDetailView()

        # Settings view con config actual
        cfg = ConfigManager().load_or_create_default()
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
        self.btn_density.toggled.connect(self._toggle_density)

        # Reenvío de acciones de detalle hacia afuera
        self.view_detail.request_setpoint.connect(self.request_setpoint)
        self.view_detail.request_estado.connect(self.request_estado)

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
        if self._current_tunnel_id and self._current_tunnel_id in data:
            self.view_detail.update_data(data[self._current_tunnel_id])

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

    def _toggle_density(self, checked: bool):
        # True => compacto
        self.view_dashboard.set_density(checked)
        self.btn_density.setText("Cómodo" if checked else "Denso")

    def _tick_clock(self):
        self.lbl_clock.setText(strftime("%H:%M:%S", localtime()))
