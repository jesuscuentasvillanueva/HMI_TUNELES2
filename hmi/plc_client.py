from __future__ import annotations

from typing import Dict, List, Optional, Union

from .models import PLCConfig, TagAddress, TunnelConfig, TunnelData


class BasePLC:
    def __init__(self, cfg: PLCConfig, tunnels: List[TunnelConfig]):
        self.cfg = cfg
        self.tunnels_map: Dict[int, TunnelConfig] = {t.id: t for t in tunnels}
        self._last_error: Optional[str] = None

    # API esperada
    def connect(self) -> bool:
        raise NotImplementedError

    def disconnect(self) -> None:
        raise NotImplementedError

    def is_connected(self) -> bool:
        raise NotImplementedError

    def read_all(self) -> Dict[int, TunnelData]:
        raise NotImplementedError

    def write_setpoint(self, tunnel_id: int, value: float) -> bool:
        raise NotImplementedError

    def write_estado(self, tunnel_id: int, value: bool) -> bool:
        raise NotImplementedError

    # Nuevos: setpoints independientes de pulpa y escritura genérica por clave
    def write_setpoint_p1(self, tunnel_id: int, value: float) -> bool:
        raise NotImplementedError

    def write_setpoint_p2(self, tunnel_id: int, value: float) -> bool:
        raise NotImplementedError

    def write_by_key(self, tunnel_id: int, tag_key: str, value) -> bool:
        raise NotImplementedError

    def last_error(self) -> Optional[str]:
        return self._last_error


