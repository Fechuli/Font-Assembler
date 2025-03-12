# Font Mixer

Un'applicazione per creare font ibridi miscelando due o più font esistenti.

## Caratteristiche

- Miscelazione di font sia in orizzontale che in verticale
- Anteprima delle lettere generate
- Esportazione in formato TTF
- Diversi metodi di miscelazione (casuale, equidistante, personalizzato)
- Supporto per font TrueType e OpenType

## Requisiti

- Python 3.6+
- PyQt5
- fontTools
- shapely

## Installazione

1. Clona o scarica questo repository
2. Installa le dipendenze:

```bash
pip install -r requirements.txt
```

## Utilizzo

1. Avvia l'applicazione:

```bash
python main.py
```

2. Aggiungi almeno due font dalla finestra "Generatore"
3. Configura le opzioni di mixaggio
4. Clicca su "GENERA FONT"
5. Visualizza e testa il font nella scheda "Anteprima"
6. Esporta il font o caricalo nel sistema per utilizzarlo

## Struttura dei file

- `geometry_utils.py`: Operazioni geometriche sui poligoni
- `font_utils.py`: Funzioni per elaborazione dei font
- `glyph_processing.py`: Algoritmi di mixaggio dei glifi
- `font_assembly.py`: Creazione e assemblaggio del font TTF
- `visualization.py`: Widget per visualizzazione dei glifi
- `generator.py`: Thread per generazione asincrona
- `gui.py`: Interfaccia grafica principale
- `main.py`: Entry point dell'applicazione

## Cartelle

- `fonts/`: Cartella dove vengono copiati i font da usare come base
- `output/`: Cartella dove vengono salvati i font generati

## Personalizzazione

### Metodi di mixaggio

- **Casuale**: Taglia ogni lettera in punti casuali
- **Equidistante**: Divide i font in sezioni uguali 
- **Personalizzato**: Permette di configurare manualmente i punti di taglio

### Tagli verticali

Attivando l'opzione "Tagli verticali" si ottiene una griglia invece di semplici tagli orizzontali,
permettendo una miscela più complessa dei font di origine.

## Licenza

Questo progetto è distribuito con licenza MIT.