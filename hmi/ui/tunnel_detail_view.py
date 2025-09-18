from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QDoubleSpinBox, QGridLayout, QSizePolicy, QDialog, QFormLayout, QSpinBox, QComboBox, QInputDialog, QMessageBox, QLineEdit, QFrame, QToolButton, QScrollArea, QScroller, QScrollerProperties

from ..models import TunnelConfig, TunnelData, TagAddress
from typing import Optional


class TunnelDetailView(QWidget):
    request_setpoint = pyqtSignal(int, float)
    request_estado = pyqtSignal(int, bool)
    update_tunnel_tags = pyqtSignal(int, dict)  # dict[str, TagAddress]
    update_tunnel_calibrations = pyqtSignal(int, dict)  # dict[str, float]
    request_setpoint_p1 = pyqtSignal(int, float)
    request_setpoint_p2 = pyqtSignal(int, float)
    back = pyqtSignal()
    # Preferencias UI (clave, valor)
    update_ui_pref = pyqtSignal(str, object)
    request_deshielo_set = pyqtSignal(int, bool)

    def __init__(self):
        super().__init__()
        self.config: Optional[TunnelConfig] = None
        # No mostrar direcciones de memoria (badges) en esta pantalla
        self._show_tag_badges: bool = False
        # Flags para no sobreescribir valores mientras el usuario edita
        self._in_update = False
        self._sp_dirty = False
        self._sp1_dirty = False
        self._sp2_dirty = False
        self._cal_amb_dirty = False
        self._cal_p1_dirty = False
        self._cal_p2_dirty = False
        self._step = 0.1
        self._defrost_active = False
        self._build_ui()

    def _build_ui(self):
        # Root layout con scroll para pantallas pequeñas
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        # Scroll táctil cómodo
        try:
            self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
            self.scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        except Exception:
            pass
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Header con estado
        self.header_frame = QFrame()
        self.header_frame.setObjectName("DetailHeader")
        header = QHBoxLayout(self.header_frame)
        header.setContentsMargins(10, 8, 10, 8)
        header.setSpacing(10)
        self.status_dot = QLabel("")
        self.status_dot.setObjectName("StatusDot")
        self.status_dot.setFixedSize(12, 12)
        self.lbl_title = QLabel("Túnel")
        self.lbl_title.setStyleSheet("font-size: 28px; font-weight: 800;")
        header.addWidget(self.status_dot)
        header.addWidget(self.lbl_title, 1)
        self.state_chip = QLabel("Apagado")
        self.state_chip.setObjectName("StateTag")
        self.state_chip.setProperty("size", "xl")
        self.state_chip.setProperty("state", "off")
        header.addWidget(self.state_chip, 0)
        layout.addWidget(self.header_frame)

        # Lecturas compactas 2x2 (etiqueta pequeña + valor grande)
        metrics = QGridLayout()
        metrics.setHorizontalSpacing(18)
        metrics.setVerticalSpacing(6)

        def metric_block(title: str):
            w = QWidget()
            vb = QVBoxLayout(w)
            vb.setContentsMargins(0, 0, 0, 0)
            vb.setSpacing(2)
            lbl = QLabel(title); lbl.setProperty("class", "metricLabel")
            val = QLabel("--.- °C"); val.setProperty("class", "bigValue"); val.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            vb.addWidget(lbl)
            vb.addWidget(val)
            return w, val

        amb_w, self.val_amb = metric_block("Ambiente")
        p1_w, self.val_p1 = metric_block("Pulpa 1")
        p2_w, self.val_p2 = metric_block("Pulpa 2")
        sp_w, self.val_sp = metric_block("Setpoint")
        # Métrica adicional: posición de válvula (%)
        valve_w = QWidget(); vb = QVBoxLayout(valve_w); vb.setContentsMargins(0,0,0,0); vb.setSpacing(2)
        lbl_valve = QLabel("Válvula"); lbl_valve.setProperty("class", "metricLabel")
        self.val_valve = QLabel("-- %"); self.val_valve.setProperty("class", "bigValue"); self.val_valve.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        vb.addWidget(lbl_valve); vb.addWidget(self.val_valve)
        # Métrica adicional: tiempo de enfriamiento (hh:mm:ss)
        time_w = QWidget(); vb_t = QVBoxLayout(time_w); vb_t.setContentsMargins(0,0,0,0); vb_t.setSpacing(2)
        lbl_time = QLabel("Tiempo"); lbl_time.setProperty("class", "metricLabel")
        self.val_time = QLabel("--:--:--"); self.val_time.setProperty("class", "bigValue"); self.val_time.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        vb_t.addWidget(lbl_time); vb_t.addWidget(self.val_time)

        metrics.addWidget(amb_w, 0, 0)
        metrics.addWidget(p1_w, 0, 1)
        metrics.addWidget(p2_w, 1, 0)
        metrics.addWidget(sp_w, 1, 1)
        metrics.addWidget(valve_w, 2, 0)
        metrics.addWidget(time_w, 2, 1)

        layout.addLayout(metrics)

        # Controles
        controls = QHBoxLayout()
        self.btn_on = QPushButton("Encender")
        self.btn_on.setObjectName("Primary")
        self.btn_on.setProperty("size", "lg")
        self.btn_on.setMinimumHeight(48)
        self.btn_on.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.btn_off = QPushButton("Apagar")
        self.btn_off.setObjectName("Danger")
        self.btn_off.setProperty("size", "lg")
        self.btn_off.setMinimumHeight(48)
        self.btn_off.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        controls.addWidget(self.btn_on)
        controls.addWidget(self.btn_off)
        # Botón Deshielo
        self.btn_defrost = QPushButton("Deshielo ON")
        self.btn_defrost.setObjectName("Warning")
        self.btn_defrost.setProperty("size", "lg")
        self.btn_defrost.setMinimumHeight(48)
        self.btn_defrost.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        controls.addWidget(self.btn_defrost)

        # Barra de paso alineada a la derecha
        step_bar = QHBoxLayout()
        step_bar.addStretch(1)
        lbl_step = QLabel("Paso"); lbl_step.setProperty("class", "metricLabel")
        self.cb_step = QComboBox(); self.cb_step.addItems(["0.1", "0.5", "1.0"]); self.cb_step.setCurrentText("0.1"); self.cb_step.setMinimumHeight(48); self.cb_step.setProperty("size", "lg")
        self.cb_step.currentTextChanged.connect(self._on_step_changed)
        step_bar.addWidget(lbl_step)
        step_bar.addWidget(self.cb_step)

        layout.addLayout(controls)
        layout.addLayout(step_bar)

        # Setpoints (General + Avanzados)
        self.sp_pulp_frame = QWidget()
        sp_pulp = QGridLayout(self.sp_pulp_frame)
        sp_pulp.setHorizontalSpacing(8)
        sp_pulp.setVerticalSpacing(6)
        # Columna 0 para etiquetas (angosta), 1-3 para contenido (elásticas)
        sp_pulp.setColumnStretch(0, 0)
        sp_pulp.setColumnStretch(1, 1)
        sp_pulp.setColumnStretch(2, 1)
        sp_pulp.setColumnStretch(3, 1)

        # Fila SP General
        self.lbl_sp_gen = QLabel("SP General")
        sp_pulp.addWidget(self.lbl_sp_gen, 0, 0)
        rowg = QWidget()
        row_g = QHBoxLayout(rowg)
        row_g.setContentsMargins(0, 0, 0, 0)
        row_g.setSpacing(8)
        self.btn_dec_sp = QPushButton("-0.1"); self.btn_dec_sp.setMinimumHeight(48); self.btn_dec_sp.setProperty("size", "lg")
        self.sp_setpoint = QDoubleSpinBox(); self.sp_setpoint.setDecimals(1); self.sp_setpoint.setRange(-40.0, 60.0); self.sp_setpoint.setSingleStep(0.1); self.sp_setpoint.setMinimumHeight(48); self.sp_setpoint.setProperty("size", "lg"); self.sp_setpoint.setMinimumWidth(180); self.sp_setpoint.setSuffix(" °C"); self.sp_setpoint.valueChanged.connect(self._on_sp_user_change)
        self.btn_inc_sp = QPushButton("+0.1"); self.btn_inc_sp.setMinimumHeight(48); self.btn_inc_sp.setProperty("size", "lg")
        self.btn_apply_sp = QPushButton("Aplicar Setpoint"); self.btn_apply_sp.setMinimumHeight(48); self.btn_apply_sp.setProperty("size", "lg"); self.btn_apply_sp.setEnabled(False)
        row_g.addWidget(self.btn_dec_sp)
        row_g.addWidget(self.sp_setpoint)
        row_g.addWidget(self.btn_inc_sp)
        row_g.addWidget(self.btn_apply_sp)
        sp_pulp.addWidget(rowg, 0, 1, 1, 3)

        layout.addWidget(self.sp_pulp_frame)

        # Contenido avanzado: SP Pulpa 1/2 dentro de sección colapsable
        sp_adv = QWidget()
        adv = QGridLayout(sp_adv)
        adv.setHorizontalSpacing(8)
        adv.setVerticalSpacing(6)
        adv.setColumnStretch(0, 0)
        adv.setColumnStretch(1, 1)
        adv.setColumnStretch(2, 1)
        adv.setColumnStretch(3, 1)
        self.lbl_sp_p1 = QLabel("SP Pulpa 1")
        self.lbl_sp_p2 = QLabel("SP Pulpa 2")
        adv.addWidget(self.lbl_sp_p1, 0, 0)
        adv.addWidget(self.lbl_sp_p2, 1, 0)
        # Fila P1
        self.row_p1 = QWidget()
        row1 = QHBoxLayout(self.row_p1)
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(8)
        self.btn_dec_sp_p1 = QPushButton("-0.1"); self.btn_dec_sp_p1.setMinimumHeight(48); self.btn_dec_sp_p1.setProperty("size", "lg")
        self.sp_setpoint_p1 = QDoubleSpinBox(); self.sp_setpoint_p1.setDecimals(1); self.sp_setpoint_p1.setRange(-40.0, 60.0); self.sp_setpoint_p1.setSingleStep(0.1); self.sp_setpoint_p1.setMinimumHeight(48); self.sp_setpoint_p1.setProperty("size", "lg"); self.sp_setpoint_p1.setSuffix(" °C")
        self.sp_setpoint_p1.valueChanged.connect(self._on_sp1_user_change)
        self.btn_inc_sp_p1 = QPushButton("+0.1"); self.btn_inc_sp_p1.setMinimumHeight(48); self.btn_inc_sp_p1.setProperty("size", "lg")
        self.btn_apply_sp_p1 = QPushButton("Aplicar SP P1"); self.btn_apply_sp_p1.setMinimumHeight(48); self.btn_apply_sp_p1.setProperty("size", "lg"); self.btn_apply_sp_p1.setEnabled(False)
        row1.addWidget(self.btn_dec_sp_p1)
        row1.addWidget(self.sp_setpoint_p1)
        row1.addWidget(self.btn_inc_sp_p1)
        row1.addWidget(self.btn_apply_sp_p1)
        adv.addWidget(self.row_p1, 0, 1, 1, 3)
        # Fila P2
        self.row_p2 = QWidget()
        row2 = QHBoxLayout(self.row_p2)
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(8)
        self.btn_dec_sp_p2 = QPushButton("-0.1"); self.btn_dec_sp_p2.setMinimumHeight(48); self.btn_dec_sp_p2.setProperty("size", "lg")
        self.sp_setpoint_p2 = QDoubleSpinBox(); self.sp_setpoint_p2.setDecimals(1); self.sp_setpoint_p2.setRange(-40.0, 60.0); self.sp_setpoint_p2.setSingleStep(0.1); self.sp_setpoint_p2.setMinimumHeight(48); self.sp_setpoint_p2.setProperty("size", "lg"); self.sp_setpoint_p2.setSuffix(" °C")
        self.sp_setpoint_p2.valueChanged.connect(self._on_sp2_user_change)
        self.btn_inc_sp_p2 = QPushButton("+0.1"); self.btn_inc_sp_p2.setMinimumHeight(48); self.btn_inc_sp_p2.setProperty("size", "lg")
        self.btn_apply_sp_p2 = QPushButton("Aplicar SP P2"); self.btn_apply_sp_p2.setMinimumHeight(48); self.btn_apply_sp_p2.setProperty("size", "lg"); self.btn_apply_sp_p2.setEnabled(False)
        row2.addWidget(self.btn_dec_sp_p2)
        row2.addWidget(self.sp_setpoint_p2)
        row2.addWidget(self.btn_inc_sp_p2)
        row2.addWidget(self.btn_apply_sp_p2)
        adv.addWidget(self.row_p2, 1, 1, 1, 3)

        # Sección colapsable por defecto
        class CollapsibleSection(QWidget):
            def __init__(self, title: str, content: QWidget, collapsed: bool = True, right_widget: QWidget = None, on_toggle=None):
                super().__init__()
                outer = QVBoxLayout(self)
                outer.setContentsMargins(0, 0, 0, 0)
                outer.setSpacing(6)
                header = QHBoxLayout()
                self.btn = QToolButton()
                self.btn.setText(title)
                self.btn.setCheckable(True)
                self.btn.setChecked(not collapsed)
                self.btn.setProperty("size", "lg")
                self.btn.setMinimumHeight(40)
                self.btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
                self.btn.setArrowType(QtCore.Qt.DownArrow if not collapsed else QtCore.Qt.RightArrow)
                header.addWidget(self.btn)
                # Resumen a la derecha del título
                self.summary_lbl = QLabel("")
                self.summary_lbl.setProperty("class", "metricLabel")
                header.addSpacing(8)
                header.addWidget(self.summary_lbl)
                header.addStretch(1)
                if right_widget is not None:
                    header.addWidget(right_widget)
                outer.addLayout(header)
                outer.addWidget(content)
                content.setVisible(not collapsed)
                self.btn.toggled.connect(lambda ch: self._toggle(content, ch, on_toggle))

            def _toggle(self, content: QWidget, checked: bool, on_toggle):
                content.setVisible(checked)
                self.btn.setArrowType(QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow)
                if callable(on_toggle):
                    on_toggle(checked)

            def set_collapsed(self, collapsed: bool):
                self.btn.setChecked(not collapsed)

        self.sec_sp_adv = CollapsibleSection("Setpoints avanzados", sp_adv, collapsed=True, on_toggle=lambda ch: self._on_section_toggle('sec_sp_adv_open', ch))
        layout.addWidget(self.sec_sp_adv)

        # Editor de Tags se integra en el encabezado de calibración

        # Calibración de Sensores
        self.calib_frame = QWidget()
        calib = QGridLayout(self.calib_frame)
        calib.setContentsMargins(0, 0, 0, 0)
        calib.setHorizontalSpacing(12)
        calib.setVerticalSpacing(6)
        calib.setColumnStretch(0, 1)
        calib.setColumnStretch(1, 1)
        calib.setColumnStretch(2, 1)
        calib.setColumnStretch(3, 0)
        # Botón para editar tags (se moverá al header de la sección colapsable)
        self.btn_edit_tags = QPushButton("Editar Tags PLC")
        self.btn_edit_tags.setProperty("size", "lg")
        self.btn_edit_tags.setMinimumHeight(48)

        # Fila de labels (ahora empieza en 0 porque el título está en el header colapsable)
        calib.addWidget(QLabel("Ambiente"), 0, 0)
        calib.addWidget(QLabel("Pulpa 1"), 0, 1)
        calib.addWidget(QLabel("Pulpa 2"), 0, 2)
        # Fila de controles de calibración con botones +/- grandes
        # Ambiente
        self.sp_off_amb = QDoubleSpinBox(); self.sp_off_amb.setDecimals(1); self.sp_off_amb.setRange(-10.0, 10.0); self.sp_off_amb.setSingleStep(0.1); self.sp_off_amb.setMinimumHeight(48); self.sp_off_amb.setProperty("size", "lg"); self.sp_off_amb.setSuffix(" °C")
        self.sp_off_amb.valueChanged.connect(lambda _: self._set_cal_dirty('amb'))
        self.btn_dec_cal_amb = QPushButton("-0.1"); self.btn_dec_cal_amb.setProperty("size", "lg"); self.btn_dec_cal_amb.setMinimumHeight(48)
        self.btn_inc_cal_amb = QPushButton("+0.1"); self.btn_inc_cal_amb.setProperty("size", "lg"); self.btn_inc_cal_amb.setMinimumHeight(48)
        self.btn_dec_cal_amb.clicked.connect(self._dec_cal_amb)
        self.btn_inc_cal_amb.clicked.connect(self._inc_cal_amb)
        row_amb = QWidget(); hb_amb = QHBoxLayout(row_amb); hb_amb.setContentsMargins(0,0,0,0); hb_amb.setSpacing(8)
        hb_amb.addWidget(self.btn_dec_cal_amb); hb_amb.addWidget(self.sp_off_amb); hb_amb.addWidget(self.btn_inc_cal_amb)
        calib.addWidget(row_amb, 1, 0)

        # Pulpa 1
        self.sp_off_p1 = QDoubleSpinBox(); self.sp_off_p1.setDecimals(1); self.sp_off_p1.setRange(-10.0, 10.0); self.sp_off_p1.setSingleStep(0.1); self.sp_off_p1.setMinimumHeight(48); self.sp_off_p1.setProperty("size", "lg"); self.sp_off_p1.setSuffix(" °C")
        self.sp_off_p1.valueChanged.connect(lambda _: self._set_cal_dirty('p1'))
        self.btn_dec_cal_p1 = QPushButton("-0.1"); self.btn_dec_cal_p1.setProperty("size", "lg"); self.btn_dec_cal_p1.setMinimumHeight(48)
        self.btn_inc_cal_p1 = QPushButton("+0.1"); self.btn_inc_cal_p1.setProperty("size", "lg"); self.btn_inc_cal_p1.setMinimumHeight(48)
        self.btn_dec_cal_p1.clicked.connect(self._dec_cal_p1)
        self.btn_inc_cal_p1.clicked.connect(self._inc_cal_p1)
        row_p1 = QWidget(); hb_p1 = QHBoxLayout(row_p1); hb_p1.setContentsMargins(0,0,0,0); hb_p1.setSpacing(8)
        hb_p1.addWidget(self.btn_dec_cal_p1); hb_p1.addWidget(self.sp_off_p1); hb_p1.addWidget(self.btn_inc_cal_p1)
        calib.addWidget(row_p1, 1, 1)

        # Pulpa 2
        self.sp_off_p2 = QDoubleSpinBox(); self.sp_off_p2.setDecimals(1); self.sp_off_p2.setRange(-10.0, 10.0); self.sp_off_p2.setSingleStep(0.1); self.sp_off_p2.setMinimumHeight(48); self.sp_off_p2.setProperty("size", "lg"); self.sp_off_p2.setSuffix(" °C")
        self.sp_off_p2.valueChanged.connect(lambda _: self._set_cal_dirty('p2'))
        self.btn_dec_cal_p2 = QPushButton("-0.1"); self.btn_dec_cal_p2.setProperty("size", "lg"); self.btn_dec_cal_p2.setMinimumHeight(48)
        self.btn_inc_cal_p2 = QPushButton("+0.1"); self.btn_inc_cal_p2.setProperty("size", "lg"); self.btn_inc_cal_p2.setMinimumHeight(48)
        self.btn_dec_cal_p2.clicked.connect(self._dec_cal_p2)
        self.btn_inc_cal_p2.clicked.connect(self._inc_cal_p2)
        row_p2 = QWidget(); hb_p2 = QHBoxLayout(row_p2); hb_p2.setContentsMargins(0,0,0,0); hb_p2.setSpacing(8)
        hb_p2.addWidget(self.btn_dec_cal_p2); hb_p2.addWidget(self.sp_off_p2); hb_p2.addWidget(self.btn_inc_cal_p2)
        calib.addWidget(row_p2, 1, 2)

        # Botón aplicar grande y en una fila completa para touch
        self.btn_apply_cal = QPushButton("Aplicar Calibración")
        self.btn_apply_cal.setProperty("size", "lg")
        self.btn_apply_cal.setMinimumHeight(48)
        self.btn_apply_cal.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_apply_cal.setEnabled(False)
        calib.addWidget(self.btn_apply_cal, 2, 0, 1, 4)

        # Envolver calibración en sección colapsable por defecto, con botón a la derecha
        self.sec_cal = CollapsibleSection("Calibración de Sensores (offset, °C)", self.calib_frame, collapsed=True, right_widget=self.btn_edit_tags, on_toggle=lambda ch: self._on_section_toggle('sec_cal_open', ch))
        layout.addWidget(self.sec_cal)

        self.btn_back = QPushButton("Volver")
        self.btn_back.setProperty("size", "xl")
        self.btn_back.setMinimumHeight(48)
        layout.addWidget(self.btn_back)

        # Señales
        self.btn_back.clicked.connect(self.back.emit)
        self.btn_on.clicked.connect(self._on_on)
        self.btn_off.clicked.connect(self._on_off)
        self.btn_defrost.clicked.connect(self._on_defrost)
        self.btn_apply_sp.clicked.connect(self._on_apply_sp)
        self.btn_inc_sp.clicked.connect(self._on_inc)
        self.btn_dec_sp.clicked.connect(self._on_dec)
        self.btn_edit_tags.clicked.connect(self._open_tag_editor)
        self.btn_apply_cal.clicked.connect(self._on_apply_cal)
        # Setpoints pulpa
        self.btn_apply_sp_p1.clicked.connect(self._on_apply_sp_p1)
        self.btn_inc_sp_p1.clicked.connect(self._inc_sp1)
        self.btn_dec_sp_p1.clicked.connect(self._dec_sp1)
        self.btn_apply_sp_p2.clicked.connect(self._on_apply_sp_p2)
        self.btn_inc_sp_p2.clicked.connect(self._inc_sp2)
        self.btn_dec_sp_p2.clicked.connect(self._dec_sp2)

        # Montar el contenido dentro del scroll
        self.scroll.setWidget(page)
        root_layout.addWidget(self.scroll)
        # Activar scroll cinético para pantallas táctiles
        self._setup_kinetic_scroll()

    def _setup_kinetic_scroll(self):
        try:
            vp = self.scroll.viewport()
            # Gestos táctiles y también con botón izquierdo para trackpads/ratón
            QScroller.grabGesture(vp, QScroller.LeftMouseButtonGesture)
            QScroller.grabGesture(vp, QScroller.TouchGesture)
            scroller = QScroller.scroller(vp)
            props = scroller.scrollerProperties()
            # Suavizar el desplazamiento y facilitar el gesto
            props.setScrollMetric(QScrollerProperties.DecelerationFactor, 0.07)
            props.setScrollMetric(QScrollerProperties.DragStartDistance, 0.001)
            props.setScrollMetric(QScrollerProperties.MaximumVelocity, 0.6)
            props.setScrollMetric(QScrollerProperties.AxisLockThreshold, 0.75)
            scroller.setScrollerProperties(props)
        except Exception:
            pass

    def apply_ui_prefs(self, ui: dict):
        # Restaurar estado colapsado
        try:
            open_adv = bool(ui.get('sec_sp_adv_open', False))
            self.sec_sp_adv.set_collapsed(not open_adv)
        except Exception:
            pass
        try:
            open_cal = bool(ui.get('sec_cal_open', False))
            self.sec_cal.set_collapsed(not open_cal)
        except Exception:
            pass
        # Refrescar resúmenes
        self._update_section_summaries()

    def set_tunnel(self, config: TunnelConfig):
        self.config = config
        self.lbl_title.setText(config.name)
        # No mostrar direcciones de memoria en esta pantalla
        self._update_tag_badges()
        # Precargar calibraciones si existen
        cal = getattr(config, "calibrations", {}) or {}
        self.sp_off_amb.setValue(float(cal.get("temp_ambiente", 0.0)))
        self.sp_off_p1.setValue(float(cal.get("temp_pulpa1", 0.0)))
        self.sp_off_p2.setValue(float(cal.get("temp_pulpa2", 0.0)))
        self._cal_amb_dirty = self._cal_p1_dirty = self._cal_p2_dirty = False
        # Resetear flags de edición al cambiar de túnel
        self._sp_dirty = False
        self._sp1_dirty = False
        self._sp2_dirty = False
        # Quitar resaltado dirty
        self._set_dirty_prop(self.sp_setpoint, False)
        self._set_dirty_prop(self.sp_setpoint_p1, False)
        self._set_dirty_prop(self.sp_setpoint_p2, False)
        self._set_dirty_prop(self.sp_off_amb, False)
        self._set_dirty_prop(self.sp_off_p1, False)
        self._set_dirty_prop(self.sp_off_p2, False)
        # Mostrar SIEMPRE sección de setpoints avanzados; deshabilitar filas si no hay tags configurados
        try:
            tags = config.tags or {}
            has_p1 = "setpoint_pulpa1" in tags
            has_p2 = "setpoint_pulpa2" in tags
            # Mantener visibles las filas y etiquetas
            self.lbl_sp_p1.setVisible(True)
            self.row_p1.setVisible(True)
            self.lbl_sp_p2.setVisible(True)
            self.row_p2.setVisible(True)
            # Habilitar/deshabilitar controles según disponibilidad de tags
            self.lbl_sp_p1.setEnabled(has_p1)
            self.row_p1.setEnabled(has_p1)
            self.btn_apply_sp_p1.setEnabled(False if not has_p1 else self._sp1_dirty)
            self.lbl_sp_p2.setEnabled(has_p2)
            self.row_p2.setEnabled(has_p2)
            self.btn_apply_sp_p2.setEnabled(False if not has_p2 else self._sp2_dirty)
            # Sección siempre visible (permite al usuario ver que existen y configurar tags)
            self.sec_sp_adv.setVisible(True)
        except Exception:
            pass
        # Actualizar resúmenes de secciones
        self._update_section_summaries()

    def update_data(self, data: TunnelData):
        self._in_update = True
        try:
            # Actualizar valores mostrados
            self.val_amb.setText(f"{data.temp_ambiente:.1f} °C")
            self.val_p1.setText(f"{data.temp_pulpa1:.1f} °C")
            self.val_p2.setText(f"{data.temp_pulpa2:.1f} °C")
            self.val_sp.setText(f"{data.setpoint:.1f} °C")
            # Tiempo de enfriamiento (segundos -> hh:mm:ss)
            try:
                secs = int(max(0.0, float(getattr(data, 'tiempo_enfriamiento', 0.0))))
                h = secs // 3600; m = (secs % 3600) // 60; s = secs % 60
                self.val_time.setText(f"{h:02d}:{m:02d}:{s:02d}")
            except Exception:
                pass

            # Solo sobreescribir spinboxes si el usuario no está editando (no foco) y no hay cambios sin aplicar
            if not self.sp_setpoint.hasFocus() and not self._sp_dirty:
                self.sp_setpoint.setValue(float(data.setpoint))
            try:
                sp1 = float(getattr(data, 'setpoint_pulpa1', 0.0))
            except Exception:
                sp1 = 0.0
            if not self.sp_setpoint_p1.hasFocus() and not self._sp1_dirty:
                self.sp_setpoint_p1.setValue(sp1)
            try:
                sp2 = float(getattr(data, 'setpoint_pulpa2', 0.0))
            except Exception:
                sp2 = 0.0
            if not self.sp_setpoint_p2.hasFocus() and not self._sp2_dirty:
                self.sp_setpoint_p2.setValue(sp2)
        finally:
            self._in_update = False
        # Actualizar resúmenes (valores visibles pudieron cambiar)
        self._update_section_summaries()
        # Estado visual destacado
        if data.estado:
            self.state_chip.setText("Encendido")
            self.state_chip.setProperty("state", "on")
            self.status_dot.setProperty("state", "on")
            self.header_frame.setProperty("on", "true")
        else:
            self.state_chip.setText("Apagado")
            self.state_chip.setProperty("state", "off")
            self.status_dot.setProperty("state", "off")
            self.header_frame.setProperty("on", "false")
        # Visualización de deshielo y texto del botón
        try:
            self._defrost_active = bool(getattr(data, "deshielo_activo", False))
            if self._defrost_active:
                self.state_chip.setText("Deshielo")
                self.state_chip.setProperty("state", "defrost")
                try:
                    self.btn_defrost.setText("Deshielo OFF")
                except Exception:
                    pass
            else:
                try:
                    self.btn_defrost.setText("Deshielo ON")
                except Exception:
                    pass
        except Exception:
            pass
        # Posición de válvula
        try:
            self.val_valve.setText(f"{float(getattr(data, 'valvula_posicion', 0.0)):.0f} %")
        except Exception:
            pass
        # Re-polish para aplicar QSS reactivo
        for w in (self.state_chip, self.status_dot, self.header_frame):
            try:
                w.style().unpolish(w)
                w.style().polish(w)
            except Exception:
                pass

    # Deshabilitar acciones que requieren PLC cuando se pierde conexión
    def set_online(self, online: bool):
        try:
            # Encender/Apagar y aplicar a PLC
            for w in (
                self.btn_on, self.btn_off,
                self.btn_apply_sp, self.btn_apply_sp_p1, self.btn_apply_sp_p2,
                self.btn_apply_cal, self.btn_defrost,
            ):
                w.setEnabled(online)
        except Exception:
            pass
        if not online:
            # Mostrar guiones en métricas
            try:
                self.val_amb.setText("--.- °C")
                self.val_p1.setText("--.- °C")
                self.val_p2.setText("--.- °C")
                self.val_sp.setText("--.- °C")
                self.val_valve.setText("-- %")
                try:
                    self.val_time.setText("--:--:--")
                except Exception:
                    pass
                self.state_chip.setText("Apagado")
                self.state_chip.setProperty("state", "off")
                self.status_dot.setProperty("state", "off")
                self.header_frame.setProperty("on", "false")
                for w in (self.state_chip, self.status_dot, self.header_frame):
                    w.style().unpolish(w)
                    w.style().polish(w)
            except Exception:
                pass

    def _on_on(self):
        if self.config:
            self.request_estado.emit(self.config.id, True)

    def _on_off(self):
        if self.config:
            self.request_estado.emit(self.config.id, False)

    def _on_defrost(self):
        if self.config:
            # Toggle ON/OFF según estado actual
            self.request_deshielo_set.emit(self.config.id, (not self._defrost_active))

    def _on_apply_sp(self):
        if self.config:
            self.request_setpoint.emit(self.config.id, float(self.sp_setpoint.value()))
            # Ya enviado: permitir que el sondeo vuelva a sincronizar
            self._sp_dirty = False
            self.btn_apply_sp.setEnabled(False)

    def _on_apply_sp_p1(self):
        if self.config:
            self.request_setpoint_p1.emit(self.config.id, float(self.sp_setpoint_p1.value()))
            self._sp1_dirty = False
            self.btn_apply_sp_p1.setEnabled(False)

    def _on_apply_sp_p2(self):
        if self.config:
            self.request_setpoint_p2.emit(self.config.id, float(self.sp_setpoint_p2.value()))
            self._sp2_dirty = False
            self.btn_apply_sp_p2.setEnabled(False)

    def _on_inc(self):
        self.sp_setpoint.setValue(self.sp_setpoint.value() + self._step)
        self._sp_dirty = True
        self.btn_apply_sp.setEnabled(True)

    def _on_dec(self):
        self.sp_setpoint.setValue(self.sp_setpoint.value() - self._step)
        self._sp_dirty = True
        self.btn_apply_sp.setEnabled(True)

    # Marcar edición por el usuario (ignorar cambios que vienen del sondeo)
    def _on_sp_user_change(self, _):
        if not self._in_update:
            self._sp_dirty = True
            self.btn_apply_sp.setEnabled(True)
            self._set_dirty_prop(self.sp_setpoint, True)

    def _on_sp1_user_change(self, _):
        if not self._in_update:
            self._sp1_dirty = True
            self.btn_apply_sp_p1.setEnabled(True)
            self._set_dirty_prop(self.sp_setpoint_p1, True)
        self._update_section_summaries()

    def _on_sp2_user_change(self, _):
        if not self._in_update:
            self._sp2_dirty = True
            self.btn_apply_sp_p2.setEnabled(True)
            self._set_dirty_prop(self.sp_setpoint_p2, True)
        self._update_section_summaries()

    def _on_step_changed(self, text: str):
        try:
            step = float(text.replace(",", "."))
        except Exception:
            step = 0.1
        self._step = step
        # Aplicar a todos los spinboxes
        for sb in (self.sp_setpoint, self.sp_setpoint_p1, self.sp_setpoint_p2, self.sp_off_amb, self.sp_off_p1, self.sp_off_p2):
            try:
                sb.setSingleStep(step)
            except Exception:
                pass
        # Actualizar etiquetas de botones +/-
        for btn in (
            self.btn_dec_sp, self.btn_inc_sp,
            self.btn_dec_sp_p1, self.btn_inc_sp_p1,
            self.btn_dec_sp_p2, self.btn_inc_sp_p2,
            self.btn_dec_cal_amb, self.btn_inc_cal_amb,
            self.btn_dec_cal_p1, self.btn_inc_cal_p1,
            self.btn_dec_cal_p2, self.btn_inc_cal_p2,
        ):
            try:
                if "+" in btn.text():
                    btn.setText(f"+{step}")
                else:
                    btn.setText(f"-{step}")
            except Exception:
                pass

    # Handlers SP P1/P2 con paso dinámico
    def _inc_sp1(self):
        self.sp_setpoint_p1.setValue(self.sp_setpoint_p1.value() + self._step)
    def _dec_sp1(self):
        self.sp_setpoint_p1.setValue(self.sp_setpoint_p1.value() - self._step)
    def _inc_sp2(self):
        self.sp_setpoint_p2.setValue(self.sp_setpoint_p2.value() + self._step)
    def _dec_sp2(self):
        self.sp_setpoint_p2.setValue(self.sp_setpoint_p2.value() - self._step)

    # Handlers Calibración con paso dinámico y habilitado del botón aplicar
    def _inc_cal_amb(self):
        self.sp_off_amb.setValue(self.sp_off_amb.value() + self._step)
        self._set_cal_dirty('amb')
        self._update_apply_cal_enabled()
        self._update_section_summaries()
    def _dec_cal_amb(self):
        self.sp_off_amb.setValue(self.sp_off_amb.value() - self._step)
        self._set_cal_dirty('amb')
        self._update_apply_cal_enabled()
        self._update_section_summaries()
    def _inc_cal_p1(self):
        self.sp_off_p1.setValue(self.sp_off_p1.value() + self._step)
        self._set_cal_dirty('p1')
        self._update_apply_cal_enabled()
        self._update_section_summaries()
    def _dec_cal_p1(self):
        self.sp_off_p1.setValue(self.sp_off_p1.value() - self._step)
        self._set_cal_dirty('p1')
        self._update_apply_cal_enabled()
        self._update_section_summaries()
    def _inc_cal_p2(self):
        self.sp_off_p2.setValue(self.sp_off_p2.value() + self._step)
        self._set_cal_dirty('p2')
        self._update_apply_cal_enabled()
        self._update_section_summaries()
    def _dec_cal_p2(self):
        self.sp_off_p2.setValue(self.sp_off_p2.value() - self._step)
        self._set_cal_dirty('p2')
        self._update_apply_cal_enabled()
        self._update_section_summaries()

    # --- Tag badges helpers ---
    def _set_dirty_prop(self, w: QWidget, dirty: bool):
        try:
            w.setProperty("dirty", "true" if dirty else "false")
            w.style().unpolish(w)
            w.style().polish(w)
        except Exception:
            pass

    def _update_apply_cal_enabled(self):
        any_dirty = bool(self._cal_amb_dirty or self._cal_p1_dirty or self._cal_p2_dirty)
        try:
            self.btn_apply_cal.setEnabled(any_dirty)
        except Exception:
            pass
        # Resaltar cada spinbox según dirty
        self._set_dirty_prop(self.sp_off_amb, self._cal_amb_dirty)
        self._set_dirty_prop(self.sp_off_p1, self._cal_p1_dirty)
        self._set_dirty_prop(self.sp_off_p2, self._cal_p2_dirty)

    def _on_section_toggle(self, key: str, open_state: bool):
        # Persistir preferencia hacia MainWindow
        try:
            self.update_ui_pref.emit(key, open_state)
        except Exception:
            pass

    def _update_section_summaries(self):
        # Resumen Setpoints avanzados
        try:
            sp1 = self.sp_setpoint_p1.value()
            sp2 = self.sp_setpoint_p2.value()
            self.sec_sp_adv.summary_lbl.setText(f"P1: {sp1:.1f} °C • P2: {sp2:.1f} °C")
        except Exception:
            pass
        # Resumen Calibración
        try:
            a = self.sp_off_amb.value(); p1 = self.sp_off_p1.value(); p2 = self.sp_off_p2.value()
            self.sec_cal.summary_lbl.setText(f"Amb: {a:+.1f} • P1: {p1:+.1f} • P2: {p2:+.1f} °C")
        except Exception:
            pass
    def _format_tag(self, tag: TagAddress) -> str:
        area = getattr(tag, "area", "DB").upper()
        if tag.type.upper() == "BOOL":
            if area == "DB":
                return f"DB{tag.db} DBX{tag.start}.{tag.bit}"
            return f"{area}{tag.start}.{tag.bit}"
        else:  # REAL
            if area == "DB":
                return f"DB{tag.db} DBD{tag.start}"
            return f"{area}{tag.start} (REAL)"

    def _update_tag_badges(self):
        if not getattr(self, "_show_tag_badges", False):
            # Oculto: no crear ni insertar barra de badges
            return
        if not hasattr(self, "_tag_bar"):
            # Crear barra de badges solo una vez
            self._tag_bar = QHBoxLayout()
            self._tag_bar.setSpacing(8)
            self.badge_amb = QLabel(""); self.badge_amb.setObjectName("TagBadge")
            self.badge_p1 = QLabel(""); self.badge_p1.setObjectName("TagBadge")
            self.badge_p2 = QLabel(""); self.badge_p2.setObjectName("TagBadge")
            self.badge_sp = QLabel(""); self.badge_sp.setObjectName("TagBadge")
            self.badge_sp1 = QLabel(""); self.badge_sp1.setObjectName("TagBadge")
            self.badge_sp2 = QLabel(""); self.badge_sp2.setObjectName("TagBadge")
            self.badge_cal_amb = QLabel(""); self.badge_cal_amb.setObjectName("TagBadge")
            self.badge_cal_p1 = QLabel(""); self.badge_cal_p1.setObjectName("TagBadge")
            self.badge_cal_p2 = QLabel(""); self.badge_cal_p2.setObjectName("TagBadge")
            self.badge_estado = QLabel(""); self.badge_estado.setObjectName("TagBadge")
            self._tag_bar.addWidget(self.badge_amb)
            self._tag_bar.addWidget(self.badge_p1)
            self._tag_bar.addWidget(self.badge_p2)
            self._tag_bar.addWidget(self.badge_sp)
            self._tag_bar.addWidget(self.badge_sp1)
            self._tag_bar.addWidget(self.badge_sp2)
            self._tag_bar.addWidget(self.badge_cal_amb)
            self._tag_bar.addWidget(self.badge_cal_p1)
            self._tag_bar.addWidget(self.badge_cal_p2)
            self._tag_bar.addWidget(self.badge_estado)
            # Insertar barra antes de los controles
            parent_layout: QVBoxLayout = self.layout()  # type: ignore
            parent_layout.insertLayout(2, self._tag_bar)
        if self.config:
            t = self.config.tags
            def set_badge(lbl: QLabel, key: str, title: str):
                if key in t and isinstance(t[key], TagAddress):
                    lbl.setText(f"{title}: {self._format_tag(t[key])}")
                    lbl.show()
                else:
                    lbl.setText("")
                    lbl.hide()
            set_badge(self.badge_amb, "temp_ambiente", "Amb")
            set_badge(self.badge_p1, "temp_pulpa1", "P1")
            set_badge(self.badge_p2, "temp_pulpa2", "P2")
            set_badge(self.badge_sp, "setpoint", "SP")
            set_badge(self.badge_sp1, "setpoint_pulpa1", "SP1")
            set_badge(self.badge_sp2, "setpoint_pulpa2", "SP2")
            set_badge(self.badge_cal_amb, "cal_temp_ambiente", "Cal Amb")
            set_badge(self.badge_cal_p1, "cal_temp_pulpa1", "Cal P1")
            set_badge(self.badge_cal_p2, "cal_temp_pulpa2", "Cal P2")
            # Estado puede ser lectura o comando
            if "estado" in t:
                set_badge(self.badge_estado, "estado", "Estado")

    # --- Tag Editor Dialog ---
    def _open_tag_editor(self):
        if not self.config:
            return
        # Password gate
        pwd, ok = QInputDialog.getText(self, "Autorización", "Ingrese contraseña:", QLineEdit.Password)
        if not ok:
            return
        if pwd != "Migiva2025":
            QMessageBox.critical(self, "Acceso denegado", "Contraseña incorrecta.")
            return
        dlg = TagEditorDialog(self, self.config)
        if dlg.exec_() == QDialog.Accepted:
            new_tags = dlg.get_tags()
            # Actualizar propio config en memoria
            self.config.tags = new_tags
            self._update_tag_badges()
            # Emitir evento para que MainWindow persista
            self.update_tunnel_tags.emit(self.config.id, new_tags)

    def _on_apply_cal(self):
        if not self.config:
            return
        cal = {
            "temp_ambiente": float(self.sp_off_amb.value()),
            "temp_pulpa1": float(self.sp_off_p1.value()),
            "temp_pulpa2": float(self.sp_off_p2.value()),
        }
        # Actualizar en memoria local para reflejar inmediatamente
        self.config.calibrations = cal
        self.update_tunnel_calibrations.emit(self.config.id, cal)
        self._cal_amb_dirty = self._cal_p1_dirty = self._cal_p2_dirty = False

    def _set_cal_dirty(self, which: str):
        if which == 'amb':
            self._cal_amb_dirty = True
        elif which == 'p1':
            self._cal_p1_dirty = True
        elif which == 'p2':
            self._cal_p2_dirty = True


