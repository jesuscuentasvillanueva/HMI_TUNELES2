# HMI Túneles de Enfriamiento (PyQt5 + python-snap7)

Aplicación HMI en pantalla completa para supervisar y controlar 14 túneles de enfriamiento con Siemens S7 (vía python-snap7). Incluye:

- Tablero principal con 14 túneles (Temperatura ambiente, Pulpa1, Pulpa2, Setpoint y Estado).
- Pantalla de detalle de túnel (Encendido/Apagado, Setpoint manual, lecturas en grande).
- Pantalla de configuración de conexión (IP, rack, slot, puerto, intervalo, modo simulación).
- Modo simulación para pruebas sin PLC.
- Tema oscuro industrial y uso eficiente del espacio de pantalla.

## Requisitos

- Python 3.8+
- Qt 5 (PyQt5)
- python-snap7 (requiere libsnap7 en Linux)

En Linux (Debian/Ubuntu) puede que necesites instalar libsnap7:

```bash
sudo apt-get update
sudo apt-get install -y libsnap7-1 libsnap7-dev
```

## Instalación

```bash
# (opcional) crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# instalar dependencias
pip install -r requirements.txt
```

## Ejecución

```bash
python3 main.py
```

La primera ejecución creará `config/config.json` con una configuración por defecto (modo simulación activado). Ajusta la IP/rack/slot/puerto y desactiva "Simulación" desde la pantalla de Configuración para conectar a tu PLC.

## Notas

- La asignación de direcciones (DB/start/bit/tipo) por túnel se define en `config/config.json`. Por simplicidad, se generan DBs por defecto diferentes para cada túnel. Ajusta estos valores para tu proyecto real.
- El sondeo se realiza en un hilo separado y la aplicación intenta reconectarse automáticamente si la conexión se pierde.
- UI en pantalla completa. Usa `Alt+F4` o el botón de la ventana para salir.
