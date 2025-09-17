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
    request_deshielo = pyqtSignal(int)
    request_deshielo_set = pyqtSignal(int, bool)
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

        # Pequeña etiqueta para errores de PLC
        self.lbl_err = QLabel("")
        self.lbl_err.setObjectName("TopErrorLabel")
        self.lbl_err.setStyleSheet("color: #f87171;")
        self.lbl_err.setWordWrap(False)

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
        top.addSpacing(12)
        top.addWidget(self.lbl_err)
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
        self._app_cfg = self._cfg_manager.load_or_create_default()
        self.view_settings = SettingsView(self._app_cfg.plc)
        # Inicializar preferencias de UI en Settings (número de túneles visibles)
        try:
            self.view_settings.set_ui_prefs(self._app_cfg.ui, len(self.tunnels))
        except Exception:
            pass

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
        # Deshielo
        try:
            self.view_detail.request_deshielo_set.connect(self.request_deshielo_set)
        except Exception:
            pass
        # Compatibilidad antigua (si existiera señal simple)
        try:
            self.view_detail.request_deshielo.connect(self.request_deshielo)
        except Exception:
            pass
        self.view_detail.update_tunnel_tags.connect(self._on_update_tunnel_tags)
        self.view_detail.update_tunnel_tags.connect(self.update_tunnel_tags)
        self.view_detail.update_tunnel_calibrations.connect(self._on_update_tunnel_calibrations)
        self.view_detail.update_tunnel_calibrations.connect(self.update_tunnel_calibrations)
        # Preferencias de UI (colapsables, etc.)
        try:
            self.view_detail.apply_ui_prefs(self._app_cfg.ui)
            self.view_detail.update_ui_pref.connect(self._on_update_ui_pref)
        except Exception:
            pass
        # Escuchar cambios de preferencias desde Settings y aplicarlos al dashboard
        try:
            self.view_settings.update_ui_pref.connect(self._on_update_ui_pref)
        except Exception:
            pass

        # Aplicación de configuración
        self.view_settings.apply_settings.connect(self._apply_settings_and_back)

        # Estado inicial
        self.on_plc_status(initial_plc_connected)
        self._navigate(0)
        # Aplicar límite de túneles visibles si está configurado
        try:
            vis = self._app_cfg.ui.get("dashboard_visible_tunnels")
            if vis is not None and hasattr(self.view_dashboard, "set_visible_limit"):
                self.view_dashboard.set_visible_limit(int(vis))
        except Exception:
            pass

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
        # Si estamos en el detalle, refrescar inmediatamente el túnel activo
        if self._current_tunnel_id and self._current_tunnel_id in data:
            try:
                self.view_detail.update_data(data[self._current_tunnel_id])
            except Exception:
                pass

    def _on_update_ui_pref(self, key: str, value):
        # Guardar preferencia en config.json
        try:
            self._app_cfg.ui[key] = value
            self._cfg_manager.save(self._app_cfg)
        except Exception:
            pass
        # Aplicar si es la preferencia de túneles visibles
        if key == "dashboard_visible_tunnels":
            try:
                if hasattr(self.view_dashboard, "set_visible_limit"):
                    self.view_dashboard.set_visible_limit(int(value))
            except Exception:
                pass
        # Si estamos en el detalle y hay datos del túnel actual, refrescar
        if self._current_tunnel_id and self._current_tunnel_id in self._last_data:
            try:
                self.view_detail.update_data(self._last_data[self._current_tunnel_id])
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
        # Propagar a la vista de detalle para habilitar/deshabilitar acciones
        try:
            self.view_detail.set_online(connected)
        except Exception:
            pass

    def on_plc_error(self, message: str):
        # Mostrar texto breve y guardar detalle en tooltip
        self.lbl_status.setToolTip(message or "")
        # texto acotado
        short = message or ""
        if len(short) > 80:
            short = short[:77] + "..."
        self.lbl_err.setText(short)
        # limpiar tras unos segundos
        try:
            QTimer.singleShot(7000, lambda: self.lbl_err.setText(""))
        except Exception:
            pass

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