class TagEditorDialog(QDialog):
    def __init__(self, parent: QWidget, cfg: TunnelConfig):
        super().__init__(parent)
        self.setWindowTitle(f"Editar Tags - {cfg.name}")
        self._cfg = cfg
        self._edits = {}
        # Contenedor con scroll para muchos campos
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(scroll)
        content = QWidget()
        form = QFormLayout(content)
        form.setSpacing(8)
        scroll.setWidget(content)
        keys = [
            ("temp_ambiente", "Ambiente", "REAL"),
            ("temp_pulpa1", "Pulpa 1", "REAL"),
            ("temp_pulpa2", "Pulpa 2", "REAL"),
            ("setpoint", "Setpoint", "REAL"),
            ("setpoint_pulpa1", "SP Pulpa 1", "REAL"),
            ("setpoint_pulpa2", "SP Pulpa 2", "REAL"),
            ("estado", "Estado", "BOOL"),
            ("cmd_encender", "CMD Encender (pulso)", "BOOL"),
            ("cmd_apagar", "CMD Apagar (pulso)", "BOOL"),
            ("deshielo_activo", "Deshielo Activo (BOOL)", "BOOL"),
            ("cmd_deshielo", "CMD Deshielo (pulso)", "BOOL"),
            ("cmd_deshielo_on", "CMD Deshielo ON (pulso)", "BOOL"),
            ("cmd_deshielo_off", "CMD Deshielo OFF (pulso)", "BOOL"),
            ("cmd_cancelar_deshielo", "CMD Cancelar Deshielo (pulso)", "BOOL"),
            ("cmd_parar_deshielo", "CMD Parar Deshielo (pulso)", "BOOL"),
            ("valvula_posicion", "Válvula Posición (%)", "REAL"),
            ("cal_temp_ambiente", "Calib Ambiente", "REAL"),
            ("cal_temp_pulpa1", "Calib Pulpa 1", "REAL"),
            ("cal_temp_pulpa2", "Calib Pulpa 2", "REAL"),
        ]
        for key, title, default_type in keys:
            row = QHBoxLayout()
            db = QSpinBox(); db.setRange(1, 4096)
            start = QSpinBox(); start.setRange(0, 65535)
            bit = QSpinBox(); bit.setRange(0, 7)
            type_cb = QComboBox(); type_cb.addItems(["REAL", "BOOL"])
            area_cb = QComboBox(); area_cb.addItems(["DB", "I", "Q", "M"])
            if key in cfg.tags:
                tag = cfg.tags[key]
                db.setValue(tag.db)
                start.setValue(tag.start)
                bit.setValue(tag.bit)
                type_cb.setCurrentText(tag.type.upper())
                area_cb.setCurrentText(getattr(tag, "area", "DB").upper())
            else:
                type_cb.setCurrentText(default_type)
                area_cb.setCurrentText("DB")
            row.addWidget(QLabel(title))
            row.addWidget(QLabel("DB")); row.addWidget(db)
            row.addWidget(QLabel("Start")); row.addWidget(start)
            row.addWidget(QLabel("Bit")); row.addWidget(bit)
            row.addWidget(QLabel("Tipo")); row.addWidget(type_cb)
            row.addWidget(QLabel("Area")); row.addWidget(area_cb)
            form.addRow(row)
            self._edits[key] = (db, start, bit, type_cb, area_cb)
        # Acciones
        btns = QHBoxLayout()
        btn_ok = QPushButton("Guardar"); btn_ok.setObjectName("Primary"); btn_ok.setProperty("size", "lg")
        btn_cancel = QPushButton("Cancelar"); btn_cancel.setProperty("size", "lg")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_ok); btns.addWidget(btn_cancel)
        root.addLayout(btns)

    def get_tags(self) -> dict:
        out = {}
        for key, (db, start, bit, type_cb, area_cb) in self._edits.items():
            out[key] = TagAddress(db=int(db.value()), start=int(start.value()), type=type_cb.currentText(), bit=int(bit.value()), area=area_cb.currentText())
        return out
