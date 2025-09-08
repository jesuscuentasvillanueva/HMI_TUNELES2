from __future__ import annotations

from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QGridLayout, QSizePolicy, QHBoxLayout, QWidget

from ..models import TunnelData, TunnelConfig


class TunnelCard(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, config: TunnelConfig):
        super().__init__()
        self.setObjectName("TunnelCard")
        self.config = config
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Sin sombra para máxima nitidez del texto
        self._build_ui()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 8, 12, 12)
        self.layout.setSpacing(8)

        self.header_frame = QFrame()
        self.header_frame.setObjectName("CardHeader")
        self.header_layout = QHBoxLayout(self.header_frame)
        self.header_layout.setContentsMargins(8, 4, 8, 6)
        self.header_layout.setSpacing(8)
        self.status_dot = QLabel("")
        self.status_dot.setObjectName("StatusDot")
        self.status_dot.setFixedSize(10, 10)
        self.title = QLabel(self.config.name)
        self.title.setObjectName("CardTitle")
        self.title.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.title.setWordWrap(False)
        self.state_tag = QLabel("-")
        self.state_tag.setObjectName("StateTag")
        self.header_layout.addWidget(self.status_dot, 0)
        self.header_layout.addWidget(self.title, 1)
        self.header_layout.addWidget(self.state_tag, 0, Qt.AlignRight)
        self.layout.addWidget(self.header_frame)

        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(10)

        # 4 filas: etiqueta a la izquierda, valor a la derecha
        lbl_amb_t = QLabel("Amb"); lbl_amb_t.setProperty("class", "metricLabel")
        self.lbl_amb_val = QLabel("--.- °C"); self.lbl_amb_val.setProperty("class", "metricValue"); self.lbl_amb_val.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lbl_p1_t = QLabel("P1"); lbl_p1_t.setProperty("class", "metricLabel")
        self.lbl_p1_val = QLabel("--.- °C"); self.lbl_p1_val.setProperty("class", "metricValue"); self.lbl_p1_val.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lbl_p2_t = QLabel("P2"); lbl_p2_t.setProperty("class", "metricLabel")
        self.lbl_p2_val = QLabel("--.- °C"); self.lbl_p2_val.setProperty("class", "metricValue"); self.lbl_p2_val.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lbl_sp_t = QLabel("SP"); lbl_sp_t.setProperty("class", "metricLabel")
        self.lbl_sp_val = QLabel("--.- °C"); self.lbl_sp_val.setProperty("class", "metricValue"); self.lbl_sp_val.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.grid.addWidget(lbl_amb_t, 0, 0); self.grid.addWidget(self.lbl_amb_val, 0, 1)
        self.grid.addWidget(lbl_p1_t, 1, 0); self.grid.addWidget(self.lbl_p1_val, 1, 1)
        self.grid.addWidget(lbl_p2_t, 2, 0); self.grid.addWidget(self.lbl_p2_val, 2, 1)
        self.grid.addWidget(lbl_sp_t, 3, 0); self.grid.addWidget(self.lbl_sp_val, 3, 1)
        # Altura mínima por fila para evitar recortes y estiramiento de valores
        for r in range(4):
            self.grid.setRowMinimumHeight(r, 36)
        self.grid.setColumnStretch(0, 0)
        self.grid.setColumnStretch(1, 1)

        self.layout.addLayout(self.grid)
        self.layout.addStretch(1)

        # Density property default
        self.setProperty("density", "normal")

        # Asegurar alturas mínimas adecuadas una vez aplicado el estilo
        QTimer.singleShot(0, self._ensure_min_heights)

    def mousePressEvent(self, event):
        self.clicked.emit(self.config.id)

    def update_data(self, data: TunnelData):
        self.lbl_amb_val.setText(f"{data.temp_ambiente:.1f} °C")
        self.lbl_p1_val.setText(f"{data.temp_pulpa1:.1f} °C")
        self.lbl_p2_val.setText(f"{data.temp_pulpa2:.1f} °C")
        self.lbl_sp_val.setText(f"{data.setpoint:.1f} °C")
        # Sin coloreo por nivel para máxima legibilidad

        # Tooltip informativo
        self.setToolTip(
            f"{self.config.name}\nAmbiente: {data.temp_ambiente:.1f} °C\nPulpa 1: {data.temp_pulpa1:.1f} °C\nPulpa 2: {data.temp_pulpa2:.1f} °C\nSetpoint: {data.setpoint:.1f} °C\nEstado: {'Encendido' if data.estado else 'Apagado'}"
        )
        if data.estado:
            self.state_tag.setText("Encendido")
            self.state_tag.setProperty("state", "on")
        else:
            self.state_tag.setText("Apagado")
            self.state_tag.setProperty("state", "off")
        # Update status dot color
        self.status_dot.setProperty("state", "on" if data.estado else "off")
        # Re-apply style to reflect property change on the chip and dot
        self.state_tag.style().unpolish(self.state_tag)
        self.state_tag.style().polish(self.state_tag)
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)
        # Dynamic property for QSS reactive border
        self.setProperty("on", "true" if data.estado else "false")
        self.header_frame.setProperty("on", "true" if data.estado else "false")
        # Re-apply style to reflect property change
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_density(self, compact: bool):
        # Ajusta propiedades y espaciados para modo compacto
        self.setProperty("density", "compact" if compact else "normal")
        if compact:
            self.layout.setContentsMargins(8, 6, 8, 8)
            self.layout.setSpacing(6)
            self.header_layout.setContentsMargins(6, 3, 6, 4)
            self.header_layout.setSpacing(6)
            self.grid.setHorizontalSpacing(12)
            self.grid.setVerticalSpacing(6)
        else:
            self.layout.setContentsMargins(12, 8, 12, 12)
            self.layout.setSpacing(8)
            self.header_layout.setContentsMargins(8, 4, 8, 6)
            self.header_layout.setSpacing(8)
            self.grid.setHorizontalSpacing(16)
            self.grid.setVerticalSpacing(8)
        self.style().unpolish(self); self.style().polish(self); self.update()

    def _metric_widget(self, title: str):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl_t = QLabel(title)
        lbl_t.setProperty("class", "metricLabel")
        lbl_v = QLabel("--.- °C")
        lbl_v.setProperty("class", "metricValue")
        lbl_v.setWordWrap(False)
        lbl_v.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lbl_v.setMinimumWidth(95)
        lbl_v.setMinimumHeight(26)
        lbl_v.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        return w, lbl_v

    def _ensure_min_heights(self):
        labels = [self.lbl_amb_val, self.lbl_p1_val, self.lbl_p2_val, self.lbl_sp_val]
        for lbl in labels:
            fm = lbl.fontMetrics()
            lbl.setMinimumHeight(fm.height() + 6)
