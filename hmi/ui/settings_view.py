from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QPushButton,
)

from ..models import PLCConfig
from typing import Optional


class SettingsView(QWidget):
    apply_settings = pyqtSignal(object)
    back = pyqtSignal()
    test_connection = pyqtSignal(object)
    # Reutiliza el mismo patrón que el DetailView para guardar prefs UI
    update_ui_pref = pyqtSignal(str, object)

    def __init__(self, plc_cfg: PLCConfig):
        super().__init__()
        self._build_ui()
        self.set_values(plc_cfg)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Configuración de Conexión")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)

        # Controles
        self.ed_ip = QLineEdit()
        self.ed_ip.setPlaceholderText("IP del PLC (ej: 192.168.0.1)")

        self.sp_rack = QSpinBox()
        self.sp_rack.setRange(0, 10)

        self.sp_slot = QSpinBox()
        self.sp_slot.setRange(0, 10)

        self.sp_port = QSpinBox()
        self.sp_port.setRange(1, 65535)

        self.sp_poll = QSpinBox()
        self.sp_poll.setRange(200, 30000)
        self.sp_poll.setSingleStep(100)

        self.chk_sim = QCheckBox("Simulación")

        # Preferencias de UI
        self.sp_visible = QSpinBox()
        self.sp_visible.setRange(1, 200)
        self.sp_from = QSpinBox()
        self.sp_from.setRange(1, 200)
        self.sp_count = QSpinBox()
        self.sp_count.setRange(1, 200)

        def add_row(label: str, w):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(w)
            layout.addLayout(row)

        add_row("IP:", self.ed_ip)
        add_row("Rack:", self.sp_rack)
        add_row("Slot:", self.sp_slot)
        add_row("Puerto:", self.sp_port)
        add_row("Intervalo (ms):", self.sp_poll)
        add_row("Modo:", self.chk_sim)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Preferencias de Interfaz"))
        add_row("Túneles visibles:", self.sp_visible)
        add_row("Desde túnel:", self.sp_from)
        add_row("Cantidad:", self.sp_count)

        # Botones
        btns = QHBoxLayout()
        self.btn_test = QPushButton("Probar conexión")
        self.btn_apply = QPushButton("Aplicar")
        self.btn_apply.setObjectName("Primary")
        self.btn_back = QPushButton("Volver")
        btns.addWidget(self.btn_test)
        btns.addStretch(1)
        btns.addWidget(self.btn_apply)
        btns.addWidget(self.btn_back)
        layout.addLayout(btns)

        # Resultado de prueba
        self.lbl_test = QLabel("")
        self.lbl_test.setWordWrap(True)
        layout.addWidget(self.lbl_test)

        # Conexiones
        self.btn_back.clicked.connect(self.back.emit)
        self.btn_apply.clicked.connect(self._emit_apply)
        self.btn_test.clicked.connect(self._emit_test)

    def set_values(self, cfg: PLCConfig):
        self.ed_ip.setText(cfg.ip)
        self.sp_rack.setValue(cfg.rack)
        self.sp_slot.setValue(cfg.slot)
        self.sp_port.setValue(cfg.port)
        self.sp_poll.setValue(cfg.poll_interval_ms)
        self.chk_sim.setChecked(cfg.simulation)

    def set_ui_prefs(self, ui: dict, total_tunnels: int):
        try:
            total = max(1, int(total_tunnels))
            self.sp_visible.setRange(1, total)
            val = int(ui.get("dashboard_visible_tunnels", total) or total)
            if val < 1:
                val = total
            val = min(max(1, val), total)
            self.sp_visible.setValue(val)
            # Rango desde (no se clampa a total para permitir nomenclaturas > total)
            self.sp_count.setRange(1, total)
            a = ui.get("dashboard_range_from")
            b = ui.get("dashboard_range_to")
            if a is not None and b is not None:
                try:
                    aa = max(1, int(a))  # no clamp superior
                    bb = max(1, int(b))  # no clamp superior
                    cnt = max(1, min(bb - aa + 1, total))
                    self.sp_from.setValue(aa)
                    self.sp_count.setValue(cnt)
                except Exception:
                    self.sp_from.setValue(1)
                    self.sp_count.setValue(total)
            else:
                # Por defecto sin rango: todo
                self.sp_from.setValue(1)
                # Si hay visible explícito, úsalo como cantidad por defecto
                try:
                    self.sp_count.setValue(int(val))
                except Exception:
                    self.sp_count.setValue(total)
        except Exception:
            # fallback seguro
            self.sp_visible.setValue(max(1, int(total_tunnels) if total_tunnels else 1))
            try:
                self.sp_from.setValue(1)
                self.sp_count.setValue(max(1, int(total_tunnels) if total_tunnels else 1))
            except Exception:
                pass

    def _emit_apply(self):
        cfg = PLCConfig(
            ip=self.ed_ip.text().strip() or "192.168.0.1",
            rack=int(self.sp_rack.value()),
            slot=int(self.sp_slot.value()),
            port=int(self.sp_port.value()),
            poll_interval_ms=int(self.sp_poll.value()),
            simulation=bool(self.chk_sim.isChecked()),
        )
        self.apply_settings.emit(cfg)
        # Sincronizar visibles con Cantidad (consistencia de lo que realmente se muestra)
        try:
            self.update_ui_pref.emit("dashboard_visible_tunnels", int(self.sp_count.value()))
        except Exception:
            pass
        # Emitir rango de túneles (desde/hasta)
        try:
            a = int(self.sp_from.value())
            cnt = int(self.sp_count.value())
            b = max(a, a + cnt - 1)
            self.update_ui_pref.emit("dashboard_range_from", a)
            self.update_ui_pref.emit("dashboard_range_to", b)
        except Exception:
            pass

    def _emit_test(self):
        cfg = PLCConfig(
            ip=self.ed_ip.text().strip() or "192.168.0.1",
            rack=int(self.sp_rack.value()),
            slot=int(self.sp_slot.value()),
            port=int(self.sp_port.value()),
            poll_interval_ms=int(self.sp_poll.value()),
            simulation=bool(self.chk_sim.isChecked()),
        )
        # Indicar estado inicial
        self.show_test_result("Probando conexión...", None)
        self.test_connection.emit(cfg)

    def show_test_result(self, text: str, success: Optional[bool]):
        # success True/False/None (en curso)
        if success is True:
            self.lbl_test.setStyleSheet("color: #10b981; font-weight: 600;")
        elif success is False:
            self.lbl_test.setStyleSheet("color: #f87171; font-weight: 600;")
        else:
            self.lbl_test.setStyleSheet("color: #9fb0bf;")
        self.lbl_test.setText(text)
