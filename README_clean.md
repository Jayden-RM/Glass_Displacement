# Glass Displacement

Control and analysis software for the Tandem PV Glass Displacement measurement system.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)  
![GUI](https://img.shields.io/badge/GUI-PyQt5-green.svg)  
![Status](https://img.shields.io/badge/status-beta-orange.svg)  
![License](https://img.shields.io/badge/license-MIT-purple.svg)  
![Last Commit](https://img.shields.io/github/last-commit/jaydenig/Glass_Displacement/main)

---

<details>
<summary><strong>📑 Table of Contents</strong> (click to expand)</summary>

- [Overview](#overview)
- [Features](#features)
- [GUI Preview](#gui-preview)
- [Quick Start](#quick-start-recommended-anaconda)
- [Launching the Application](#launching-the-application-ipython-recommended)
- [Measurement Workflow](#typical-measurement-workflow)
- [Hardware Requirements](#hardware-requirements)
- [Troubleshooting](#troubleshooting)
- [Development Status](#development-status)
- [Authors](#authors)
- [License](#license)

</details>

---

## Overview

Glass Displacement provides automated XY stage motion, laser displacement sensing, and real-time visualization through a PyQt5 graphical interface. The software is designed for high-precision surface mapping workflows in research and production environments.

---

## Features

- Automated serpentine grid scanning
- UDP motor control for XY stage
- High-precision laser displacement measurements
- Interactive PyQt5 graphical interface
- Real-time progress tracking
- 2D and 3D surface visualization
- Abort-safe measurement handling
- CSV export of measurement data

---

## GUI Preview

![GUI Screenshot](docs/images/gui.png)

---

## Quick Start (Recommended: Anaconda)

This project runs most reliably inside an Anaconda environment, especially on Windows systems using PyQt5.

### 1. Create environment

conda create -n glass_disp python=3.10  
conda activate glass_disp

### 2. Install the project

pip install -e .

---

## Launching the Application (IPython Recommended)

Start IPython:

ipython

Then run:

from Glass_Displacement.Glass_Displacement import GD_UI  
GD_UI()

### Why IPython?

- Faster iteration during hardware testing
- Easier debugging
- Avoids repeated script restarts
- Better interactive workflow for lab environments

---

## Typical Measurement Workflow

1. Connect motors and displacement sensor
2. Launch the GUI
3. Home the stage
4. Configure grid width, length, and resolution
5. Run measurement
6. Review plots
7. Save results

The scan uses a serpentine traversal pattern with stabilization delays between moves.

---

## Hardware Requirements

### XY Stage

- Dual motor screw drive
- UDP communication
- Static IP configuration required

### Displacement Sensor

- FTDI serial interface
- 921600 baud
- Automatic port detection supported

---

## Troubleshooting

### PyQt fails to launch

- Use the Anaconda workflow above
- Ensure PyQt5 installs inside the same environment
- Avoid mixing system Python with conda

### Motors not responding

- Verify PC and motors are on the same subnet
- Check UDP ports are not blocked
- Confirm motor controller IP settings

### Sensor not detected

- Confirm FTDI device appears in Device Manager
- Verify COM port permissions
- Check USB cable and power

---

## Development Status

**Beta** — active development and internal use.

---

## Authors

- Sean P. Dunfield — Original implementation  
- Jayden — Major modifications, stability improvements, and UI enhancements  

---

## License

MIT License (see LICENSE file)
