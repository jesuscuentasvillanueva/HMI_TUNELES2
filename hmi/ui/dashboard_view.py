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
        # Modo densidad (compacto por defecto para ver todo de un vistazo)
        self._compact = True
        # Límite de túneles visibles (None = todos)
        self._visible_limit = None
        # Rango visible (1-indexed, inclusive). Si se define, tiene prioridad sobre el límite.
        self._range_from = None
        self._range_to = None
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
        # Aplicar densidad compacta a las tarjetas
        try:
            self.set_density(True)
        except Exception:
            pass

    def _build_ui(self):
        grid = QGridLayout(self)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(24)
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
        # Resetear alturas de filas previas para evitar residuos
        try:
            for r in range(0, 50):
                self._grid.setRowMinimumHeight(r, 0)
        except Exception:
            pass

    def _visible_tunnels(self) -> List[TunnelConfig]:
        total = len(self.tunnels)
        # Aplicar rango si está definido y válido
        if self._range_from is not None and self._range_to is not None and total > 0:
            a = max(1, int(self._range_from))
            b = max(1, int(self._range_to))
            if a > b:
                a, b = b, a
            # Cantidad a mostrar según nomenclatura solicitada, pero limitada a los túneles físicos
            count = max(1, b - a + 1)
            count = min(count, total)
            return self.tunnels[:count]
        # Si no hay rango, aplicar límite simple (primeros N)
        if self._visible_limit:
            limit = int(max(1, min(int(self._visible_limit), total)))
            return self.tunnels[:limit]
        return list(self.tunnels)

    def _reflow_grid(self):
        self._clear_grid()
        columns = max(1, self._columns)
        tunnels_to_show = self._visible_tunnels()
        visible_ids = {t.id for t in tunnels_to_show}
        # Mostrar/ocultar según el conjunto visible actual
        for tid, card in self.cards.items():
            if tid in visible_ids:
                card.show()
            else:
                card.hide()
        # Asignar nombres visibles (nomenclatura) si hay rango definido, o restaurar nombres reales
        range_active = (self._range_from is not None and self._range_to is not None)
        start_num = max(1, int(self._range_from)) if range_active else None
        for idx, t in enumerate(tunnels_to_show):
            r = idx // columns
            c = idx % columns
            card = self.cards[t.id]
            try:
                if range_active and start_num is not None and hasattr(card, "set_display_name"):
                    card.set_display_name(f"Túnel {start_num + idx}")
                elif hasattr(card, "set_display_name"):
                    card.set_display_name(t.name)
            except Exception:
                pass
            self._grid.addWidget(card, r, c)
        # Estirar solo columnas
        for c in range(max(1, columns)):
            self._grid.setColumnStretch(c, 1)
        self._apply_uniform_sizes()

    def _update_columns(self):
        # Calcular columnas principalmente por ancho disponible, con límites razonables
        m = self._grid.contentsMargins()
        avail_w = max(0, self.width() - (m.left() + m.right()))
        spacing_h = self._grid.horizontalSpacing() or 0
        # Requisitos mínimos de ancho por tarjeta (compacto permite algo más angosto)
        min_card_w = 200 if self._compact else 260
        if avail_w <= 0:
            return
        total = len(self._visible_tunnels())
        # Base mínima de columnas: 3 en compacto, 4 normal, pero nunca mayor que el total visible
        base_min = min(max(1, total), (3 if self._compact else 4))
        cols_by_width = max(base_min, int((avail_w + spacing_h) // (min_card_w + spacing_h)))
        # No más columnas que túneles visibles, y no más de 4 en total (legibilidad)
        columns = int(min(cols_by_width, max(1, total), 4))
        if columns != self._columns:
            self._columns = columns
            self._reflow_grid()

    def _apply_uniform_sizes(self):
        if not hasattr(self, "_grid"):
            return
        columns = max(1, self._columns)
        total = len(self._visible_tunnels())
        rows = (total + columns - 1) // columns
        if rows <= 0:
            return
        m = self._grid.contentsMargins()
        spacing = self._grid.verticalSpacing() or 0
        avail_h = max(0, self.height() - (m.top() + m.bottom()) - spacing * (rows - 1))
        # Ajustar altura objetivo para que TODAS las filas quepan sin scroll (sin mínimos forzados)
        row_h_raw = int(avail_h // max(1, rows))
        # Limitar altura máxima de tarjeta para evitar sobredimensionamiento cuando hay pocas tarjetas
        target_max = 320
        row_h = min(row_h_raw, target_max)
        for r in range(rows):
            self._grid.setRowMinimumHeight(r, int(row_h))
        # Aplicar a cada tarjeta y dejar que se adapte internamente
        # Solo las visibles en el grid necesitan forzar altura; las no visibles no están en el layout
        # Recorremos las tarjetas agregadas al grid
        for idx, t in enumerate(self._visible_tunnels()):
            card = self.cards.get(t.id)
            if not card:
                continue
            try:
                if hasattr(card, "apply_target_height"):
                    card.apply_target_height(int(row_h))
                card.setFixedHeight(int(row_h))
            except Exception:
                pass

    def set_visible_limit(self, n=None):
        try:
            if n is None:
                self._visible_limit = None
            else:
                total = len(self.tunnels)
                self._visible_limit = int(max(1, min(int(n), total)))
        except Exception:
            self._visible_limit = None
        # Primero recalcular columnas en base al nuevo total visible, luego reflujo y tamaños
        self._update_columns()
        self._reflow_grid()
        self._apply_uniform_sizes()

    def set_visible_range(self, a=None, b=None):
        try:
            total = len(self.tunnels)
            if a is None or b is None:
                self._range_from = None
                self._range_to = None
            else:
                aa = int(a); bb = int(b)
                if aa > bb:
                    aa, bb = bb, aa
                # Solo asegurar límite inferior; el superior puede exceder para nomenclatura
                aa = max(1, aa)
                bb = max(1, bb)
                self._range_from = aa
                self._range_to = bb
        except Exception:
            self._range_from = None
            self._range_to = None
        # Cambió el conjunto visible -> recalcular todo
        self._update_columns()
        self._reflow_grid()
        self._apply_uniform_sizes()

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
