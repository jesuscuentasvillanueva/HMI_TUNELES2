from __future__ import annotations

from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QSize, QEvent
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QGridLayout, QSizePolicy, QHBoxLayout, QWidget

from ..models import TunnelData, TunnelConfig


class TunnelCard(QFrame):
    clicked = pyqtSignal(int)
    content_height_changed = pyqtSignal(int)

    def __init__(self, config: TunnelConfig):
        super().__init__()
        self.setObjectName("TunnelCard")
        self.config = config
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._min_h_cache = 0
        # Sin sombra para máxima nitidez del texto
        self._build_ui()
        self._install_click_filter()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 8, 12, 16)
        self.layout.setSpacing(8)

        self.header_frame = QFrame()
        self.header_frame.setObjectName("CardHeader")
        self.header_layout = QHBoxLayout(self.header_frame)
        self.header_layout.setContentsMargins(8, 4, 8, 8)
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
        self.grid.setVerticalSpacing(12)

        # 4 filas: etiqueta a la izquierda, valor a la derecha
        lbl_amb_t = QLabel("Amb"); lbl_amb_t.setProperty("class", "metricLabel"); lbl_amb_t.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_amb_val = QLabel("--.- °C"); self.lbl_amb_val.setProperty("class", "metricValue"); self.lbl_amb_val.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lbl_p1_t = QLabel("P1"); lbl_p1_t.setProperty("class", "metricLabel"); lbl_p1_t.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_p1_val = QLabel("--.- °C"); self.lbl_p1_val.setProperty("class", "metricValue"); self.lbl_p1_val.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lbl_p2_t = QLabel("P2"); lbl_p2_t.setProperty("class", "metricLabel"); lbl_p2_t.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_p2_val = QLabel("--.- °C"); self.lbl_p2_val.setProperty("class", "metricValue"); self.lbl_p2_val.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lbl_sp_t = QLabel("SP"); lbl_sp_t.setProperty("class", "metricLabel"); lbl_sp_t.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_sp_val = QLabel("--.- °C"); self.lbl_sp_val.setProperty("class", "metricValue"); self.lbl_sp_val.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.grid.addWidget(lbl_amb_t, 0, 0); self.grid.addWidget(self.lbl_amb_val, 0, 1)
        self.grid.addWidget(lbl_p1_t, 1, 0); self.grid.addWidget(self.lbl_p1_val, 1, 1)
        self.grid.addWidget(lbl_p2_t, 2, 0); self.grid.addWidget(self.lbl_p2_val, 2, 1)
        self.grid.addWidget(lbl_sp_t, 3, 0); self.grid.addWidget(self.lbl_sp_val, 3, 1)
        # Altura mínima por fila para evitar recortes y estiramiento de valores
        for r in range(4):
            self.grid.setRowMinimumHeight(r, 42)
        self.grid.setColumnMinimumWidth(0, 44)
        self.grid.setColumnStretch(0, 0)
        self.grid.setColumnStretch(1, 1)

        self.layout.addLayout(self.grid)

        # Density property default
        self.setProperty("density", "normal")

        # Asegurar alturas mínimas adecuadas una vez aplicado el estilo
        QTimer.singleShot(0, self._ensure_min_heights)
        QTimer.singleShot(0, self._recalc_min_height)

    def mousePressEvent(self, event):
        self.clicked.emit(self.config.id)

    def update_data(self, data: TunnelData):
        self.lbl_amb_val.setText(f"{data.temp_ambiente:.1f} °C")
        self.lbl_p1_val.setText(f"{data.temp_pulpa1:.1f} °C")
        self.lbl_p2_val.setText(f"{data.temp_pulpa2:.1f} °C")
        self.lbl_sp_val.setText(f"{data.setpoint:.1f} °C")
        # Sin coloreo por nivel para máxima legibilidad

        # Tooltip informativo
        if getattr(data, "deshielo_activo", False):
            state_text = "Deshielo"
            state_prop = "defrost"
        else:
            state_text = "Encendido" if data.estado else "Apagado"
            state_prop = "on" if data.estado else "off"
        self.setToolTip(
            f"{self.config.name}\nAmbiente: {data.temp_ambiente:.1f} °C\nPulpa 1: {data.temp_pulpa1:.1f} °C\nPulpa 2: {data.temp_pulpa2:.1f} °C\nSetpoint: {data.setpoint:.1f} °C\nEstado: {state_text}"
        )
        self.state_tag.setText(state_text)
        self.state_tag.setProperty("state", state_prop)
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
        lbl_v.setMinimumHeight(28)
        lbl_v.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        return w, lbl_v

    def _ensure_min_heights(self):
        labels = [self.lbl_amb_val, self.lbl_p1_val, self.lbl_p2_val, self.lbl_sp_val]
        max_h = 0
        for lbl in labels:
            fm = lbl.fontMetrics()
            h = max(28, fm.height() + 8)
            lbl.setMinimumHeight(h)
            max_h = max(max_h, h)
        # Ajustar altura mínima por fila en función del texto renderizado
        for r in range(4):
            self.grid.setRowMinimumHeight(r, max_h + 6)
        self._recalc_min_height()

    def _recalc_min_height(self):
        try:
            m = self.layout.contentsMargins()
            header_h = self.header_frame.sizeHint().height()
            rows_h = sum(self.grid.rowMinimumHeight(r) for r in range(4))
            rows_h += (self.grid.verticalSpacing() or 0) * 3
            total = m.top() + header_h + rows_h + m.bottom()
            self._min_h_cache = int(total)
            self.setFixedHeight(self._min_h_cache)
            self.updateGeometry()
            self.content_height_changed.emit(self._min_h_cache)
        except Exception:
            pass

    # --- Click support on all child widgets ---
    def _install_click_filter(self):
        try:
            self.installEventFilter(self)
            for w in self.findChildren(QWidget):
                w.installEventFilter(self)
        except Exception:
            pass

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            try:
                if hasattr(event, 'button') and (event.button() & Qt.LeftButton):
                    self.clicked.emit(self.config.id)
                    return True
            except Exception:
                pass
        return super().eventFilter(obj, event)

    def sizeHint(self):
        # Altura basada en el contenido calculado, ancho razonable por defecto
        base_w = max(240, self.minimumWidth())
        base_h = max(180, int(self._min_h_cache) if self._min_h_cache else 0)
        return QSize(base_w, base_h)

    # Ajuste dinámico para encajar en el alto objetivo sin scroll
    def apply_target_height(self, target_h: int):
        try:
            m = self.layout.contentsMargins()
            header_h = self.header_frame.sizeHint().height()
            inner = max(40, target_h - (m.top() + m.bottom()) - header_h)
            rows = 4
            spacing = self.grid.verticalSpacing() or 0
            avail_rows = max(1, inner - spacing * (rows - 1))
            per = max(22, int(avail_rows // rows))
            # Ajustar altura por fila
            for r in range(rows):
                self.grid.setRowMinimumHeight(r, per)
            # Ajustar minHeight de labels y tamaño de fuente para evitar recortes
            val_min = max(18, per - 4)
            labels = [self.lbl_amb_val, self.lbl_p1_val, self.lbl_p2_val, self.lbl_sp_val]
            for lbl in labels:
                lbl.setMinimumHeight(val_min)
                # Escalado de fuente si es muy bajo
                if per < 26:
                    lbl.setStyleSheet("font-size: 16px;")
                else:
                    lbl.setStyleSheet("")  # usar QSS global (18px)
            # Fijar la altura ofrecida por la tarjeta al layout
            total = m.top() + header_h + rows * per + spacing * (rows - 1) + m.bottom()
            self._min_h_cache = int(total)
            self.setFixedHeight(self._min_h_cache)
            self.updateGeometry()
        except Exception:
            pass
