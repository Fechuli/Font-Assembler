# Requisiti per Font Mixer

## Librerie necessarie
Per eseguire l'applicazione Font Mixer sono necessarie le seguenti librerie Python:

1. **PyQt5**: Per l'interfaccia grafica
   ```
   pip install PyQt5
   ```

2. **FontTools**: Per la manipolazione dei font
   ```
   pip install fonttools
   ```

3. **Shapely**: Per le operazioni geometriche sui contorni
   ```
   pip install shapely
   ```

## Struttura delle cartelle
L'applicazione richiede la seguente struttura di cartelle:

- `fonts/`: Cartella dove inserire i font TTF/OTF da mixare
- `output/`: Cartella dove verranno salvati i font generati

L'applicazione creerà automaticamente queste cartelle se non esistono.

## Compatibilità
- L'applicazione funziona con font TrueType (.ttf) e OpenType (.otf)
- Testato su Windows, macOS e Linux con Python 3.6+
- Per migliori risultati, utilizzare font con glifi semplici e non compositi

## Setup rapido
1. Installare le dipendenze
   ```
   pip install PyQt5 fonttools shapely
   ```
2. Inserire almeno due font nella cartella `fonts/`
3. Eseguire l'applicazione
   ```
   python font_mixer.py
   ```

## Note
- Per una corretta visualizzazione del font generato, è necessario che il sistema supporti il caricamento dinamico dei font
- Se il font generato presenta errori, provare con font di input diversi o con impostazioni di taglio differenti