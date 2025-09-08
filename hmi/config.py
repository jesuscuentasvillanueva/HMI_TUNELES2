import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from .models import AppConfig, PLCConfig, TagAddress, TunnelConfig


class ConfigManager:
    def __init__(self, path: Optional[Path] = None):
        self.root = Path(__file__).resolve().parent.parent
        self.config_dir = self.root / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.path = path or (self.config_dir / "config.json")

    def load_or_create_default(self) -> AppConfig:
        if self.path.exists():
            return self.load()
        cfg = self.default_config()
        self.save(cfg)
        return cfg

    def load(self) -> AppConfig:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        plc_data = data.get("plc", {})
        plc = PLCConfig(**plc_data)
        tunnels_list = []
        for t in data.get("tunnels", []):
            tags = {k: TagAddress(**v) for k, v in t.get("tags", {}).items()}
            calibrations = t.get("calibrations", {})
            tunnels_list.append(TunnelConfig(id=t["id"], name=t["name"], tags=tags, calibrations=calibrations))
        return AppConfig(plc=plc, tunnels=tunnels_list)

    def save(self, cfg: AppConfig) -> None:
        data = {
            "plc": asdict(cfg.plc),
            "tunnels": [
                {
                    "id": t.id,
                    "name": t.name,
                    "tags": {k: asdict(v) for k, v in t.tags.items()},
                    "calibrations": t.calibrations,
                }
                for t in cfg.tunnels
            ],
        }
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def default_config(self) -> AppConfig:
        plc = PLCConfig(
            ip="192.168.0.1",
            rack=0,
            slot=1,
            port=102,
            poll_interval_ms=1000,
            simulation=True,
        )
        tunnels: List[TunnelConfig] = []
        # Genera 14 túneles con DBs únicos por defecto
        for i in range(1, 15):
            name = f"Túnel {i}"
            base_temp_db = 100 + i
            base_sp_db = 200 + i
            base_state_db = 300 + i
            tags = {
                "temp_ambiente": TagAddress(db=base_temp_db, start=0, type="REAL"),
                "temp_pulpa1": TagAddress(db=base_temp_db, start=4, type="REAL"),
                "temp_pulpa2": TagAddress(db=base_temp_db, start=8, type="REAL"),
                "setpoint": TagAddress(db=base_sp_db, start=0, type="REAL"),
                "estado": TagAddress(db=base_state_db, start=0, type="BOOL", bit=0),
            }
            tunnels.append(TunnelConfig(id=i, name=name, tags=tags))
        return AppConfig(plc=plc, tunnels=tunnels)
