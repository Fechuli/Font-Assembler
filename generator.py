"""
Modulo per la generazione asincrona del font.
Contiene il thread di generazione per evitare il blocco dell'interfaccia.
"""

import os
import random
import traceback
from string import ascii_uppercase

from PyQt5.QtCore import QThread, pyqtSignal
from fontTools.ttLib import TTFont

from geometry_utils import polygon_from_contour, polygon_to_contours, normalize_glyph_polygon
from font_utils import get_glyph_contours
from glyph_processing import (
    mix_multiple_polygons, mix_fonts_deterministic, 
    assemble_letter_multiple_fonts
)
from font_assembly import create_alphabet_font


class FontGeneratorThread(QThread):
    """
    Thread per la generazione del font in background.
    Evita il blocco dell'interfaccia durante l'elaborazione.
    """
    update_progress = pyqtSignal(int, str)  # (percentuale, messaggio)
    generation_complete = pyqtSignal(bool, str, dict)  # (successo, messaggio, lettere)
    
    def __init__(self, font_paths, cut_method, h_cuts=None, v_cuts=None, normalize=True, use_vertical_cuts=False, font_name="MixedFont"):
        super().__init__()
        self.font_paths = font_paths
        self.cut_method = cut_method
        self.h_cuts = h_cuts if h_cuts else []
        self.v_cuts = v_cuts if v_cuts else []
        self.normalize = normalize
        self.use_vertical_cuts = use_vertical_cuts
        self.font_name = font_name
        self.letters_dict = {}
        self.output_path = os.path.join("output", f"{self.font_name}.ttf")
    
    def run(self):
        """Esegue la generazione del font in un thread separato"""
        try:
            num_fonts = len(self.font_paths)
            if num_fonts < 2:
                self.generation_complete.emit(False, "Servono almeno 2 font", {})
                return

            # Preparazione della cartella output
            os.makedirs("output", exist_ok=True)
            
            self.update_progress.emit(5, "Inizializzazione...")
            
            # Scelta del metodo di taglio
            if self.cut_method == "casuale":
                cut_method_name = "random"
                h_cut_points = [random.uniform(0.2, 0.8) for _ in range(num_fonts - 1)]
                h_cut_points.sort()
                
                if self.use_vertical_cuts:
                    v_cut_points = [random.uniform(0.2, 0.8) for _ in range(num_fonts - 1)]
                    v_cut_points.sort()
                else:
                    v_cut_points = []
                    
            elif self.cut_method == "equidistante":
                cut_method_name = "equal"
                h_cut_points = [float(i+1)/num_fonts for i in range(num_fonts - 1)]
                
                if self.use_vertical_cuts:
                    v_cut_points = h_cut_points.copy()
                else:
                    v_cut_points = []
                    
            else:  # personalizzato
                cut_method_name = "custom"
                h_cut_points = self.h_cuts[:num_fonts-1] if self.h_cuts else [0.5] * (num_fonts - 1)
                
                if self.use_vertical_cuts and self.v_cuts:
                    v_cut_points = self.v_cuts[:num_fonts-1]
                else:
                    v_cut_points = []
            
            # Scelta del metodo di mixaggio
            mix_method = "checkerboard" if self.use_vertical_cuts else "horizontal"
            
            # Crea un dizionario per memorizzare le lettere generate
            self.letters_dict = {}
            letters = list(ascii_uppercase)
            
            # Processa ogni lettera dell'alfabeto
            for i, letter in enumerate(letters):
                progress = 5 + int(85 * (i / len(letters)))
                self.update_progress.emit(progress, f"Elaborazione lettera {letter}...")
                
                try:
                    # Decidi se usare parametri diversi per ogni lettera (per varietà)
                    if cut_method_name == "random":
                        # Genera nuovi punti casuali per ogni lettera
                        h_cuts = [random.uniform(0.2, 0.8) for _ in range(num_fonts - 1)]
                        h_cuts.sort()
                        
                        if self.use_vertical_cuts:
                            v_cuts = [random.uniform(0.2, 0.8) for _ in range(num_fonts - 1)]
                            v_cuts.sort()
                        else:
                            v_cuts = []
                    else:
                        # Usa i punti di taglio globali
                        h_cuts = h_cut_points
                        v_cuts = v_cut_points
                    
                    # Debug: mostra i valori usati per il mixaggio
                    print(f"\nMixaggio lettera {letter}:")
                    print(f"- Tagli orizzontali: {h_cuts}")
                    print(f"- Tagli verticali: {v_cuts}")
                    print(f"- Metodo di mixaggio: {mix_method}")
                    
                    # Usando la funzione migliorata per assemblare lettere
                    poly = assemble_letter_multiple_fonts(
                        self.font_paths, 
                        letter, 
                        h_cuts, 
                        v_cuts, 
                        self.normalize,
                        mix_method
                    )
                    
                    # Converti il poligono risultante in contorni
                    if poly:
                        contours = polygon_to_contours(poly)
                        self.letters_dict[letter] = contours
                    else:
                        self.letters_dict[letter] = []
                        
                except Exception as e:
                    print(f"Errore nell'elaborazione della lettera {letter}: {str(e)}")
                    traceback.print_exc()
                    # Se c'è un errore, metti un contorno vuoto
                    self.letters_dict[letter] = []
            
            self.update_progress.emit(90, "Creazione del font...")
            
            # Crea il percorso di output
            import time
            timestamp = int(time.time())
            
            self.output_path = os.path.join("output", f"{self.font_name}.ttf")
            alt_output_path = os.path.join("output", f"{self.font_name}_{timestamp}.ttf")
            
            # Crea il font con le lettere generate
            success, result = create_alphabet_font(self.letters_dict, self.output_path, self.font_name)
            
            if success and isinstance(result, str) and os.path.exists(result):
                self.output_path = result
                
            self.update_progress.emit(100, "Completato!")
            
            if success:
                self.generation_complete.emit(True, self.output_path, self.letters_dict)
            else:
                # Se c'è un errore di permesso, prova con un nome alternativo
                if "Permission denied" in str(result):
                    success, result = create_alphabet_font(self.letters_dict, alt_output_path, self.font_name)
                    if success:
                        self.output_path = alt_output_path
                        self.generation_complete.emit(True, self.output_path, self.letters_dict)
                        return
                
                self.generation_complete.emit(False, f"Errore: {result}", {})
                
        except Exception as e:
            traceback.print_exc()  
            
            self.update_progress.emit(0, f"Errore: {str(e)}")
            self.generation_complete.emit(False, f"Errore: {str(e)}", {})