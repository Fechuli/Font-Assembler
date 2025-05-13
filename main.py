"""
Entry point dell'applicazione Font Mixer.
Avvia la GUI e imposta le cartelle necessarie.
"""

import os
import sys
from PyQt5.QtWidgets import QApplication

from gui import FontMixerApp


def main():
    """
    Funzione principale che avvia l'applicazione.
    Crea le cartelle necessarie e inizializza l'interfaccia.
    """
    app = QApplication(sys.argv)
    
    for folder in ["fonts", "output"]:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    window = FontMixerApp()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()