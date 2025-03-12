"""
Modulo per l'interfaccia grafica principale.
Contiene la finestra principale e la gestione degli eventi dell'interfaccia.
"""

import os
import sys
import traceback
import random
from string import ascii_uppercase

# PyQt5 per la GUI
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, 
    QWidget, QComboBox, QListWidget, QSlider, QTabWidget,
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QScrollArea,
    QGridLayout, QSizePolicy, QLineEdit, QListWidgetItem, QCheckBox,
    QDialog, QTextEdit
)
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtCore import Qt

from fontTools.ttLib import TTFont

from visualization import LetterPreviewWidget, AlphabetPreviewWidget
from generator import FontGeneratorThread


class FontMixerApp(QMainWindow):
    """
    Finestra principale dell'applicazione.
    Gestisce l'interfaccia utente e le operazioni di mixaggio.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Font Mixer - Generatore di Font Ibridi")
        self.setMinimumSize(900, 700)
        
        self.font_paths = []
        self.available_fonts = []
        self.selected_fonts = []
        self.cut_method = "random"
        self.custom_cuts = [0.5] 
        self.letters_dict = {}
        self.output_font_path = ""
        
        self.setupUi()
        self.loadAvailableFonts()
        
    def setupUi(self):
        """Configura l'interfaccia utente"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        self.tabs = QTabWidget()
        self.tab_generator = QWidget()
        self.tab_preview = QWidget()
        
        self.tabs.addTab(self.tab_generator, "Generatore")
        self.tabs.addTab(self.tab_preview, "Anteprima")
        
        main_layout.addWidget(self.tabs)
        
        # --- TAB GENERATORE ---
        generator_layout = QVBoxLayout(self.tab_generator)
        
        font_group = QGroupBox("Selezione Font")
        font_layout = QVBoxLayout(font_group)
        
        add_font_layout = QHBoxLayout()
        self.font_list = QListWidget()
        self.font_list.setSelectionMode(QListWidget.ExtendedSelection)
        
        font_buttons_layout = QVBoxLayout()
        self.btn_add_font = QPushButton("Aggiungi Font...")
        self.btn_remove_font = QPushButton("Rimuovi Font")
        self.btn_move_up = QPushButton("↑ Sposta Su")
        self.btn_move_down = QPushButton("↓ Sposta Giù")
        
        font_buttons_layout.addWidget(self.btn_add_font)
        font_buttons_layout.addWidget(self.btn_remove_font)
        font_buttons_layout.addWidget(self.btn_move_up)
        font_buttons_layout.addWidget(self.btn_move_down)
        font_buttons_layout.addStretch()
        
        add_font_layout.addWidget(self.font_list, 3)
        add_font_layout.addLayout(font_buttons_layout, 1)
        
        font_layout.addLayout(add_font_layout)
        
        mix_group = QGroupBox("Opzioni di Mixaggio")
        mix_layout = QVBoxLayout(mix_group)
        
        self.setupMixingOptions(mix_layout)
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nome del font:"))
        self.font_name_edit = QLineEdit("MixedFont")
        name_layout.addWidget(self.font_name_edit)
        
        mix_layout.addLayout(name_layout)
        
        generate_layout = QHBoxLayout()
        self.btn_generate = QPushButton("GENERA FONT")
        self.btn_generate.setMinimumHeight(40)
        generate_layout.addWidget(self.btn_generate)
        
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_status = QLabel("Pronto")
        progress_layout.addWidget(self.progress_bar, 3)
        progress_layout.addWidget(self.progress_status, 1)
        
        generator_layout.addWidget(font_group, 3)
        generator_layout.addWidget(mix_group, 2)
        generator_layout.addLayout(generate_layout)
        generator_layout.addLayout(progress_layout)
        
        # --- TAB ANTEPRIMA ---
        preview_layout = QVBoxLayout(self.tab_preview)
        
        preview_controls_layout = QHBoxLayout()
        
        # Lettere scroll
        letters_scroll = QScrollArea()
        letters_scroll.setWidgetResizable(True)
        letters_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        letters_container = QWidget()
        
        # Inizializza i widget per le lettere
        self.letter_widgets = {}
        letters_grid_layout = QGridLayout(letters_container)
        
        # Prima riga: Lettere maiuscole
        row = 0
        for i, letter in enumerate(ascii_uppercase):
            col = i % 7  # 7 colonne
            if i > 0 and i % 7 == 0:
                row += 1
                
            letter_widget = LetterPreviewWidget(letter)
            letters_grid_layout.addWidget(letter_widget, row, col)
            self.letter_widgets[letter] = letter_widget
        
        # Righe successive: Lettere minuscole
        lowercase_start_row = (len(ascii_uppercase) + 6) // 7  # Calcola la riga iniziale per le minuscole
        row = lowercase_start_row
        for i, letter in enumerate('abcdefghijklmnopqrstuvwxyz'):
            col = i % 7  # 7 colonne
            if i > 0 and i % 7 == 0:
                row += 1
                
            letter_widget = LetterPreviewWidget(letter)
            letters_grid_layout.addWidget(letter_widget, row, col)
            self.letter_widgets[letter] = letter_widget
        
        letters_scroll.setWidget(letters_container)
        
        preview_controls = QWidget()
        preview_controls_panel = QVBoxLayout(preview_controls)
        
        self.preview_label = QLabel("Anteprima Font")
        self.preview_label.setAlignment(Qt.AlignCenter)
        
        self.btn_export = QPushButton("Esporta Font...")
        self.btn_export.setEnabled(False)
        
        self.btn_load_in_system = QPushButton("Carica nel Sistema")
        self.btn_load_in_system.setEnabled(False)
        
        self.btn_test_text = QPushButton("Apri Editor di Testo")
        self.btn_test_text.setEnabled(False)
        
        preview_controls_panel.addWidget(self.preview_label)
        preview_controls_panel.addWidget(self.btn_export)
        preview_controls_panel.addWidget(self.btn_load_in_system)
        preview_controls_panel.addWidget(self.btn_test_text)
        preview_controls_panel.addStretch()
        
        preview_controls_layout.addWidget(letters_scroll, 7)
        preview_controls_layout.addWidget(preview_controls, 3)
        
        preview_alphabet_group = QGroupBox("Anteprima Alfabeto Completo")
        preview_alphabet_layout = QVBoxLayout(preview_alphabet_group)
        
        self.alphabet_preview = AlphabetPreviewWidget()
        preview_alphabet_layout.addWidget(self.alphabet_preview)
        
        preview_layout.addLayout(preview_controls_layout, 7)
        preview_layout.addWidget(preview_alphabet_group, 3)
        
        # --- CONNESSIONI ---
        self.check_vertical_cuts.stateChanged.connect(self.onVerticalCutsChanged)
        self.btn_add_font.clicked.connect(self.onAddFont)
        self.btn_remove_font.clicked.connect(self.onRemoveFont)
        self.btn_move_up.clicked.connect(self.onMoveUp)
        self.btn_move_down.clicked.connect(self.onMoveDown)
        self.btn_generate.clicked.connect(self.onGenerateFont)
        self.combo_cut_method.currentIndexChanged.connect(self.onCutMethodChanged)
        self.btn_export.clicked.connect(self.onExportFont)
        self.btn_load_in_system.clicked.connect(self.onLoadInSystem)
        self.btn_test_text.clicked.connect(self.onOpenTextEditor)
        self.font_list.itemSelectionChanged.connect(self.updateUI)

        self.updateUI()
        
    def onVerticalCutsChanged(self, state):
        """Gestisce l'attivazione/disattivazione dei tagli verticali"""
        use_vertical = state == Qt.Checked
        
        if self.combo_cut_method.currentText() == "Personalizzato":
            self.v_cuts_group.setVisible(use_vertical)
            
        if self.letters_dict:
            self.updateLetterPreviews()
        
    def setupMixingOptions(self, mix_layout):
        """Configura le opzioni di mixaggio avanzate"""
        # Metodo di taglio
        cut_method_layout = QHBoxLayout()
        cut_method_layout.addWidget(QLabel("Metodo di taglio:"))
        self.combo_cut_method = QComboBox()
        self.combo_cut_method.addItems([
            "Casuale", 
            "Equidistante", 
            "Personalizzato", 
        ])
        cut_method_layout.addWidget(self.combo_cut_method)
        mix_layout.addLayout(cut_method_layout)
        
        # Normalizzazione dimensione
        norm_layout = QHBoxLayout()
        norm_layout.addWidget(QLabel("Normalizza dimensione:"))
        self.check_normalize = QCheckBox()
        self.check_normalize.setChecked(True)
        norm_layout.addWidget(self.check_normalize)
        
        norm_layout.addSpacing(20)
        norm_layout.addWidget(QLabel("Attiva tagli verticali:"))
        self.check_vertical_cuts = QCheckBox()
        self.check_vertical_cuts.setChecked(False)
        norm_layout.addWidget(self.check_vertical_cuts)
        norm_layout.addStretch()
        
        mix_layout.addLayout(norm_layout)
    
        
        # Gruppo taglio orizzontale
        self.h_cuts_group = QGroupBox("Punti di taglio orizzontali")
        h_cuts_layout = QGridLayout(self.h_cuts_group)
        
        self.h_cut_sliders = []
        
        for i in range(4):  
            slider = QSlider(Qt.Horizontal)
            slider.setRange(10, 90)
            slider.setValue(50)
            slider.setEnabled(False)
            
            label = QLabel(f"Taglio H {i+1}:")
            value_label = QLabel("50%")
            
            h_cuts_layout.addWidget(label, i, 0)
            h_cuts_layout.addWidget(slider, i, 1)
            h_cuts_layout.addWidget(value_label, i, 2)
            
            slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(f"{v}%"))
            slider.valueChanged.connect(self.updateCutPreview)
            
            self.h_cut_sliders.append((slider, value_label))
            
        mix_layout.addWidget(self.h_cuts_group)
        
        # Gruppo taglio verticale
        self.v_cuts_group = QGroupBox("Punti di taglio verticali")
        v_cuts_layout = QGridLayout(self.v_cuts_group)
        
        # Importante: inizializza l'array prima di usarlo
        self.v_cut_sliders = []
        
        for i in range(4):
            slider = QSlider(Qt.Horizontal)
            slider.setRange(10, 90)
            slider.setValue(50)
            slider.setEnabled(False)
            
            label = QLabel(f"Taglio V {i+1}:")
            value_label = QLabel("50%")
            
            v_cuts_layout.addWidget(label, i, 0)
            v_cuts_layout.addWidget(slider, i, 1)
            v_cuts_layout.addWidget(value_label, i, 2)
            
            slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(f"{v}%"))
            slider.valueChanged.connect(self.updateCutPreview)
            
            self.v_cut_sliders.append((slider, value_label))
        
        mix_layout.addWidget(self.v_cuts_group)
        
        # Inizialmente nascondi i gruppi di sliders
        self.h_cuts_group.setVisible(False)
        self.v_cuts_group.setVisible(False)
        
    def updateCutPreview(self):
        """Aggiorna l'anteprima delle linee di taglio quando gli slider cambiano"""
        if not self.letters_dict:
            return  # Nessuna lettera da visualizzare
        
        # Ottieni i valori di taglio correnti
        h_cuts = self.getCustomCutPoints()
        v_cuts = self.getCustomVerticalCutPoints()
        
        # Aggiorna le linee di taglio in ogni widget lettera
        for letter, widget in self.letter_widgets.items():
            widget.setCutLines(h_cuts)
            widget.setVerticalCutLines(v_cuts)
        
    def loadAvailableFonts(self):
        """Carica i font disponibili dalla cartella 'fonts'"""
        font_dir = "fonts"
        if not os.path.exists(font_dir):
            os.makedirs(font_dir)
            
        self.available_fonts = [
            f for f in os.listdir(font_dir) 
            if f.lower().endswith((".ttf", ".otf"))
        ]
        
        if not self.available_fonts:
            QMessageBox.warning(
                self, 
                "Nessun Font Trovato", 
                "Nessun font trovato nella cartella 'fonts'.\n"
                "Aggiungi almeno due font TTF o OTF."
            )
    
    def updateUI(self):
        """Aggiorna lo stato dell'interfaccia in base alla selezione corrente"""
        num_selected = len(self.font_list.selectedItems())
        self.btn_remove_font.setEnabled(num_selected > 0)
        
        selected_row = -1
        if self.font_list.currentItem() is not None:
            selected_row = self.font_list.row(self.font_list.currentItem())
        
        self.btn_move_up.setEnabled(num_selected == 1 and selected_row > 0)
        self.btn_move_down.setEnabled(
            num_selected == 1 and 
            selected_row >= 0 and  
            selected_row < self.font_list.count() - 1
        )
        
        can_generate = self.font_list.count() >= 2
        self.btn_generate.setEnabled(can_generate)
        
        method = self.combo_cut_method.currentText()
        use_vertical = self.check_vertical_cuts.isChecked()
        num_cuts = max(0, self.font_list.count() - 1)
        
        # Aggiorna visibilità e stato degli slider orizzontali
        self.h_cuts_group.setVisible(method == "Personalizzato")
        for i, (slider, label) in enumerate(self.h_cut_sliders):
            enabled = i < num_cuts and method == "Personalizzato"
            slider.setEnabled(enabled)
            label.setEnabled(enabled)
        
        # Aggiorna visibilità e stato degli slider verticali
        self.v_cuts_group.setVisible(method == "Personalizzato" and use_vertical)
        for i, (slider, label) in enumerate(self.v_cut_sliders):
            enabled = i < num_cuts and method == "Personalizzato" and use_vertical
            slider.setEnabled(enabled)
            label.setEnabled(enabled)
    
    def onAddFont(self):
        """Gestisce l'aggiunta di un font"""
        # Mostra dialogo per selezionare un font
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Font Files (*.ttf *.otf)")
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            
            for font_path in selected_files:
                # Copia il font nella cartella fonts
                font_name = os.path.basename(font_path)
                dest_path = os.path.join("fonts", font_name)
                
                try:
                    if not os.path.exists("fonts"):
                        os.makedirs("fonts")
                    
                    if font_path != dest_path:
                        import shutil
                        shutil.copy2(font_path, dest_path)
                    
                    # Aggiungi alla lista
                    try:
                        # Prova ad aprire il font per verificare che sia valido
                        font = TTFont(dest_path)
                        font_family = "Unknown Font"
                        
                        # Tenta di ottenere il nome del font
                        if "name" in font and font["name"].names:
                            for record in font["name"].names:
                                if record.nameID == 1 and record.platformID == 3:
                                    try:
                                        font_family = record.string.decode("utf-16-be")
                                        break
                                    except:
                                        pass
                        
                        font.close()
                        
                        # Aggiungiamo alla lista con nome famiglia e percorso
                        display_name = f"{font_family} ({font_name})"
                        item = QListWidgetItem(display_name)
                        item.setData(Qt.UserRole, dest_path)
                        self.font_list.addItem(item)
                        
                    except Exception as e:
                        QMessageBox.warning(
                            self, 
                            "Font Non Valido", 
                            f"Impossibile leggere il font {font_name}.\nErrore: {str(e)}"
                        )
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                            
                except Exception as e:
                    QMessageBox.warning(
                        self, 
                        "Errore", 
                        f"Impossibile copiare il font {font_name}.\nErrore: {str(e)}"
                    )
            
            # Aggiorna l'interfaccia
            self.updateUI()
            
            # Aggiorna i punti di taglio
            self.updateCutSliders()
    
    def onRemoveFont(self):
        """Rimuove i font selezionati dalla lista"""
        selected_items = self.font_list.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            row = self.font_list.row(item)
            self.font_list.takeItem(row)
            
        self.updateUI()
        self.updateCutSliders()
    
    def onMoveUp(self):
        """Sposta il font selezionato verso l'alto"""
        current_row = self.font_list.currentRow()
        if current_row <= 0:
            return
            
        item = self.font_list.takeItem(current_row)
        self.font_list.insertItem(current_row - 1, item)
        self.font_list.setCurrentItem(item)
        
        self.updateUI()
    
    def onMoveDown(self):
        """Sposta il font selezionato verso il basso"""
        current_row = self.font_list.currentRow()
        if current_row >= self.font_list.count() - 1:
            return
            
        item = self.font_list.takeItem(current_row)
        self.font_list.insertItem(current_row + 1, item)
        self.font_list.setCurrentItem(item)
        
        self.updateUI()
    
    def onCutMethodChanged(self, index):
        """Gestisce il cambio del metodo di taglio"""
        method = self.combo_cut_method.currentText()
        use_vertical = self.check_vertical_cuts.isChecked()
        
        self.h_cuts_group.setVisible(method == "Personalizzato")
        self.v_cuts_group.setVisible(method == "Personalizzato" and use_vertical)
        
        self.updateUI()
        
        if method == "Equidistante":
            self.updateEqualCutSliders()
            
    def getCustomVerticalCutPoints(self):
        """Ottiene i punti di taglio verticali personalizzati"""
        cut_points = []
        num_cuts = self.font_list.count() - 1
        
        for i, (slider, _) in enumerate(self.v_cut_sliders):
            if i < num_cuts:
                value = slider.value() / 100.0
                cut_points.append(value)
                    
        return cut_points
        
    def updateCutSliders(self):
        """Aggiorna gli slider in base al numero di font"""
        num_cuts = max(0, self.font_list.count() - 1)
        method = self.combo_cut_method.currentText()
        
        if method == "Equidistante":
            self.updateEqualCutSliders()
        else:
            for i, (slider, label) in enumerate(self.h_cut_sliders):
                enabled = i < num_cuts and method == "Personalizzato"
                slider.setEnabled(enabled)
                label.setEnabled(enabled)
                
            for i, (slider, label) in enumerate(self.v_cut_sliders):
                enabled = i < num_cuts and method == "Personalizzato"
                slider.setEnabled(enabled)
                label.setEnabled(enabled)   
    
    def updateEqualCutSliders(self):
        """Imposta gli slider a valori equidistanti"""
        num_cuts = max(0, self.font_list.count() - 1)
        
        if num_cuts <= 0:
            return
            
        for i, (slider, label) in enumerate(self.h_cut_sliders):
            if i < num_cuts:
                value = int(100 * (i + 1) / (num_cuts + 1))
                slider.setValue(value)
                label.setText(f"{value}%")
                
        for i, (slider, label) in enumerate(self.v_cut_sliders):
            if i < num_cuts:
                value = int(100 * (i + 1) / (num_cuts + 1))
                slider.setValue(value)
                label.setText(f"{value}%")
    
    def getSelectedFontPaths(self):
        """Ottiene i percorsi dei font selezionati"""
        paths = []
        for i in range(self.font_list.count()):
            item = self.font_list.item(i)
            path = item.data(Qt.UserRole)
            paths.append(path)
        return paths
    
    def getCustomCutPoints(self):
        """Ottiene i punti di taglio personalizzati (orizzontali)"""
        cut_points = []
        num_cuts = self.font_list.count() - 1
        
        for i, (slider, _) in enumerate(self.h_cut_sliders):
            if i < num_cuts:
                value = slider.value() / 100.0
                cut_points.append(value)
                    
        return cut_points
    
    def onGenerateFont(self):
        """Gestisce la generazione del font"""
        if self.font_list.count() < 2:
            QMessageBox.warning(
                self, 
                "Font Insufficienti", 
                "Servono almeno due font per il mixaggio."
            )
            return
        
        self.btn_generate.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_status.setText("Inizializzazione...")
        
        font_paths = self.getSelectedFontPaths()
        
        cut_method = self.combo_cut_method.currentText().lower()
        h_cuts = None
        v_cuts = None
        
        # Determina i punti di taglio in base al metodo selezionato
        if cut_method == "personalizzato":
            h_cuts = self.getCustomCutPoints()
            if self.check_vertical_cuts.isChecked():
                v_cuts = self.getCustomVerticalCutPoints()
        elif cut_method == "equidistante":
            num_cuts = self.font_list.count() - 1
            h_cuts = [(i + 1) / (num_cuts + 1) for i in range(num_cuts)]
            
            if self.check_vertical_cuts.isChecked():
                v_cuts = h_cuts.copy()
        else:  # casuale
            num_cuts = self.font_list.count() - 1
            h_cuts = [random.uniform(0.2, 0.8) for _ in range(num_cuts)]
            h_cuts.sort()  # Ordinati per chiarezza
            
            if self.check_vertical_cuts.isChecked():
                v_cuts = [random.uniform(0.2, 0.8) for _ in range(num_cuts)]
                v_cuts.sort()
        
        use_vertical_cuts = self.check_vertical_cuts.isChecked()
        normalize = self.check_normalize.isChecked()
        
        font_name = self.font_name_edit.text().strip()
        if not font_name:
            font_name = "MixedFont"
            
        # Crea il thread di generazione
        self.generator_thread = FontGeneratorThread(
            font_paths, 
            cut_method, 
            h_cuts, 
            v_cuts,
            normalize,
            use_vertical_cuts,  
            font_name
        )
        
        self.generator_thread.update_progress.connect(self.updateProgress)
        self.generator_thread.generation_complete.connect(self.onGenerationComplete)
        
        self.generator_thread.start()
    
    def updateProgress(self, value, status):
        """Aggiorna la barra di progresso"""
        self.progress_bar.setValue(value)
        self.progress_status.setText(status)
    
    def onGenerationComplete(self, success, message, letters_dict):
        """Gestisce il completamento della generazione"""
        self.btn_generate.setEnabled(True)
        
        if not success:
            QMessageBox.warning(self, "Errore", f"Generazione fallita:\n{message}")
            return
        
        try:
            if isinstance(message, str) and os.path.exists(message) and letters_dict:
                self.letters_dict = letters_dict
                self.output_font_path = message  
                
                print(f"Font generato: {self.output_font_path}")
                print(f"Lettere generate: {len(self.letters_dict)}")
                
                try:
                    print("Aggiornamento anteprime...")
                    self.updateLetterPreviews()
                    self.alphabet_preview.setLetters(letters_dict)
                    print("Anteprima aggiornata")
                except Exception as e:
                    print(f"Errore nell'aggiornamento delle anteprime: {str(e)}")
                    traceback.print_exc()
                
                self.btn_export.setEnabled(True)
                self.btn_load_in_system.setEnabled(True)
                self.btn_test_text.setEnabled(True)
                
                print("Passaggio alla tab di anteprima")
                self.tabs.setCurrentIndex(1)
                
                QMessageBox.information(
                    self, 
                    "Font Generato", 
                    f"Font generato con successo!\nSalvato in: {self.output_font_path}"
                )
            else:
                err_message = "Il file generato non è stato trovato o non contiene dati validi.\n"
                if not isinstance(message, str) or not os.path.exists(message):
                    err_message += f"File non trovato: {message}\n"
                if not letters_dict:
                    err_message += "Nessun contorno di lettere generato.\n"
                    
                QMessageBox.warning(self, "Errore di generazione", err_message)
        except Exception as e:
            QMessageBox.warning(
                self, 
                "Errore nella gestione del completamento",
                f"Si è verificato un errore dopo la generazione:\n{str(e)}"
            )
            traceback.print_exc()
    
    def updateLetterPreviews(self):
        """Aggiorna tutte le anteprime delle lettere"""
        if not self.letters_dict:
            return
            
        try:
            h_cuts = []
            v_cuts = []
            method = self.combo_cut_method.currentText()
            num_cuts = self.font_list.count() - 1
            
            if method == "Personalizzato":
                h_cuts = self.getCustomCutPoints()
                if self.check_vertical_cuts.isChecked():
                    v_cuts = self.getCustomVerticalCutPoints()
            elif method == "Equidistante":
                h_cuts = [(i + 1) / (num_cuts + 1) for i in range(num_cuts)]
                if self.check_vertical_cuts.isChecked():
                    v_cuts = h_cuts.copy()
            
            print(f"Aggiornamento anteprime con h_cuts={h_cuts}, v_cuts={v_cuts}")
            
            for letter, contours in self.letters_dict.items():
                if letter in self.letter_widgets:
                    self.letter_widgets[letter].setContours(contours)
                    self.letter_widgets[letter].setCutLines(h_cuts)
                    self.letter_widgets[letter].setVerticalCutLines(v_cuts)
        except Exception as e:
            print(f"Errore in updateLetterPreviews: {e}")
            traceback.print_exc()
    
    def onExportFont(self):
        """Esporta il font generato"""
        if not self.output_font_path or not os.path.exists(self.output_font_path):
            QMessageBox.warning(
                self, 
                "Font Non Disponibile", 
                "Il font non è stato generato o non è più disponibile."
            )
            return
            
        # Dialogo salvataggio
        file_dialog = QFileDialog()
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setNameFilter("Font Files (*.ttf)")
        file_dialog.setDefaultSuffix("ttf")
        
        font_name = os.path.basename(self.output_font_path)
        file_dialog.selectFile(font_name)
        
        if file_dialog.exec_():
            selected_path = file_dialog.selectedFiles()[0]
            
            try:
                import shutil
                shutil.copy2(self.output_font_path, selected_path)
                
                QMessageBox.information(
                    self, 
                    "Esportazione Riuscita", 
                    f"Font esportato con successo in:\n{selected_path}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self, 
                    "Errore di Esportazione", 
                    f"Impossibile esportare il font:\n{str(e)}"
                )
    
    def onLoadInSystem(self):
        """Carica il font nel sistema per l'anteprima"""
        if not self.output_font_path or not os.path.exists(self.output_font_path):
            QMessageBox.warning(
                self, 
                "Font Non Disponibile", 
                "Il font non è stato generato o non è più disponibile."
            )
            return
            
        # Tenta di caricare il font in QFontDatabase
        font_id = QFontDatabase.addApplicationFont(self.output_font_path)
        
        if font_id == -1:
            QMessageBox.warning(
                self, 
                "Caricamento Fallito", 
                "Impossibile caricare il font nel sistema.\n"
                "Il file potrebbe essere danneggiato."
            )
            return
            
        # Ottieni famiglia font
        families = QFontDatabase.applicationFontFamilies(font_id)
        if not families:
            QMessageBox.warning(
                self, 
                "Nessuna Famiglia Font", 
                "Il font è stato caricato ma non sono state trovate famiglie."
            )
            return
            
        # Mostra anteprima
        family = families[0]
        preview_font = QFont(family, 18)
        
        self.preview_label.setFont(preview_font)
        self.preview_label.setText("ABCDEFG\nabcdefg")
        
        QMessageBox.information(
            self, 
            "Font Caricato", 
            f"Font '{family}' caricato con successo nel sistema.\n"
            "È ora disponibile per l'uso in questa sessione dell'applicazione."
        )
    
    def onOpenTextEditor(self):
        """Apre un editor di testo per testare il font"""
        if not self.output_font_path or not os.path.exists(self.output_font_path):
            QMessageBox.warning(
                self, 
                "Font Non Disponibile", 
                "Il font non è stato generato o non è più disponibile."
            )
            return
            
        # Carichiamo il font se non è già stato caricato
        font_id = QFontDatabase.addApplicationFont(self.output_font_path)
        
        families = []
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
        
        if not families:
            QMessageBox.warning(
                self, 
                "Caricamento Fallito", 
                "Impossibile caricare il font per l'anteprima."
            )
            return
            
        family = families[0]
        
        # Crea finestra editor
        editor = QDialog(self)
        editor.setWindowTitle(f"Test Font - {family}")
        editor.resize(600, 400)
        
        layout = QVBoxLayout(editor)
        
        text_edit = QTextEdit()
        text_edit.setFontFamily(family)
        text_edit.setFontPointSize(16)
        text_edit.setText("ABCDEFGHIJKLMNOPQRSTUVWXYZ\nabcdefghijklmnopqrstuvwxyz\n1234567890")
        
        layout.addWidget(text_edit)
        
        editor.exec_()