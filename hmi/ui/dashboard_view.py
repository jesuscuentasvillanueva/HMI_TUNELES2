from __future__ import annotations

from typing import Dict, List

from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QGridLayout, QSizePolicy
from math import ceil

from ..models import TunnelConfig, TunnelData
from .tunnel_card import TunnelCard


class DashboardView(QWidget):
    tunnel_clicked = pyqtSignal(int)

    def __init__(self, tunnels: List[TunnelConfig]):
        super().__init__()
        self.tunnels = tunnels
        # Modo densidad (debe estar antes de construir la UI)
        self._compact = False
        # Crear tarjetas una sola vez y reutilizarlas al reordenar
        self.cards: Dict[int, TunnelCard] = {}
        for t in self.tunnels:
            card = TunnelCard(t)
            card.clicked.connect(self.tunnel_clicked)
            self.cards[t.id] = card
        self._build_ui()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._apply_uniform_sizes()
        # Ajuste diferido para que tome el ancho definitivo del contenedor
        QTimer.singleShot(0, self._deferred_layout_update)

    def _build_ui(self):
        grid = QGridLayout(self)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        columns = 4  # valor inicial
        self._grid = grid
        self._columns = columns
        self._reflow_grid()

    def _clear_grid(self):
        # Quitar widgets del layout sin destruir las tarjetas
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                self._grid.removeWidget(w)

    def _reflow_grid(self):
        self._clear_grid()
        columns = max(1, self._columns)
        for idx, t in enumerate(self.tunnels):
            r = idx // columns
            c = idx % columns
            self._grid.addWidget(self.cards[t.id], r, c)
        # Estirar TODAS las filas y columnas por igual para uso uniforme del espacio
        rows = (len(self.tunnels) + columns - 1) // columns
        for r in range(max(1, rows)):
            self._grid.setRowStretch(r, 1)
        for c in range(max(1, columns)):
            self._grid.setColumnStretch(c, 1)
        self._apply_uniform_sizes()

    def _update_columns(self):
        # Calcular columnas en función del ancho disponible y ancho mínimo por tarjeta
        m = self._grid.contentsMargins()
        avail_w = max(0, self.width() - (m.left() + m.right()))
        spacing = self._grid.horizontalSpacing() or 0
        min_card_w = 180 if self._compact else 200
        # Probar cuántas tarjetas entran por fila
        if avail_w <= 0:
            return
        # columns = floor((avail_w + spacing) / (min_card_w + spacing))
        base_min = 3 if self._compact else 4
        columns = max(base_min, min(8, (avail_w + spacing) // (min_card_w + spacing)))
        columns = int(columns)
        if columns != self._columns:
            self._columns = columns
            self._reflow_grid()

    def _apply_uniform_sizes(self):
        if not hasattr(self, "_grid"):
            return
        rows = max(1, ceil(len(self.tunnels) / float(self._columns)))
        m = self._grid.contentsMargins()
        avail_h = max(0, self.height() - (m.top() + m.bottom()) - self._grid.verticalSpacing() * (rows - 1))
        # Usar altura mínima para evitar recortes, dejando que el layout expanda según el espacio
        row_min = max(140 if getattr(self, "_compact", False) else 160, avail_h // rows)
        for card in self.cards.values():
            card.setMinimumHeight(int(row_min))

    def set_density(self, compact: bool):
        self._compact = bool(compact)
        for card in self.cards.values():
            card.set_density(compact)
        self._update_columns()
        self._apply_uniform_sizes()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_columns()
        self._apply_uniform_sizes()

    def showEvent(self, event):
        super().showEvent(event)
        # Asegura cálculo inicial correcto según ancho real
        self._update_columns()
        self._apply_uniform_sizes()

    def _deferred_layout_update(self):
        self._update_columns()
        self._apply_uniform_sizes()

    def update_data(self, data: Dict[int, TunnelData]):
        for tid, td in data.items():
            if tid in self.cards:
                self.cards[tid].update_data(td)
