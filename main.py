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
    # Crea l'applicazione QT
    app = QApplication(sys.argv)
    
    # Assicurati che le cartelle necessarie esistano
    for folder in ["fonts", "output"]:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    # Inizializza e mostra la finestra principale
    window = FontMixerApp()
    window.show()
    
    # Entra nel loop degli eventi
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()