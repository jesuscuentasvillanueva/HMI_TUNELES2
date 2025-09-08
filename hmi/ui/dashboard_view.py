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
            # Recalcular alturas de fila cuando cambie la altura de contenido de una tarjeta
            try:
                card.content_height_changed.connect(lambda _h, self=self: self._apply_uniform_sizes())
            except Exception:
                pass
            self.cards[t.id] = card
        self._build_ui()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._apply_uniform_sizes()
        # Ajuste diferido para que tome el ancho definitivo del contenedor
        QTimer.singleShot(0, self._deferred_layout_update)

    def _build_ui(self):
        grid = QGridLayout(self)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
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
        # Estirar solo columnas
        for c in range(max(1, columns)):
            self._grid.setColumnStretch(c, 1)
        self._apply_uniform_sizes()

    def _update_columns(self):
        # Calcular columnas en función del ancho disponible y ancho mínimo por tarjeta
        m = self._grid.contentsMargins()
        avail_w = max(0, self.width() - (m.left() + m.right()))
        spacing = self._grid.horizontalSpacing() or 0
        min_card_w = 180 if self._compact else 240
        # Probar cuántas tarjetas entran por fila
        if avail_w <= 0:
            return
        # columns = floor((avail_w + spacing) / (min_card_w + spacing))
        base_min = 3 if self._compact else 4
        columns = max(base_min, min(6, (avail_w + spacing) // (min_card_w + spacing)))
        columns = int(columns)
        if columns != self._columns:
            self._columns = columns
            self._reflow_grid()

    def _apply_uniform_sizes(self):
        if not hasattr(self, "_grid"):
            return
        columns = max(1, self._columns)
        rows = (len(self.tunnels) + columns - 1) // columns
        if rows <= 0:
            return
        m = self._grid.contentsMargins()
        spacing = self._grid.verticalSpacing() or 0
        avail_h = max(0, self.height() - (m.top() + m.bottom()) - spacing * (rows - 1))
        # Altura objetivo por tarjeta para que TODAS quepan sin scroll
        row_h = max(120, avail_h // rows)
        for r in range(rows):
            self._grid.setRowMinimumHeight(r, int(row_h))
        # Aplicar a cada tarjeta y dejar que se adapte internamente
        for card in self.cards.values():
            try:
                if hasattr(card, "apply_target_height"):
                    card.apply_target_height(int(row_h))
                card.setFixedHeight(int(row_h))
            except Exception:
                pass

    def _update_container_min_height(self):
        return

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
        self._update_container_min_height()

    def showEvent(self, event):
        super().showEvent(event)
        # Asegura cálculo inicial correcto según ancho real
        self._update_columns()
        self._apply_uniform_sizes()
        self._update_container_min_height()

    def _deferred_layout_update(self):
        self._update_columns()
        self._apply_uniform_sizes()
        self._update_container_min_height()

    def update_data(self, data: Dict[int, TunnelData]):
        for tid, td in data.items():
            if tid in self.cards:
                self.cards[tid].update_data(td)
