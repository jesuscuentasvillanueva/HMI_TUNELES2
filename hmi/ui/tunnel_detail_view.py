from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QDoubleSpinBox, QGridLayout, QSizePolicy, QDialog, QFormLayout, QSpinBox, QComboBox, QInputDialog, QMessageBox, QLineEdit, QFrame

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

    def __init__(self):
        super().__init__()
        self.config: Optional[TunnelConfig] = None
        # No mostrar direcciones de memoria (badges) en esta pantalla
        self._show_tag_badges: bool = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
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

        metrics.addWidget(amb_w, 0, 0)
        metrics.addWidget(p1_w, 0, 1)
        metrics.addWidget(p2_w, 1, 0)
        metrics.addWidget(sp_w, 1, 1)

        layout.addLayout(metrics)

        # Controles
        controls = QHBoxLayout()
        self.btn_on = QPushButton("Encender")
        self.btn_on.setObjectName("Primary")
        self.btn_on.setProperty("size", "xl")
        self.btn_on.setMinimumHeight(56)
        self.btn_on.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.btn_off = QPushButton("Apagar")
        self.btn_off.setObjectName("Danger")
        self.btn_off.setProperty("size", "xl")
        self.btn_off.setMinimumHeight(56)
        self.btn_off.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        controls.addWidget(self.btn_on)
        controls.addWidget(self.btn_off)

        sp_layout = QHBoxLayout()
        sp_layout.setSpacing(12)
        self.btn_dec_sp = QPushButton("-0.1")
        self.btn_dec_sp.setProperty("size", "xl")
        self.btn_dec_sp.setMinimumHeight(48)
        self.btn_dec_sp.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.sp_setpoint = QDoubleSpinBox()
        self.sp_setpoint.setDecimals(1)
        self.sp_setpoint.setRange(-40.0, 60.0)
        self.sp_setpoint.setSingleStep(0.1)
        self.sp_setpoint.setProperty("size", "xl")
        self.sp_setpoint.setMinimumHeight(48)
        self.sp_setpoint.setMinimumWidth(180)

        self.btn_inc_sp = QPushButton("+0.1")
        self.btn_inc_sp.setProperty("size", "xl")
        self.btn_inc_sp.setMinimumHeight(48)
        self.btn_inc_sp.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.btn_apply_sp = QPushButton("Aplicar Setpoint")
        self.btn_apply_sp.setProperty("size", "xl")
        self.btn_apply_sp.setMinimumHeight(48)
        self.btn_apply_sp.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        sp_layout.addWidget(self.btn_dec_sp)
        sp_layout.addWidget(self.sp_setpoint)
        sp_layout.addWidget(self.btn_inc_sp)
        sp_layout.addWidget(self.btn_apply_sp)

        layout.addLayout(controls)
        layout.addLayout(sp_layout)

        # Setpoints independientes Pulpa 1 y Pulpa 2 (dos filas ocultables)
        self.sp_pulp_frame = QWidget()
        sp_pulp = QGridLayout(self.sp_pulp_frame)
        sp_pulp.setHorizontalSpacing(8)
        sp_pulp.setVerticalSpacing(6)

        self.lbl_sp_p1 = QLabel("SP Pulpa 1")
        self.lbl_sp_p2 = QLabel("SP Pulpa 2")
        sp_pulp.addWidget(self.lbl_sp_p1, 0, 0)
        sp_pulp.addWidget(self.lbl_sp_p2, 1, 0)

        # Fila P1
        self.row_p1 = QWidget()
        row1 = QHBoxLayout(self.row_p1)
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(8)
        self.btn_dec_sp_p1 = QPushButton("-0.1"); self.btn_dec_sp_p1.setMinimumHeight(44); self.btn_dec_sp_p1.setProperty("size", "lg")
        self.sp_setpoint_p1 = QDoubleSpinBox(); self.sp_setpoint_p1.setDecimals(1); self.sp_setpoint_p1.setRange(-40.0, 60.0); self.sp_setpoint_p1.setSingleStep(0.1); self.sp_setpoint_p1.setMinimumHeight(44); self.sp_setpoint_p1.setProperty("size", "lg")
        self.btn_inc_sp_p1 = QPushButton("+0.1"); self.btn_inc_sp_p1.setMinimumHeight(44); self.btn_inc_sp_p1.setProperty("size", "lg")
        self.btn_apply_sp_p1 = QPushButton("Aplicar SP P1"); self.btn_apply_sp_p1.setMinimumHeight(44); self.btn_apply_sp_p1.setProperty("size", "lg")
        row1.addWidget(self.btn_dec_sp_p1)
        row1.addWidget(self.sp_setpoint_p1)
        row1.addWidget(self.btn_inc_sp_p1)
        row1.addWidget(self.btn_apply_sp_p1)
        sp_pulp.addWidget(self.row_p1, 0, 1, 1, 3)

        # Fila P2
        self.row_p2 = QWidget()
        row2 = QHBoxLayout(self.row_p2)
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(8)
        self.btn_dec_sp_p2 = QPushButton("-0.1"); self.btn_dec_sp_p2.setMinimumHeight(44); self.btn_dec_sp_p2.setProperty("size", "lg")
        self.sp_setpoint_p2 = QDoubleSpinBox(); self.sp_setpoint_p2.setDecimals(1); self.sp_setpoint_p2.setRange(-40.0, 60.0); self.sp_setpoint_p2.setSingleStep(0.1); self.sp_setpoint_p2.setMinimumHeight(44); self.sp_setpoint_p2.setProperty("size", "lg")
        self.btn_inc_sp_p2 = QPushButton("+0.1"); self.btn_inc_sp_p2.setMinimumHeight(44); self.btn_inc_sp_p2.setProperty("size", "lg")
        self.btn_apply_sp_p2 = QPushButton("Aplicar SP P2"); self.btn_apply_sp_p2.setMinimumHeight(44); self.btn_apply_sp_p2.setProperty("size", "lg")
        row2.addWidget(self.btn_dec_sp_p2)
        row2.addWidget(self.sp_setpoint_p2)
        row2.addWidget(self.btn_inc_sp_p2)
        row2.addWidget(self.btn_apply_sp_p2)
        sp_pulp.addWidget(self.row_p2, 1, 1, 1, 3)

        layout.addWidget(self.sp_pulp_frame)

        # Editor de Tags se integra en el encabezado de calibración

        # Calibración de Sensores
        self.calib_frame = QWidget()
        calib = QGridLayout(self.calib_frame)
        calib.setContentsMargins(0, 0, 0, 0)
        calib.setHorizontalSpacing(12)
        calib.setVerticalSpacing(6)
        title_cal = QLabel("Calibración de Sensores (offset, °C)")
        title_cal.setProperty("class", "sectionTitle")
        calib.addWidget(title_cal, 0, 0, 1, 3)
        # Botón pequeño para editar tags integrado aquí
        self.btn_edit_tags = QPushButton("Editar Tags PLC")
        self.btn_edit_tags.setProperty("size", "lg")
        self.btn_edit_tags.setMinimumHeight(40)
        calib.addWidget(self.btn_edit_tags, 0, 3, 1, 1)

        # Fila de labels
        calib.addWidget(QLabel("Ambiente"), 1, 0)
        calib.addWidget(QLabel("Pulpa 1"), 1, 1)
        calib.addWidget(QLabel("Pulpa 2"), 1, 2)
        # Fila de spinboxes
        self.sp_off_amb = QDoubleSpinBox(); self.sp_off_amb.setDecimals(1); self.sp_off_amb.setRange(-10.0, 10.0); self.sp_off_amb.setSingleStep(0.1); self.sp_off_amb.setMinimumHeight(44); self.sp_off_amb.setProperty("size", "lg")
        calib.addWidget(self.sp_off_amb, 2, 0)
        self.sp_off_p1 = QDoubleSpinBox(); self.sp_off_p1.setDecimals(1); self.sp_off_p1.setRange(-10.0, 10.0); self.sp_off_p1.setSingleStep(0.1); self.sp_off_p1.setMinimumHeight(44); self.sp_off_p1.setProperty("size", "lg")
        calib.addWidget(self.sp_off_p1, 2, 1)
        self.sp_off_p2 = QDoubleSpinBox(); self.sp_off_p2.setDecimals(1); self.sp_off_p2.setRange(-10.0, 10.0); self.sp_off_p2.setSingleStep(0.1); self.sp_off_p2.setMinimumHeight(44); self.sp_off_p2.setProperty("size", "lg")
        calib.addWidget(self.sp_off_p2, 2, 2)

        # Botón aplicar a la derecha para ahorrar altura
        self.btn_apply_cal = QPushButton("Aplicar Calibración")
        self.btn_apply_cal.setProperty("size", "lg")
        self.btn_apply_cal.setMinimumHeight(44)
        calib.addWidget(self.btn_apply_cal, 2, 3)

        layout.addWidget(self.calib_frame)

        self.btn_back = QPushButton("Volver")
        self.btn_back.setProperty("size", "xl")
        self.btn_back.setMinimumHeight(48)
        layout.addWidget(self.btn_back)

        # Señales
        self.btn_back.clicked.connect(self.back.emit)
        self.btn_on.clicked.connect(self._on_on)
        self.btn_off.clicked.connect(self._on_off)
        self.btn_apply_sp.clicked.connect(self._on_apply_sp)
        self.btn_inc_sp.clicked.connect(self._on_inc)
        self.btn_dec_sp.clicked.connect(self._on_dec)
        self.btn_edit_tags.clicked.connect(self._open_tag_editor)
        self.btn_apply_cal.clicked.connect(self._on_apply_cal)
        # Setpoints pulpa
        self.btn_apply_sp_p1.clicked.connect(self._on_apply_sp_p1)
        self.btn_inc_sp_p1.clicked.connect(lambda: self.sp_setpoint_p1.setValue(self.sp_setpoint_p1.value() + 0.1))
        self.btn_dec_sp_p1.clicked.connect(lambda: self.sp_setpoint_p1.setValue(self.sp_setpoint_p1.value() - 0.1))
        self.btn_apply_sp_p2.clicked.connect(self._on_apply_sp_p2)
        self.btn_inc_sp_p2.clicked.connect(lambda: self.sp_setpoint_p2.setValue(self.sp_setpoint_p2.value() + 0.1))
        self.btn_dec_sp_p2.clicked.connect(lambda: self.sp_setpoint_p2.setValue(self.sp_setpoint_p2.value() - 0.1))

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
        # Mostrar/ocultar SP Pulpa según tags existentes
        try:
            tags = config.tags or {}
            has_p1 = "setpoint_pulpa1" in tags
            has_p2 = "setpoint_pulpa2" in tags
            self.lbl_sp_p1.setVisible(has_p1)
            self.row_p1.setVisible(has_p1)
            self.lbl_sp_p2.setVisible(has_p2)
            self.row_p2.setVisible(has_p2)
            self.sp_pulp_frame.setVisible(has_p1 or has_p2)
        except Exception:
            pass

    def update_data(self, data: TunnelData):
        # Actualizar valores en el layout compacto 2x2
        self.val_amb.setText(f"{data.temp_ambiente:.1f} °C")
        self.val_p1.setText(f"{data.temp_pulpa1:.1f} °C")
        self.val_p2.setText(f"{data.temp_pulpa2:.1f} °C")
        self.val_sp.setText(f"{data.setpoint:.1f} °C")
        self.sp_setpoint.setValue(data.setpoint)
        # Setpoints pulpa
        try:
            self.sp_setpoint_p1.setValue(float(getattr(data, 'setpoint_pulpa1', 0.0)))
            self.sp_setpoint_p2.setValue(float(getattr(data, 'setpoint_pulpa2', 0.0)))
        except Exception:
            pass
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
        # Re-polish para aplicar QSS reactivo
        for w in (self.state_chip, self.status_dot, self.header_frame):
            try:
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

    def _on_apply_sp(self):
        if self.config:
            self.request_setpoint.emit(self.config.id, float(self.sp_setpoint.value()))

    def _on_apply_sp_p1(self):
        if self.config:
            self.request_setpoint_p1.emit(self.config.id, float(self.sp_setpoint_p1.value()))

    def _on_apply_sp_p2(self):
        if self.config:
            self.request_setpoint_p2.emit(self.config.id, float(self.sp_setpoint_p2.value()))

    def _on_inc(self):
        self.sp_setpoint.setValue(self.sp_setpoint.value() + 0.1)

    def _on_dec(self):
        self.sp_setpoint.setValue(self.sp_setpoint.value() - 0.1)

    # --- Tag badges helpers ---
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


class TagEditorDialog(QDialog):
    def __init__(self, parent: QWidget, cfg: TunnelConfig):
        super().__init__(parent)
        self.setWindowTitle(f"Editar Tags - {cfg.name}")
        self._cfg = cfg
        self._edits = {}
        form = QFormLayout(self)
        form.setSpacing(8)
        keys = [
            ("temp_ambiente", "Ambiente", "REAL"),
            ("temp_pulpa1", "Pulpa 1", "REAL"),
            ("temp_pulpa2", "Pulpa 2", "REAL"),
            ("setpoint", "Setpoint", "REAL"),
            ("setpoint_pulpa1", "SP Pulpa 1", "REAL"),
            ("setpoint_pulpa2", "SP Pulpa 2", "REAL"),
            ("estado", "Estado", "BOOL"),
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
        form.addRow(btns)

    def get_tags(self) -> dict:
        out = {}
        for key, (db, start, bit, type_cb, area_cb) in self._edits.items():
            out[key] = TagAddress(db=int(db.value()), start=int(start.value()), type=type_cb.currentText(), bit=int(bit.value()), area=area_cb.currentText())
        return out
