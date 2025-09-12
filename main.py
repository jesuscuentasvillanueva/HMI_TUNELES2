import sys
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, QMetaObject, Qt, QTimer

from hmi.config import ConfigManager
from hmi.simulator import SimulatedPLC
from hmi.plc_client import Snap7PLC, BasePLC
from hmi.workers import Poller
from hmi.ui.main_window import MainWindow


def build_plc(plc_cfg, tunnels):
    # Selecciona implementación según configuración.
    if getattr(plc_cfg, "simulation", True):
        return SimulatedPLC(plc_cfg, tunnels)
    # Intentar Snap7, si falla usar Simulación
    try:
        return Snap7PLC(plc_cfg, tunnels)
    except Exception as e:
        print(f"[WARN] No se pudo inicializar Snap7 ({e}). Usando Simulación.")
        sim_cfg = plc_cfg
        setattr(sim_cfg, "simulation", True)
        return SimulatedPLC(sim_cfg, tunnels)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("HMI Tuneles")

    # Cargar tema
    theme_path = Path(__file__).resolve().parent / "hmi" / "ui" / "theme.qss"
    if theme_path.exists():
        app.setStyleSheet(theme_path.read_text(encoding="utf-8"))

    # Configuración
    cfg_manager = ConfigManager()
    app_cfg = cfg_manager.load_or_create_default()

    tunnels = app_cfg.tunnels
    plc_cfg = app_cfg.plc

    # PLC y worker de sondeo en hilo dedicado
    plc: BasePLC = build_plc(plc_cfg, tunnels)

    poller_thread = QThread()
    poller = Poller(plc=plc, tunnels=tunnels, interval_ms=plc_cfg.poll_interval_ms)
    poller.moveToThread(poller_thread)

    # UI principal
    window = MainWindow(tunnels=tunnels, initial_plc_connected=False)

    # Conexiones señales/slots
    poller.updated.connect(window.on_data_update)
    poller.plc_status_changed.connect(window.on_plc_status)
    poller.plc_error.connect(window.on_plc_error)

    window.request_setpoint.connect(poller.write_setpoint)
    window.request_setpoint_p1.connect(poller.write_setpoint_p1)
    window.request_setpoint_p2.connect(poller.write_setpoint_p2)
    window.request_estado.connect(poller.write_estado)
    window.request_deshielo.connect(poller.trigger_deshielo)
    window.request_deshielo_set.connect(poller.set_deshielo)
    window.update_tunnel_tags.connect(poller.update_tunnel_tags)
    window.update_tunnel_calibrations.connect(poller.update_tunnel_calibrations)

    def apply_settings(new_plc_cfg):
        # Guardar y reiniciar infraestructura
        nonlocal plc, poller, poller_thread, app_cfg
        app_cfg.plc = new_plc_cfg
        cfg_manager.save(app_cfg)

        # Parar hilo anterior
        try:
            QMetaObject.invokeMethod(poller, "stop", Qt.QueuedConnection)
        except Exception:
            pass
        poller_thread.quit()
        poller_thread.wait()

        # Re-crear PLC y Poller
        plc = build_plc(new_plc_cfg, tunnels)
        poller_thread = QThread()
        poller = Poller(plc=plc, tunnels=tunnels, interval_ms=new_plc_cfg.poll_interval_ms)
        poller.moveToThread(poller_thread)

        # Re-conectar señales
        poller.updated.connect(window.on_data_update)
        poller.plc_status_changed.connect(window.on_plc_status)
        poller.plc_error.connect(window.on_plc_error)
        window.request_setpoint.connect(poller.write_setpoint)
        window.request_setpoint_p1.connect(poller.write_setpoint_p1)
        window.request_setpoint_p2.connect(poller.write_setpoint_p2)
        window.request_estado.connect(poller.write_estado)
        window.request_deshielo.connect(poller.trigger_deshielo)
        window.request_deshielo_set.connect(poller.set_deshielo)
        window.update_tunnel_tags.connect(poller.update_tunnel_tags)
        window.update_tunnel_calibrations.connect(poller.update_tunnel_calibrations)

        # Iniciar
        poller_thread.started.connect(poller.start)
        poller_thread.start()

    window.apply_settings.connect(apply_settings)

    # Prueba de conexión desde vista de configuración
    def test_connection(plc_cfg):
        if getattr(plc_cfg, "simulation", False):
            window.view_settings.show_test_result("Modo Simulación activo. No se requiere conexión.", True)
            return
        try:
            tmp = Snap7PLC(plc_cfg, tunnels)
        except Exception as e:
            window.view_settings.show_test_result(f"No se pudo inicializar Snap7: {e}", False)
            return
        ok = tmp.connect()
        if ok:
            window.view_settings.show_test_result(
                f"Conectado a {plc_cfg.ip}:{getattr(plc_cfg, 'port', 102)} (rack {plc_cfg.rack}, slot {plc_cfg.slot})",
                True,
            )
            try:
                tmp.disconnect()
            except Exception:
                pass
        else:
            window.view_settings.show_test_result(tmp.last_error() or "Fallo de conexión", False)

    window.view_settings.test_connection.connect(test_connection)

    # Arrancar sondeo
    poller_thread.started.connect(poller.start)
    poller_thread.start()

    # Cierre ordenado al salir de la app
    def on_about_to_quit():
        try:
            QMetaObject.invokeMethod(poller, "stop", Qt.QueuedConnection)
        except Exception:
            pass
        poller_thread.quit()
        poller_thread.wait()

    app.aboutToQuit.connect(on_about_to_quit)

    # Ajustar geometría a pantalla disponible
    try:
        screen = app.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            window.setGeometry(geo)
            window.setMinimumSize(geo.width(), geo.height())
    except Exception:
        pass

    # Mostrar en pantalla completa y reforzar tras iniciar el bucle de eventos
    window.showFullScreen()

    def enforce_fullscreen():
        if not window.isFullScreen():
            window.showFullScreen()

    def fallback_maximized():
        if not window.isFullScreen():
            window.showMaximized()

    QTimer.singleShot(0, enforce_fullscreen)
    QTimer.singleShot(250, enforce_fullscreen)
    QTimer.singleShot(800, fallback_maximized)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
