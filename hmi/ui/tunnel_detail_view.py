from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QDoubleSpinBox

from ..models import TunnelConfig, TunnelData
from typing import Optional


class TunnelDetailView(QWidget):
    request_setpoint = pyqtSignal(int, float)
    request_estado = pyqtSignal(int, bool)
    back = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.config: Optional[TunnelConfig] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.lbl_title = QLabel("Túnel")
        self.lbl_title.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(self.lbl_title)

        # Lecturas grandes
        self.lbl_amb = QLabel("Ambiente: --.- °C")
        self.lbl_p1 = QLabel("Pulpa 1: --.- °C")
        self.lbl_p2 = QLabel("Pulpa 2: --.- °C")
        self.lbl_sp = QLabel("Setpoint: --.- °C")
        for w in (self.lbl_amb, self.lbl_p1, self.lbl_p2, self.lbl_sp):
            w.setProperty("class", "bigValue")
            layout.addWidget(w)

        # Controles
        controls = QHBoxLayout()
        self.btn_on = QPushButton("Encender")
        self.btn_on.setObjectName("Primary")
        self.btn_off = QPushButton("Apagar")
        self.btn_off.setObjectName("Danger")
        controls.addWidget(self.btn_on)
        controls.addWidget(self.btn_off)

        sp_layout = QHBoxLayout()
        self.sp_setpoint = QDoubleSpinBox()
        self.sp_setpoint.setDecimals(1)
        self.sp_setpoint.setRange(-40.0, 60.0)
        self.sp_setpoint.setSingleStep(0.5)
        self.btn_apply_sp = QPushButton("Aplicar Setpoint")
        sp_layout.addWidget(self.sp_setpoint)
        sp_layout.addWidget(self.btn_apply_sp)

        layout.addLayout(controls)
        layout.addLayout(sp_layout)

        self.btn_back = QPushButton("Volver")
        layout.addWidget(self.btn_back)

        # Señales
        self.btn_back.clicked.connect(self.back.emit)
        self.btn_on.clicked.connect(self._on_on)
        self.btn_off.clicked.connect(self._on_off)
        self.btn_apply_sp.clicked.connect(self._on_apply_sp)

    def set_tunnel(self, config: TunnelConfig):
        self.config = config
        self.lbl_title.setText(config.name)

    def update_data(self, data: TunnelData):
        self.lbl_amb.setText(f"Ambiente: {data.temp_ambiente:.1f} °C")
        self.lbl_p1.setText(f"Pulpa 1: {data.temp_pulpa1:.1f} °C")
        self.lbl_p2.setText(f"Pulpa 2: {data.temp_pulpa2:.1f} °C")
        self.lbl_sp.setText(f"Setpoint: {data.setpoint:.1f} °C")
        self.sp_setpoint.setValue(data.setpoint)

    def _on_on(self):
        if self.config:
            self.request_estado.emit(self.config.id, True)

    def _on_off(self):
        if self.config:
            self.request_estado.emit(self.config.id, False)

    def _on_apply_sp(self):
        if self.config:
            self.request_setpoint.emit(self.config.id, float(self.sp_setpoint.value()))