class Snap7PLC(BasePLC):
    def __init__(self, cfg: PLCConfig, tunnels: List[TunnelConfig]):
        super().__init__(cfg, tunnels)
        # Carga perezosa de snap7
        try:
            from snap7.client import Client  # type: ignore
            from snap7.util import get_real, set_real, get_bool, set_bool  # type: ignore
            try:
                from snap7.types import Areas as _Areas  # type: ignore
            except Exception:
                from snap7.snap7types import Areas as _Areas  # type: ignore
        except Exception as e:
            raise RuntimeError(f"python-snap7 no disponible: {e}")
        self._Client = Client
        self._get_real = get_real
        self._set_real = set_real
        self._get_bool = get_bool
        self._set_bool = set_bool
        # Áreas (DB, I=PE, Q=PA, M=MK) con fallback numérico
        try:
            self._Areas = _Areas
            # probar atributos
            _ = (_Areas.DB, _Areas.PE, _Areas.PA, _Areas.MK)
        except Exception:
            class _FallbackAreas:
                DB = 0x84
                PE = 0x81
                PA = 0x82
                MK = 0x83
            self._Areas = _FallbackAreas
        # Crear cliente diferido: lo reinstanciaremos en connect() para asegurar
        # que se crea en el hilo correcto y con parámetros limpios
        self.client = None
        self._connected = False

    def connect(self) -> bool:
        try:
            if not self._connected:
                # Re-crear Client cada intento para evitar "Cannot change this param now"
                # y asegurar que el objeto se construye en el hilo del Poller
                try:
                    if self.client is not None:
                        try:
                            self.client.disconnect()
                        except Exception:
                            pass
                    self.client = self._Client()
                except Exception as _:
                    pass

                # Nota: puerto 102 es el predeterminado; algunos wrappers no lo exponen directamente.
                # Pasar puerto desde configuración si está disponible y reintentar con 102 si falla
                port_to_use = getattr(self.cfg, "port", 102) or 102
                connected = False
                try:
                    try:
                        self.client.connect(self.cfg.ip, self.cfg.rack, self.cfg.slot, port_to_use)
                        connected = True
                    except TypeError:
                        # Compatibilidad con versiones antiguas de python-snap7 sin argumento tcpport
                        self.client.connect(self.cfg.ip, self.cfg.rack, self.cfg.slot)
                        connected = True
                except Exception as e1:
                    # Fallback con puerto 102 si el puerto configurado no es 102
                    if port_to_use != 102:
                        try:
                            try:
                                self.client.connect(self.cfg.ip, self.cfg.rack, self.cfg.slot, 102)
                                connected = True
                            except TypeError:
                                self.client.connect(self.cfg.ip, self.cfg.rack, self.cfg.slot)
                                connected = True
                        except Exception as e2:
                            self._last_error = f"Conexión fallida (puerto {port_to_use} y fallback 102): {e1} / {e2}"
                            self._connected = False
                            return False
                    else:
                        self._last_error = f"Conexión fallida (puerto {port_to_use}): {e1}"
                        self._connected = False
                        return False
                self._connected = True
            return True
        except Exception as e:
            self._last_error = f"Conexión fallida: {e}"
            self._connected = False
            return False

    def disconnect(self) -> None:
        try:
            self.client.disconnect()
        except Exception:
            pass
        self._connected = False

    def is_connected(self) -> bool:
        try:
            if self.client is not None:
                # Algunas versiones exponen get_connected()
                if hasattr(self.client, "get_connected"):
                    ok = bool(self.client.get_connected())
                    self._connected = ok
                    return ok
        except Exception:
            self._connected = False
        return self._connected

    def _read_tag(self, tag: TagAddress) -> Optional[Union[float, bool]]:
        try:
            area = getattr(tag, "area", "DB").upper()
            if area == "DB":
                area_const = self._Areas.DB
                dbnum = tag.db
            elif area == "I":
                area_const = self._Areas.PE
                dbnum = 0
            elif area == "Q":
                area_const = self._Areas.PA
                dbnum = 0
            else:  # M
                area_const = self._Areas.MK
                dbnum = 0

            if tag.type.upper() == "REAL":
                data = self.client.read_area(area_const, dbnum, tag.start, 4)
                return float(self._get_real(data, 0))
            elif tag.type.upper() == "BOOL":
                data = self.client.read_area(area_const, dbnum, tag.start, 1)
                return bool(self._get_bool(data, 0, tag.bit))
            else:
                return None
        except Exception as e:
            self._last_error = f"Lectura fallida DB{tag.db}.{tag.start}/{tag.type}: {e}"
            self._connected = False
            return None

    def _write_tag(self, tag: TagAddress, value) -> bool:
        try:
            area = getattr(tag, "area", "DB").upper()
            if area == "DB":
                area_const = self._Areas.DB
                dbnum = tag.db
            elif area == "I":
                area_const = self._Areas.PE
                dbnum = 0
            elif area == "Q":
                area_const = self._Areas.PA
                dbnum = 0
            else:  # M
                area_const = self._Areas.MK
                dbnum = 0

            if tag.type.upper() == "REAL":
                b = bytearray(4)
                self._set_real(b, 0, float(value))
                self.client.write_area(area_const, dbnum, tag.start, b)
                return True
            elif tag.type.upper() == "BOOL":
                # leer byte actual para preservar otros bits
                current = self.client.read_area(area_const, dbnum, tag.start, 1)
                b = bytearray(current)
                self._set_bool(b, 0, tag.bit, bool(value))
                self.client.write_area(area_const, dbnum, tag.start, b)
                return True
            else:
                return False
        except Exception as e:
            self._last_error = f"Escritura fallida DB{tag.db}.{tag.start}/{tag.type}: {e}"
            self._connected = False
            return False

    def read_all(self) -> Dict[int, TunnelData]:
        out: Dict[int, TunnelData] = {}
        if not self._connected and not self.connect():
            return out
        for tid, tcfg in self.tunnels_map.items():
            try:
                ta = tcfg.tags
                amb = self._read_tag(ta["temp_ambiente"]) or 0.0
                p1 = self._read_tag(ta["temp_pulpa1"]) or 0.0
                p2 = self._read_tag(ta["temp_pulpa2"]) or 0.0
                sp = self._read_tag(ta["setpoint"]) or 0.0
                sp_p1 = self._read_tag(ta["setpoint_pulpa1"]) if "setpoint_pulpa1" in ta else 0.0
                sp_p2 = self._read_tag(ta["setpoint_pulpa2"]) if "setpoint_pulpa2" in ta else 0.0
                est = self._read_tag(ta["estado"]) or False
                td = TunnelData(
                    id=tcfg.id,
                    name=tcfg.name,
                    temp_ambiente=float(amb),
                    temp_pulpa1=float(p1),
                    temp_pulpa2=float(p2),
                    setpoint=float(sp),
                    setpoint_pulpa1=float(sp_p1 or 0.0),
                    setpoint_pulpa2=float(sp_p2 or 0.0),
                    estado=bool(est),
                )
                out[tid] = td
            except Exception as e:
                self._last_error = f"Lectura túnel {tcfg.id} fallida: {e}"
                self._connected = False
                return out
        return out

    def write_setpoint(self, tunnel_id: int, value: float) -> bool:
        tcfg = self.tunnels_map.get(tunnel_id)
        if not tcfg:
            self._last_error = f"Túnel {tunnel_id} no encontrado"
            return False
        tag = tcfg.tags.get("setpoint")
        if not tag:
            self._last_error = f"Tag setpoint no definido para túnel {tunnel_id}"
            return False
        if not self._connected and not self.connect():
            return False
        return self._write_tag(tag, float(value))

    def write_estado(self, tunnel_id: int, value: bool) -> bool:
        tcfg = self.tunnels_map.get(tunnel_id)
        if not tcfg:
            self._last_error = f"Túnel {tunnel_id} no encontrado"
            return False
        tag = tcfg.tags.get("estado")
        if not tag:
            self._last_error = f"Tag estado no definido para túnel {tunnel_id}"
            return False
        if not self._connected and not self.connect():
            return False
        return self._write_tag(tag, bool(value))

    def write_setpoint_p1(self, tunnel_id: int, value: float) -> bool:
        tcfg = self.tunnels_map.get(tunnel_id)
        if not tcfg:
            self._last_error = f"Túnel {tunnel_id} no encontrado"
            return False
        tag = tcfg.tags.get("setpoint_pulpa1")
        if not tag:
            self._last_error = f"Tag setpoint_pulpa1 no definido para túnel {tunnel_id}"
            return False
        if not self._connected and not self.connect():
            return False
        return self._write_tag(tag, float(value))

    def write_setpoint_p2(self, tunnel_id: int, value: float) -> bool:
        tcfg = self.tunnels_map.get(tunnel_id)
        if not tcfg:
            self._last_error = f"Túnel {tunnel_id} no encontrado"
            return False
        tag = tcfg.tags.get("setpoint_pulpa2")
        if not tag:
            self._last_error = f"Tag setpoint_pulpa2 no definido para túnel {tunnel_id}"
            return False
        if not self._connected and not self.connect():
            return False
        return self._write_tag(tag, float(value))

    def write_by_key(self, tunnel_id: int, tag_key: str, value) -> bool:
        tcfg = self.tunnels_map.get(tunnel_id)
        if not tcfg:
            self._last_error = f"Túnel {tunnel_id} no encontrado"
            return False
        tag = tcfg.tags.get(tag_key)
        if not tag:
            self._last_error = f"Tag {tag_key} no definido para túnel {tunnel_id}"
            return False
        if not self._connected and not self.connect():
            return False
        return self._write_tag(tag, value)
