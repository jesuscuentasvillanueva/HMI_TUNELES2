from dataclasses import dataclass, field
from typing import Dict, List, Optional
from time import time


@dataclass
class TagAddress:
    db: int
    start: int
    type: str  # "REAL" or "BOOL"
    bit: int = 0
    area: str = "DB"  # "DB", "I", "Q", "M"


@dataclass
class TunnelConfig:
    id: int
    name: str
    tags: Dict[str, TagAddress]
    calibrations: Dict[str, float] = field(default_factory=dict)  # offsets por señal


@dataclass
class PLCConfig:
    ip: str = "192.168.0.1"
    rack: int = 0
    slot: int = 1
    port: int = 102
    poll_interval_ms: int = 1000
    simulation: bool = True


@dataclass
class TunnelData:
    id: int
    name: str
    temp_ambiente: float = 0.0
    temp_pulpa1: float = 0.0
    temp_pulpa2: float = 0.0
    setpoint: float = 0.0
    setpoint_pulpa1: float = 0.0
    setpoint_pulpa2: float = 0.0
    estado: bool = False
    deshielo_activo: bool = False
    valvula_posicion: float = 0.0
    ts: float = field(default_factory=time)


@dataclass
class AppConfig:
    plc: PLCConfig
    tunnels: List[TunnelConfig]
    ui: dict = field(default_factory=dict)
