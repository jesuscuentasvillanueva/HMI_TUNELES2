from dataclasses import dataclass, field
from typing import Dict, List, Optional
from time import time


@dataclass
class TagAddress:
    db: int
    start: int
    type: str  # "REAL" or "BOOL"
    bit: int = 0


@dataclass
class TunnelConfig:
    id: int
    name: str
    tags: Dict[str, TagAddress]


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
    estado: bool = False
    ts: float = field(default_factory=time)


@dataclass
class AppConfig:
    plc: PLCConfig
    tunnels: List[TunnelConfig]
