#!/usr/bin/env python3.12
"""
ACSR Transmission Line Calculator
Entry point – bootstraps the MVC stack and launches the GUI.
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, "ACSR-Tabla-RMG.csv")

    # Load the conductor database before creating the main window so that
    # a missing CSV can be reported before the UI appears.
    try:
        from model.conductor_db import ConductorDatabase
        db = ConductorDatabase(csv_path)
    except FileNotFoundError as exc:
        _fatal_error(
            "Archivo no encontrado",
            f"{exc}\n\n"
            "Asegúrese de que el archivo 'ACSR-Tabla-RMG.csv' se encuentre "
            "en el mismo directorio que main.py.",
        )
        return
    except Exception as exc:
        _fatal_error("Error al cargar el catálogo", str(exc))
        return

    from view.main_view import MainView
    from controller.app_controller import AppController

    view = MainView()
    AppController(view, db)
    view.mainloop()


def _fatal_error(title: str, message: str):
    """Show a messagebox error before the main window exists and exit."""
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(title, message)
    root.destroy()
    sys.exit(1)


if __name__ == "__main__":
    main()
