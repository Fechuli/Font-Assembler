import sys
import os
import random
from string import ascii_uppercase
import traceback

# PyQt5 per la GUI
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, 
    QWidget, QComboBox, QListWidget, QSlider, QTabWidget,
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QScrollArea,
    QGridLayout, QSizePolicy, QLineEdit, QListWidgetItem
)
from PyQt5.QtGui import QFontDatabase, QFont, QPainter, QColor, QPen, QImage, QPainterPath
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRectF, QPointF

# FontTools
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables.O_S_2f_2 import Panose
from fontTools.ttLib.tables._n_a_m_e import NameRecord
from fontTools.ttLib.tables._c_m_a_p import cmap_format_4
from fontTools.pens.ttGlyphPen import TTGlyphPen

# Shapely
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

# ------------------------------------------------------------------------
# FUNZIONI GEOMETRICHE (Shapely)
# ------------------------------------------------------------------------

def polygon_from_contour(contour):
    if not contour:
        return None
    # Chiudiamo il contorno se non è chiuso
    if contour[0] != contour[-1]:
        contour = contour + [contour[0]]
    try:
        poly = Polygon(contour)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return poly
    except Exception as e:
        print(f"Errore nella creazione del poligono: {str(e)}")
        return None

def polygon_to_contours(poly):
    if not poly or poly.is_empty:
        return []
    if isinstance(poly, MultiPolygon):
        all_contours = []
        for p in poly.geoms:
            all_contours.extend(polygon_to_contours(p))
        return all_contours
    
    contours = []
    try:
        # Exterior
        contours.append(list(poly.exterior.coords))
        # Interiors (buchi)
        for interior in poly.interiors:
            contours.append(list(interior.coords))
    except Exception as e:
        print(f"Errore nell'estrazione dei contorni: {str(e)}")
    return contours

def cut_polygon_at_y(poly, y_cut):
    if not poly or poly.is_empty:
        return None, None
    if isinstance(poly, MultiPolygon):
        poly = poly.buffer(0)

    try:
        minx, miny, maxx, maxy = poly.bounds
        safe_margin = 20000  # Ampliamo per sicurezza
        
        top_rect = Polygon([
            (minx - safe_margin, y_cut),
            (maxx + safe_margin, y_cut),
            (maxx + safe_margin, maxy + safe_margin),
            (minx - safe_margin, maxy + safe_margin)
        ])
        
        bottom_rect = Polygon([
            (minx - safe_margin, miny - safe_margin),
            (maxx + safe_margin, miny - safe_margin),
            (maxx + safe_margin, y_cut),
            (minx - safe_margin, y_cut)
        ])
        
        top_part = poly.intersection(top_rect)
        bottom_part = poly.intersection(bottom_rect)
        
        # Validazione
        if top_part and not top_part.is_empty:
            top_part = top_part.buffer(0)
        if bottom_part and not bottom_part.is_empty:
            bottom_part = bottom_part.buffer(0)
            
        return top_part, bottom_part
    except Exception as e:
        print(f"Errore nel taglio del poligono: {str(e)}")
        return None, None

def mix_multiple_polygons(polygons, cut_points):
    """
    Mixa più poligoni usando più punti di taglio.
    
    Args:
        polygons: lista di poligoni (uno per font)
        cut_points: lista di punti y di taglio (N-1 punti per N poligoni)
    
    Returns:
        Un poligono assemblato con parti da ciascun poligono
    """
    if not polygons or len(polygons) < 2:
        return polygons[0] if polygons else None
    
    if len(cut_points) != len(polygons) - 1:
        print("Errore: il numero di punti di taglio deve essere fonts - 1")
        return None
    
    # Iniziamo con l'ultimo poligono e risaliamo
    result = polygons[-1]
    
    # Per ogni punto di taglio, partendo dall'ultimo
    for i in range(len(cut_points) - 1, -1, -1):
        # Tagliamo il risultato corrente al punto di taglio i
        _, bottom_result = cut_polygon_at_y(result, cut_points[i])
        
        # Tagliamo il poligono i al punto di taglio i
        top_poly_i, _ = cut_polygon_at_y(polygons[i], cut_points[i])
        
        # Uniamo la parte superiore del poligono i con la parte inferiore del risultato
        parts = []
        if top_poly_i and not top_poly_i.is_empty:
            parts.append(top_poly_i)
        if bottom_result and not bottom_result.is_empty:
            parts.append(bottom_result)
        
        result = unary_union([p for p in parts if p])
    
    return result

# ------------------------------------------------------------------------
# LETTURA CONTORNI DI UN GLIFO (TrueType)
# ------------------------------------------------------------------------

def get_glyph_contours(font: TTFont, glyph_name: str):
    """
    Estrae i contorni di un glifo da un font TTF o OTF.
    Gestisce in modo migliore i font OpenType.
    
    Args:
        font: oggetto TTFont
        glyph_name: nome del glifo (es. "A")
        
    Returns:
        Lista di contorni, dove ogni contorno è una lista di tuple (x, y)
    """
    try:
        # Verifica se è un font CFF (OpenType)
        is_cff = "CFF " in font or "CFF" in font
        
        if is_cff:
            return get_cff_glyph_contours(font, glyph_name)
        elif "glyf" in font:
            return get_ttf_glyph_contours(font, glyph_name)
        else:
            print(f"Tipo di font non supportato: {list(font.keys())}")
            return []
            
    except Exception as e:
        print(f"Errore nella lettura dei contorni: {str(e)}")
        traceback.print_exc()
        return []
        
def get_ttf_glyph_contours(font: TTFont, glyph_name: str):
    """Estrae i contorni di un glifo da un font TrueType."""
    try:
        glyf_table = font["glyf"]
        if glyph_name not in glyf_table:
            print(f"TTF: Glifo '{glyph_name}' non trovato nel font")
            return []
            
        glyph = glyf_table[glyph_name]
        if glyph.isComposite():
            print(f"TTF: Glifo composito non supportato: {glyph_name}")
            return []
        
        coords = glyph.coordinates
        end_pts = glyph.endPtsOfContours
        
        contours = []
        start = 0
        for end in end_pts:
            c = []
            for i in range(start, end + 1):
                x, y = coords[i]
                c.append((x, y))
            contours.append(c)
            start = end + 1
            
        return contours
    except Exception as e:
        print(f"Errore nell'estrazione contorni TTF: {str(e)}")
        traceback.print_exc()
        return []

def get_cff_glyph_contours(font: TTFont, glyph_name: str):
    """Estrae i contorni di un glifo da un font OpenType (CFF)."""
    try:
        from fontTools.pens.recordingPen import RecordingPen
        
        # Usa CFF o CFF2 a seconda di quale è presente
        cff_table_tag = "CFF " if "CFF " in font else "CFF"
        cff_table = font[cff_table_tag]
        
        # Ottieni il T2CharString per il glifo
        cff_topDict = cff_table.cff.topDictIndex[0]
        char_strings = cff_topDict.CharStrings
        
        if glyph_name not in char_strings:
            print(f"CFF: Glifo '{glyph_name}' non trovato nel font")
            return []
        
        # Usa RecordingPen per registrare le operazioni di disegno
        pen = RecordingPen()
        char_strings[glyph_name].draw(pen)
        
        # Estrai i contorni dal pen
        contours = []
        current_contour = None
        
        for operator, operands in pen.value:
            if operator == "moveTo":
                if current_contour is not None and current_contour:
                    contours.append(current_contour)
                current_contour = [operands[0]]
            elif operator == "lineTo":
                if current_contour is not None:
                    current_contour.append(operands[0])
            elif operator == "curveTo":
                # Converti la curva Bézier cubica in segmenti lineari (semplificazione)
                if current_contour is not None:
                    # Aggiungi punti intermedi per approssimare la curva
                    p0 = current_contour[-1]
                    p1, p2, p3 = operands
                    
                    # Aggiungi 5 punti per approssimare la curva
                    for t in [0.2, 0.4, 0.6, 0.8, 1.0]:
                        # Formula per Bézier cubico
                        x = (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
                        y = (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
                        current_contour.append((x, y))
            elif operator == "qCurveTo":
                # Converti la curva Bézier quadratica in segmenti lineari (semplificazione)
                if current_contour is not None and len(operands) >= 2:
                    p0 = current_contour[-1]
                    control_points = operands[:-1]
                    p2 = operands[-1]
                    
                    for control_point in control_points:
                        # Aggiungi 3 punti per approssimare la curva
                        for t in [0.33, 0.66, 1.0]:
                            # Formula per Bézier quadratico
                            x = (1-t)**2 * p0[0] + 2*(1-t)*t * control_point[0] + t**2 * p2[0]
                            y = (1-t)**2 * p0[1] + 2*(1-t)*t * control_point[1] + t**2 * p2[1]
                            current_contour.append((x, y))
                        p0 = p2
            elif operator == "closePath":
                if current_contour is not None and current_contour:
                    # Chiudi il contorno
                    if current_contour[0] != current_contour[-1]:
                        current_contour.append(current_contour[0])
                    contours.append(current_contour)
                    current_contour = None
        
        # Aggiungi l'ultimo contorno se necessario
        if current_contour is not None and current_contour:
            contours.append(current_contour)
        
        # Debug
        print(f"CFF: Estratti {len(contours)} contorni per il glifo '{glyph_name}'")
        for i, c in enumerate(contours):
            print(f"  Contorno {i}: {len(c)} punti")
            
        return contours
    except Exception as e:
        print(f"Errore nell'estrazione contorni CFF: {str(e)}")
        traceback.print_exc()
        return []

def normalize_glyph_contours(contours, target_height=1000):
    """Normalizza i contorni per adattarli a un'altezza target"""
    if not contours:
        return []
    
    # Trova min/max per normalizzare
    all_points = [pt for c in contours for pt in c]
    min_x = min(p[0] for p in all_points)
    max_x = max(p[0] for p in all_points)
    min_y = min(p[1] for p in all_points)
    max_y = max(p[1] for p in all_points)
    
    height = max_y - min_y
    if height == 0:
        return contours  # Evita divisione per zero
    
    scale = target_height / height
    
    normalized = []
    for contour in contours:
        new_contour = []
        for x, y in contour:
            new_x = (x - min_x) * scale
            new_y = (y - min_y) * scale
            new_contour.append((new_x, new_y))
        normalized.append(new_contour)
    
    return normalized

def glyph_to_image(contours, width=200, height=200, padding=10):
    """Converte i contorni di un glifo in un'immagine QImage per l'anteprima"""
    if not contours:
        return QImage(width, height, QImage.Format_ARGB32)
    
    # Trova i limiti
    all_points = [pt for c in contours for pt in c]
    min_x = min(p[0] for p in all_points)
    max_x = max(p[0] for p in all_points)
    min_y = min(p[1] for p in all_points)
    max_y = max(p[1] for p in all_points)
    
    glyph_width = max_x - min_x
    glyph_height = max_y - min_y
    
    # Crea l'immagine
    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # Determina il fattore di scala per adattare il glifo allo spazio disponibile
    available_width = width - 2 * padding
    available_height = height - 2 * padding
    scale_x = available_width / glyph_width if glyph_width > 0 else 1
    scale_y = available_height / glyph_height if glyph_height > 0 else 1
    scale = min(scale_x, scale_y)
    
    # Imposta la trasformazione per centrare e scalare il glifo
    painter.translate(width / 2, height / 2)
    painter.scale(scale, -scale)  # Y negativo perché in font Y cresce verso l'alto
    painter.translate(-((min_x + max_x) / 2), -((min_y + max_y) / 2))
    
    # Disegna i contorni
    painter.setPen(QPen(Qt.black, 1/scale))
    painter.setBrush(QColor(0, 0, 0, 128))
    
    for contour in contours:
        if len(contour) < 3:
            continue
            
        path = painter.path()
        path.moveTo(contour[0][0], contour[0][1])
        for x, y in contour[1:]:
            path.lineTo(x, y)
        path.closeSubpath()
        painter.drawPath(path)
    
    painter.end()
    return image

# ------------------------------------------------------------------------
# ASSEMBLAGGIO LETTERA (multiple fonts)
# ------------------------------------------------------------------------

def assemble_letter_multiple_fonts(font_paths, glyph_name, cut_points):
    """
    Assembla un glifo da più font con più punti di taglio.
    
    Args:
        font_paths: lista di percorsi ai font
        glyph_name: nome del glifo da assemblare (es. "A")
        cut_points: punti y di taglio (N-1 punti per N font)
    
    Returns:
        Il poligono assemblato
    """
    polygons = []
    
    # Leggiamo i contorni da ogni font
    for font_path in font_paths:
        try:
            font = TTFont(font_path)
            contours = get_glyph_contours(font, glyph_name)
            font.close()
            
            # Convertiamo in poligono
            poly = unary_union([polygon_from_contour(c) for c in contours if c])
            polygons.append(poly if poly else None)
        except Exception as e:
            print(f"Errore nel leggere font {font_path}: {str(e)}")
            polygons.append(None)
    
    # Filtriamo i poligoni nulli
    valid_polygons = [p for p in polygons if p and not p.is_empty]
    if not valid_polygons:
        return None
    
    # Normalizzazione dei punti di taglio (0-1000)
    normalized_cut_points = [cp * 1000 for cp in cut_points]
    
    # Mixiamo i poligoni
    return mix_multiple_polygons(valid_polygons, normalized_cut_points)

def contours_to_glyph(contours):
    pen = TTGlyphPen(None)
    for c in contours:
        if not c or len(c) < 3:
            continue
        pen.moveTo(c[0])
        for pt in c[1:]:
            pen.lineTo(pt)
        pen.closePath()
    return pen.glyph()

# ------------------------------------------------------------------------
# CREAZIONE FONT CON TUTTE LE LETTERE (A-Z)
# ------------------------------------------------------------------------

def create_alphabet_font(letters_dict, output_path, font_name="MixedFont"):
    """
    Crea un font TTF con le lettere specificate.
    
    Args:
        letters_dict: { 'A': [contorni], 'B': [contorni], ... }
        output_path: percorso dove salvare il file TTF
        font_name: nome del font
    """
    try:
        new_font = TTFont()
        
        # =============== HEAD
        new_font["head"] = newTable("head")
        head_table = new_font["head"]
        head_table.tableVersion = 1.0
        head_table.fontRevision = 1.0
        head_table.checkSumAdjustment = 0
        head_table.magicNumber = 0x5F0F3CF5
        head_table.flags = 0x000B
        head_table.unitsPerEm = 1000
        head_table.created = 0
        head_table.modified = 0
        head_table.xMin = 0
        head_table.yMin = 0
        head_table.xMax = 0
        head_table.yMax = 0
        head_table.macStyle = 0
        head_table.lowestRecPPEM = 8
        head_table.fontDirectionHint = 2
        head_table.indexToLocFormat = 0
        head_table.glyphDataFormat = 0
        
        # =============== HHEA
        new_font["hhea"] = newTable("hhea")
        hhea_table = new_font["hhea"]
        hhea_table.tableVersion = 0x00010000
        hhea_table.ascent = 800
        hhea_table.descent = -200
        hhea_table.lineGap = 0
        hhea_table.advanceWidthMax = 1000
        hhea_table.minLeftSideBearing = 0
        hhea_table.minRightSideBearing = 0
        hhea_table.xMaxExtent = 1000
        hhea_table.caretSlopeRise = 1
        hhea_table.caretSlopeRun = 0
        hhea_table.caretOffset = 0
        hhea_table.reserved0 = 0
        hhea_table.reserved1 = 0
        hhea_table.reserved2 = 0
        hhea_table.reserved3 = 0
        hhea_table.metricDataFormat = 0
        hhea_table.numberOfHMetrics = len(letters_dict) + 1  # .notdef + lettere
        
        # =============== MAXP
        new_font["maxp"] = newTable("maxp")
        maxp_table = new_font["maxp"]
        maxp_table.tableVersion = 0x00010000
        maxp_table.numGlyphs = len(letters_dict) + 1
        maxp_table.maxPoints = 0
        maxp_table.maxContours = 0
        maxp_table.maxCompositePoints = 0
        maxp_table.maxCompositeContours = 0
        maxp_table.maxZones = 2
        maxp_table.maxTwilightPoints = 0
        maxp_table.maxStorage = 0
        maxp_table.maxFunctionDefs = 0
        maxp_table.maxInstructionDefs = 0
        maxp_table.maxStackElements = 0
        maxp_table.maxSizeOfInstructions = 0
        maxp_table.maxComponentElements = 0
        maxp_table.maxComponentDepth = 0
        
        # =============== OS/2
        new_font["OS/2"] = newTable("OS/2")
        os2_table = new_font["OS/2"]
        os2_table.version = 4
        os2_table.xAvgCharWidth = 500
        os2_table.usWeightClass = 400
        os2_table.usWidthClass = 5
        os2_table.fsType = 0
        os2_table.ySubscriptXSize = 650
        os2_table.ySubscriptYSize = 600
        os2_table.ySubscriptXOffset = 0
        os2_table.ySubscriptYOffset = 75
        os2_table.ySuperscriptXSize = 650
        os2_table.ySuperscriptYSize = 600
        os2_table.ySuperscriptXOffset = 0
        os2_table.ySuperscriptYOffset = 350
        os2_table.yStrikeoutSize = 50
        os2_table.yStrikeoutPosition = 250
        os2_table.sFamilyClass = 0
        
        p = Panose()
        p.bFamilyType = 2
        p.bSerifStyle = 0
        p.bWeight = 5
        p.bProportion = 0
        p.bContrast = 0
        p.bStrokeVariation = 0
        p.bArmStyle = 0
        p.bLetterform = 0
        p.bMidline = 0
        p.bXHeight = 0
        os2_table.panose = p
        
        os2_table.ulUnicodeRange1 = 1  # Basic Latin
        os2_table.ulUnicodeRange2 = 0
        os2_table.ulUnicodeRange3 = 0
        os2_table.ulUnicodeRange4 = 0
        os2_table.achVendID = "PYFT"
        os2_table.fsSelection = 64
        os2_table.usFirstCharIndex = 0x0041  # 'A'
        os2_table.usLastCharIndex = 0x005A   # 'Z'
        os2_table.sTypoAscender = 800
        os2_table.sTypoDescender = -200
        os2_table.sTypoLineGap = 200
        os2_table.usWinAscent = 1000
        os2_table.usWinDescent = 200
        os2_table.ulCodePageRange1 = 1  # Latin 1
        os2_table.ulCodePageRange2 = 0
        os2_table.sxHeight = 500
        os2_table.sCapHeight = 700
        os2_table.usDefaultChar = 0
        os2_table.usBreakChar = 32
        os2_table.usMaxContext = 1
        
        # =============== CMAP
        new_font["cmap"] = newTable("cmap")
        new_font["cmap"].tableVersion = 0
        new_font["cmap"].tables = []
        subtable = cmap_format_4(4)
        subtable.platformID = 3
        subtable.platEncID = 1
        subtable.language = 0
        
        cmap_dict = {}
        for letter in letters_dict:
            # A->0x0041, B->0x0042, ...
            codepoint = ord(letter)
            cmap_dict[codepoint] = letter
        subtable.cmap = cmap_dict
        new_font["cmap"].tables.append(subtable)
        
        # =============== GLYF
        new_font["glyf"] = newTable("glyf")
        
        # =============== HMTX
        new_font["hmtx"] = newTable("hmtx")
        new_font["hmtx"].metrics = {}
        
        # =============== ORDINE DEI GLIFI
        glyph_order = [".notdef"] + list(letters_dict.keys())
        new_font.setGlyphOrder(glyph_order)
        
        # =============== .notdef - VERSIONE CORRETTA
        pen = TTGlyphPen(None)
        # Rettangolo esterno
        pen.moveTo((0, 0))
        pen.lineTo((600, 0)) 
        pen.lineTo((600, 700))
        pen.lineTo((0, 700))
        pen.closePath()
        
        # Rettangolo interno
        pen.moveTo((100, 100))
        pen.lineTo((500, 100))
        pen.lineTo((500, 600))
        pen.lineTo((100, 600))
        pen.closePath()
        
        notdef_glyph = pen.glyph()
        
        setattr(new_font["glyf"], "glyphs", {})
        new_font["glyf"].glyphOrder = glyph_order
        new_font["glyf"].glyphs[".notdef"] = notdef_glyph
        new_font["hmtx"].metrics[".notdef"] = (600, 0)
        
        # =============== LETTERE
        for letter, contours in letters_dict.items():
            if not contours:
                # Glifo invisibile
                g = TTGlyphPen(None).glyph()
                new_font["hmtx"].metrics[letter] = (500, 0)
            else:
                g = contours_to_glyph(contours)
                # Calcoliamo l'advance width basato sul contorno
                max_x = 0
                for c in contours:
                    if c:
                        max_x = max(max_x, max(x for x, y in c))
                advance = max(500, int(max_x) + 100)  # Min 500, o max_x + margine
                new_font["hmtx"].metrics[letter] = (advance, 0)
                
            new_font["glyf"].glyphs[letter] = g
        
        # =============== NAME
        new_font["name"] = newTable("name")
        new_font["name"].names = []
        
        def _makeName(nameString, nameID, platformID=3, platEncID=1, langID=0x409):
            nr = NameRecord()
            nr.nameID = nameID
            nr.platformID = platformID
            nr.platEncID = platEncID
            nr.langID = langID
            nr.string = nameString.encode('utf-16-be')
            return nr
        
        new_font["name"].names.append(_makeName(font_name, 1))  # Font Family
        new_font["name"].names.append(_makeName("Regular", 2))  # Font Subfamily
        new_font["name"].names.append(_makeName(f"{font_name} Regular", 3))  # Unique ID
        new_font["name"].names.append(_makeName(font_name, 4))  # Full font name
        new_font["name"].names.append(_makeName("Version 1.000", 5))  # Version
        new_font["name"].names.append(_makeName(f"{font_name}-Regular", 6))  # PostScript name
        
        # =============== POST
        new_font["post"] = newTable("post")
        post_table = new_font["post"]
        post_table.formatType = 3.0
        post_table.italicAngle = 0
        post_table.underlinePosition = -100
        post_table.underlineThickness = 50
        post_table.isFixedPitch = 0
        post_table.minMemType42 = 0
        post_table.maxMemType42 = 0
        post_table.minMemType1 = 0
        post_table.maxMemType1 = 0
        
        # =============== loca (necessaria per TrueType)
        new_font["loca"] = newTable("loca")
        
        # =============== RICALCOLA BOUNDING BOX DI OGNI GLIFO
        for gname in new_font.getGlyphOrder():
            g = new_font["glyf"][gname]
            if g is not None:
                g.recalcBounds(None)
        
        # =============== AGGIORNA head.xMin, xMax, yMin, yMax
        all_xmin = []
        all_xmax = []
        all_ymin = []
        all_ymax = []
        
        for gname in new_font.getGlyphOrder():
            g = new_font["glyf"][gname]
            if g is not None and hasattr(g, "xMin"):
                all_xmin.append(g.xMin if g.xMin is not None else 0)
                all_xmax.append(g.xMax if g.xMax is not None else 0)
                all_ymin.append(g.yMin if g.yMin is not None else 0)
                all_ymax.append(g.yMax if g.yMax is not None else 0)
        
        head_table.xMin = min(all_xmin) if all_xmin else 0
        head_table.xMax = max(all_xmax) if all_xmax else 0
        head_table.yMin = min(all_ymin) if all_ymin else 0
        head_table.yMax = max(all_ymax) if all_ymax else 0
        
        # =============== SALVA IL FONT CON GESTIONE DEGLI ERRORI
        import time
        
        # Assicuriamoci che la cartella esista
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Prova a salvare con diversi tentativi
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    # Se non è il primo tentativo, modifichiamo il nome del file
                    name_parts = os.path.splitext(output_path)
                    new_path = f"{name_parts[0]}_{attempt+1}{name_parts[1]}"
                    print(f"Tentativo {attempt+1}: Salvataggio come {new_path}")
                    new_font.save(new_path)
                    print(f"Font salvato in '{new_path}'")
                    return True, new_path
                else:
                    new_font.save(output_path)
                    print(f"Font salvato in '{output_path}'")
                    return True, output_path
                    
            except PermissionError as e:
                print(f"Tentativo {attempt+1} fallito: {str(e)}")
                # Attendi un po' prima di riprovare
                time.sleep(0.5)
                
                # Se questo è l'ultimo tentativo, solleva l'errore
                if attempt == max_attempts - 1:
                    raise
        
        return True, output_path
        
    except Exception as e:
        print(f"Errore nella creazione del font: {str(e)}")
        traceback.print_exc()
        return False, str(e)

# ------------------------------------------------------------------------
# GENERATORE (Thread separato)
# ------------------------------------------------------------------------

class FontGeneratorThread(QThread):
    update_progress = pyqtSignal(int, str)
    generation_complete = pyqtSignal(bool, str, dict)
    
    def __init__(self, font_paths, cut_method, y_cuts=None, font_name="MixedFont"):
        super().__init__()
        self.font_paths = font_paths
        self.cut_method = cut_method  
        self.y_cuts = y_cuts  
        self.font_name = font_name
        self.letters_dict = {}
        self.output_path = "output/MixedFont.ttf"
    
    def run(self):
        try:
            print("Thread avviato - inizializzazione...")
            
            num_fonts = len(self.font_paths)
            if num_fonts < 2:
                self.generation_complete.emit(False, "Servono almeno 2 font", {})
                return
                
            self.update_progress.emit(5, "Inizializzazione...")
            
            self.letters_dict = {}
            letters = list(ascii_uppercase)
            
            for i, letter in enumerate(letters):
                progress = 5 + int(85 * (i / len(letters)))
                self.update_progress.emit(progress, f"Elaborazione lettera {letter}...")
                
                if self.cut_method == "random":
                    cuts = [random.uniform(0.2, 0.8) for _ in range(num_fonts - 1)]
                    cuts.sort()  
                elif self.cut_method == "equal":
                    cuts = [float(i+1)/num_fonts for i in range(num_fonts - 1)]
                else:  
                    cuts = self.y_cuts[:num_fonts-1] if self.y_cuts else [0.5] * (num_fonts - 1)
                
                poly = assemble_letter_multiple_fonts(self.font_paths, letter, cuts)
                
                if poly and not poly.is_empty:
                    final_contours = polygon_to_contours(poly)
                    self.letters_dict[letter] = final_contours
                else:
                    self.letters_dict[letter] = []
            
            self.update_progress.emit(90, "Creazione del font...")
            
            import time
            timestamp = int(time.time())
            os.makedirs("output", exist_ok=True)
            
            self.output_path = os.path.join("output", f"{self.font_name}.ttf")
            
            alt_output_path = os.path.join("output", f"{self.font_name}_{timestamp}.ttf")
            
            success, result = create_alphabet_font(self.letters_dict, self.output_path, self.font_name)
            
            if success and isinstance(result, str) and os.path.exists(result):
                self.output_path = result
                
            self.update_progress.emit(100, "Completato!")
            
            if success:
                self.generation_complete.emit(True, self.output_path, self.letters_dict)
            else:
                if "Permission denied" in str(result):
                    success, result = create_alphabet_font(self.letters_dict, alt_output_path, self.font_name)
                    if success:
                        self.output_path = alt_output_path
                        self.generation_complete.emit(True, self.output_path, self.letters_dict)
                        return
                
                self.generation_complete.emit(False, f"Errore: {result}", {})
                
        except Exception as e:
            import traceback
            traceback.print_exc()  
            
            self.update_progress.emit(0, f"Errore: {str(e)}")
            self.generation_complete.emit(False, f"Errore: {str(e)}", {})

# ------------------------------------------------------------------------
# WIDGET PER ANTEPRIMA LETTERA
# ------------------------------------------------------------------------

class LetterPreviewWidget(QWidget):
    def __init__(self, letter="A", parent=None):
        super().__init__(parent)
        self.letter = letter
        self.contours = []
        self.cut_lines = []  # Lista di valori y (0-1)
        self.setMinimumSize(120, 150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def setContours(self, contours):
        self.contours = contours
        self.update()
        
    def setCutLines(self, cut_points):
        self.cut_lines = cut_points
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Sfondo
        painter.fillRect(self.rect(), Qt.white)
        
        # Bordo
        painter.setPen(QPen(Qt.lightGray, 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        
        # Lettera centrata sopra
        painter.setPen(Qt.black)
        font = QFont("Arial", 12, QFont.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignHCenter, self.letter)
        
        # Area di disegno della lettera
        draw_rect = self.rect().adjusted(10, 25, -10, -10)
        
        if not self.contours:
            # Se non ci sono contorni, mostra un messaggio
            painter.setPen(Qt.gray)
            painter.drawText(draw_rect, Qt.AlignCenter, "Nessun\ncontorno")
            return
            
        # Disegna le linee di taglio
        painter.setPen(QPen(QColor(255, 0, 0, 128), 1))
        for cut in self.cut_lines:
            # QUESTA È LA PARTE CORRETTA: Usa QPointF per coordinate float
            y_pos = draw_rect.top() + (1.0 - cut) * draw_rect.height()
            start_point = QPointF(draw_rect.left(), y_pos)
            end_point = QPointF(draw_rect.right(), y_pos)
            painter.drawLine(start_point, end_point)
            
        # Disegna il contorno della lettera
        all_points = [pt for c in self.contours for pt in c]
        if not all_points:
            return
            
        min_x = min(p[0] for p in all_points)
        max_x = max(p[0] for p in all_points)
        min_y = min(p[1] for p in all_points)
        max_y = max(p[1] for p in all_points)
        
        # Fattore di scala
        scale_x = draw_rect.width() / (max_x - min_x) if max_x > min_x else 1
        scale_y = draw_rect.height() / (max_y - min_y) if max_y > min_y else 1
        scale = min(scale_x, scale_y) * 0.9  # 90% per margine
        
        # Centro del rettangolo di disegno
        center_x = draw_rect.left() + draw_rect.width() / 2
        center_y = draw_rect.top() + draw_rect.height() / 2
        
        # Centro del glifo
        glyph_center_x = (min_x + max_x) / 2
        glyph_center_y = (min_y + max_y) / 2
        
        # Disegna i contorni
        painter.setPen(QPen(Qt.black, 1))
        painter.setBrush(QColor(0, 0, 0, 40))
        
        for contour in self.contours:
            if len(contour) < 3:
                continue
                
            path = QPainterPath()
            
            # Trasforma le coordinate
            first_x = center_x + (contour[0][0] - glyph_center_x) * scale
            # Invertiamo y perché nei font y cresce verso l'alto
            first_y = center_y - (contour[0][1] - glyph_center_y) * scale
            
            path.moveTo(first_x, first_y)
            
            for x, y in contour[1:]:
                tx = center_x + (x - glyph_center_x) * scale
                ty = center_y - (y - glyph_center_y) * scale
                path.lineTo(tx, ty)
                
            path.closeSubpath()
            painter.drawPath(path)

# ------------------------------------------------------------------------
# WIDGET PER ANTEPRIMA DELL'ALFABETO
# ------------------------------------------------------------------------

class AlphabetPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.letters_dict = {}  # {'A': contours, 'B': contours, ...}
        self.setMinimumSize(600, 200)
        
    def setLetters(self, letters_dict):
        self.letters_dict = letters_dict
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Sfondo
        painter.fillRect(self.rect(), Qt.white)
        
        # Bordo
        painter.setPen(QPen(Qt.lightGray, 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        
        if not self.letters_dict:
            # Se non ci sono lettere, mostra un messaggio
            painter.setPen(Qt.gray)
            painter.drawText(self.rect(), Qt.AlignCenter, "Nessuna lettera generata")
            return
            
        # Calcoliamo la disposizione delle lettere
        num_letters = len(self.letters_dict)
        cols = min(13, num_letters)  # Max 13 lettere per riga
        rows = (num_letters + cols - 1) // cols
        
        cell_width = self.width() / cols
        cell_height = self.height() / rows
        
        # Disegna ogni lettera
        letters = sorted(self.letters_dict.keys())
        for i, letter in enumerate(letters):
            row = i // cols
            col = i % cols
            
            x = col * cell_width
            y = row * cell_height
            
            letter_rect = QRectF(x, y, cell_width, cell_height)
            
            painter.save()
            painter.setClipRect(letter_rect)
            
            contours = self.letters_dict[letter]
            if not contours:
                # Lettera vuota
                painter.setPen(Qt.gray)
                painter.drawText(letter_rect, Qt.AlignCenter, letter)
                painter.restore()
                continue
                
            all_points = [pt for c in contours for pt in c]
            min_x = min(p[0] for p in all_points)
            max_x = max(p[0] for p in all_points)
            min_y = min(p[1] for p in all_points)
            max_y = max(p[1] for p in all_points)
            
            scale_x = (cell_width * 0.8) / (max_x - min_x) if max_x > min_x else 1
            scale_y = (cell_height * 0.8) / (max_y - min_y) if max_y > min_y else 1
            scale = min(scale_x, scale_y)
            
            center_x = x + cell_width / 2
            center_y = y + cell_height / 2
            
            glyph_center_x = (min_x + max_x) / 2
            glyph_center_y = (min_y + max_y) / 2
            
            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(QColor(0, 0, 0, 80))
            
            for contour in contours:
                if len(contour) < 3:
                    continue
                    
                path = QPainterPath()
                
                first_x = center_x + (contour[0][0] - glyph_center_x) * scale
                first_y = center_y - (contour[0][1] - glyph_center_y) * scale
                
                path.moveTo(first_x, first_y)
                
                for x_pt, y_pt in contour[1:]:
                    tx = center_x + (x_pt - glyph_center_x) * scale
                    ty = center_y - (y_pt - glyph_center_y) * scale
                    path.lineTo(tx, ty)
                    
                path.closeSubpath()
                painter.drawPath(path)
                
            painter.setPen(Qt.black)
            font = QFont("Arial", 8)
            painter.setFont(font)
            painter.drawText(letter_rect.adjusted(0, 0, 0, -5), Qt.AlignBottom | Qt.AlignHCenter, letter)
            
            painter.restore()

# ------------------------------------------------------------------------
# GUI PyQt5 MIGLIORATA
# ------------------------------------------------------------------------

class FontMixerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Font Mixer - Generatore di Font Ibridi")
        self.setMinimumSize(900, 700)
        
        self.font_paths = []
        self.available_fonts = []
        self.selected_fonts = []
        self.cut_method = "random"
        self.custom_cuts = [0.5]  # Valore default
        self.letters_dict = {}
        self.output_font_path = ""
        
        self.setupUi()
        self.loadAvailableFonts()
        
    def setupUi(self):
        # Widget centrale
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principale
        main_layout = QVBoxLayout(central_widget)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tab_generator = QWidget()
        self.tab_preview = QWidget()
        
        self.tabs.addTab(self.tab_generator, "Generatore")
        self.tabs.addTab(self.tab_preview, "Anteprima")
        
        main_layout.addWidget(self.tabs)
        
        # --- TAB GENERATORE ---
        generator_layout = QVBoxLayout(self.tab_generator)
        
        # Gruppo Font
        font_group = QGroupBox("Selezione Font")
        font_layout = QVBoxLayout(font_group)
        
        # Layout per aggiungere font
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
        
        # Gruppo opzioni di mixaggio
        mix_group = QGroupBox("Opzioni di Mixaggio")
        mix_layout = QVBoxLayout(mix_group)
        
        # Metodo di taglio
        cut_method_layout = QHBoxLayout()
        cut_method_layout.addWidget(QLabel("Metodo di taglio:"))
        self.combo_cut_method = QComboBox()
        self.combo_cut_method.addItems(["Casuale", "Equidistante", "Personalizzato"])
        cut_method_layout.addWidget(self.combo_cut_method)
        
        mix_layout.addLayout(cut_method_layout)
        
        # Opzioni di taglio personalizzato
        self.custom_cuts_group = QGroupBox("Punti di taglio personalizzati")
        custom_cuts_layout = QGridLayout(self.custom_cuts_group)
        
        self.cut_sliders = []
        for i in range(4):  # Supportiamo fino a 5 font (4 punti di taglio)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(10, 90)
            slider.setValue(50)
            slider.setEnabled(False)
            
            label = QLabel(f"Taglio {i+1}:")
            value_label = QLabel("50%")
            
            custom_cuts_layout.addWidget(label, i, 0)
            custom_cuts_layout.addWidget(slider, i, 1)
            custom_cuts_layout.addWidget(value_label, i, 2)
            
            slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(f"{v}%"))
            
            self.cut_sliders.append((slider, value_label))
        
        mix_layout.addWidget(self.custom_cuts_group)
        self.custom_cuts_group.setVisible(False)
        
        # Nome del font
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nome del font:"))
        self.font_name_edit = QLineEdit("MixedFont")
        name_layout.addWidget(self.font_name_edit)
        
        mix_layout.addLayout(name_layout)
        
        # Pulsante genera
        generate_layout = QHBoxLayout()
        self.btn_generate = QPushButton("GENERA FONT")
        self.btn_generate.setMinimumHeight(40)
        generate_layout.addWidget(self.btn_generate)
        
        # Progress bar
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_status = QLabel("Pronto")
        progress_layout.addWidget(self.progress_bar, 3)
        progress_layout.addWidget(self.progress_status, 1)
        
        # Aggiungi i gruppi al tab generatore
        generator_layout.addWidget(font_group, 3)
        generator_layout.addWidget(mix_group, 2)
        generator_layout.addLayout(generate_layout)
        generator_layout.addLayout(progress_layout)
        
        # --- TAB ANTEPRIMA ---
        preview_layout = QVBoxLayout(self.tab_preview)
        
        # Layout orizzontale per anteprima e controlli
        preview_controls_layout = QHBoxLayout()
        
        # Area di scorrimento per le lettere
        letters_scroll = QScrollArea()
        letters_scroll.setWidgetResizable(True)
        letters_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        letters_container = QWidget()
        self.letters_grid = QGridLayout(letters_container)
        
        # Creiamo widget per ciascuna lettera
        self.letter_widgets = {}
        for i, letter in enumerate(ascii_uppercase):
            row = i // 7
            col = i % 7
            
            letter_widget = LetterPreviewWidget(letter)
            self.letters_grid.addWidget(letter_widget, row, col)
            self.letter_widgets[letter] = letter_widget
        
        letters_scroll.setWidget(letters_container)
        
        # Pannello controlli anteprima
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
        
        # Aggiungiamo i controlli
        preview_controls_panel.addWidget(self.preview_label)
        preview_controls_panel.addWidget(self.btn_export)
        preview_controls_panel.addWidget(self.btn_load_in_system)
        preview_controls_panel.addWidget(self.btn_test_text)
        preview_controls_panel.addStretch()
        
        # Aggiungiamo a layout orizzontale
        preview_controls_layout.addWidget(letters_scroll, 7)
        preview_controls_layout.addWidget(preview_controls, 3)
        
        # Anteprima alfabeto completo
        preview_alphabet_group = QGroupBox("Anteprima Alfabeto Completo")
        preview_alphabet_layout = QVBoxLayout(preview_alphabet_group)
        
        self.alphabet_preview = AlphabetPreviewWidget()
        preview_alphabet_layout.addWidget(self.alphabet_preview)
        
        # Aggiungiamo tutto al layout principale della tab
        preview_layout.addLayout(preview_controls_layout, 7)
        preview_layout.addWidget(preview_alphabet_group, 3)
        
        # --- CONNESSIONI ---
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

        # Aggiorniamo lo stato iniziale dell'UI
        self.updateUI()
    
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
        # Aggiorna pulsanti font
        num_selected = len(self.font_list.selectedItems())
        self.btn_remove_font.setEnabled(num_selected > 0)
        
        selected_row = -1
        if self.font_list.currentItem() is not None:
            selected_row = self.font_list.row(self.font_list.currentItem())
    
        self.btn_move_up.setEnabled(num_selected == 1 and selected_row > 0)
        self.btn_move_down.setEnabled(
            num_selected == 1 and 
            selected_row >= 0 and  # Assicurati che un elemento sia selezionato
            selected_row < self.font_list.count() - 1
        )
        
        # Aggiorna stato generazione
        can_generate = self.font_list.count() >= 2
        self.btn_generate.setEnabled(can_generate)
        
        # Aggiorna sliders taglio personalizzato
        self.custom_cuts_group.setVisible(self.combo_cut_method.currentText() == "Personalizzato")
        
        num_cuts = max(0, self.font_list.count() - 1)
        for i, (slider, label) in enumerate(self.cut_sliders):
            enabled = i < num_cuts
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
        
        # Aggiorna UI
        self.custom_cuts_group.setVisible(method == "Personalizzato")
        self.updateUI()
        
        # Se passiamo a taglio equidistante, impostiamo i valori
        if method == "Equidistante":
            self.updateEqualCutSliders()
    
    def updateCutSliders(self):
        """Aggiorna gli slider in base al numero di font"""
        num_cuts = max(0, self.font_list.count() - 1)
        
        if self.combo_cut_method.currentText() == "Equidistante":
            self.updateEqualCutSliders()
        else:
            # Abilitiamo/disabilitiamo gli slider
            for i, (slider, label) in enumerate(self.cut_sliders):
                enabled = i < num_cuts
                slider.setEnabled(enabled)
                label.setEnabled(enabled)
    
    def updateEqualCutSliders(self):
        """Imposta gli slider a valori equidistanti"""
        num_cuts = max(0, self.font_list.count() - 1)
        
        if num_cuts <= 0:
            return
            
        # Calcola valori equidistanti
        for i, (slider, label) in enumerate(self.cut_sliders):
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
        """Ottiene i punti di taglio personalizzati"""
        cut_points = []
        num_cuts = self.font_list.count() - 1
        
        for i, (slider, _) in enumerate(self.cut_sliders):
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
        
        # Disabilita UI durante la generazione
        self.btn_generate.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_status.setText("Inizializzazione...")
        
        # Prepara parametri
        font_paths = self.getSelectedFontPaths()
        
        cut_method_map = {
            "Casuale": "random",
            "Equidistante": "equal",
            "Personalizzato": "custom"
        }
        cut_method = cut_method_map[self.combo_cut_method.currentText()]
        
        custom_cuts = None
        if cut_method == "custom":
            custom_cuts = self.getCustomCutPoints()
            
        font_name = self.font_name_edit.text().strip()
        if not font_name:
            font_name = "MixedFont"
            
        # Crea thread generatore
        self.generator_thread = FontGeneratorThread(
            font_paths, 
            cut_method, 
            custom_cuts, 
            font_name
        )
        
        # Connetti segnali
        self.generator_thread.update_progress.connect(self.updateProgress)
        self.generator_thread.generation_complete.connect(self.onGenerationComplete)
        
        # Avvia generazione
        self.generator_thread.start()
    
    def updateProgress(self, value, status):
        """Aggiorna la barra di progresso"""
        self.progress_bar.setValue(value)
        self.progress_status.setText(status)
    
    def onGenerationComplete(self, success, message, letters_dict):
        """Gestisce il completamento della generazione"""
        # Riabilita UI
        self.btn_generate.setEnabled(True)
    
        if not success:
            QMessageBox.warning(self, "Errore", f"Generazione fallita:\n{message}")
            return
    
        try:
            # Verifica che il percorso sia valido
            if not os.path.exists(message):
                QMessageBox.warning(
                    self, 
                    "File non trovato",
                    f"Il file generato non è stato trovato in:\n{message}\n\n"
                    "Controlla la cartella output manualmente."
                )
                return
        
            # Memorizza risultati
            self.letters_dict = letters_dict
            self.output_font_path = message  # Il percorso del font
        
            # Aggiorna anteprima con gestione errori
            try:
                self.updateLetterPreviews()
                self.alphabet_preview.setLetters(letters_dict)
            except Exception as e:
                print(f"Errore nell'aggiornamento delle anteprime: {str(e)}")
                traceback.print_exc()
        
            # Abilita controlli anteprima
            self.btn_export.setEnabled(True)
            self.btn_load_in_system.setEnabled(True)
            self.btn_test_text.setEnabled(True)
        
            # Passa alla tab di anteprima
            self.tabs.setCurrentIndex(1)
        
            # Notifica utente
            QMessageBox.information(
                self, 
                "Font Generato", 
                f"Font generato con successo!\nSalvato in: {self.output_font_path}"
            )
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
            
        # Calcola punti di taglio per visualizzazione
        cut_points = []
        num_cuts = self.font_list.count() - 1
        
        if self.combo_cut_method.currentText() == "Personalizzato":
            cut_points = self.getCustomCutPoints()
        elif self.combo_cut_method.currentText() == "Equidistante":
            cut_points = [(i + 1) / (num_cuts + 1) for i in range(num_cuts)]
        else:
            # Per il metodo casuale, non mostriamo linee
            cut_points = []
        
        # Aggiorna ogni widget lettera
        for letter, contours in self.letters_dict.items():
            if letter in self.letter_widgets:
                self.letter_widgets[letter].setContours(contours)
                self.letter_widgets[letter].setCutLines(cut_points)
    
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
        preview_font = QFont(family, 24)
        
        self.preview_label.setFont(preview_font)
        self.preview_label.setText("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        
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
        from PyQt5.QtWidgets import QDialog, QTextEdit, QVBoxLayout
        
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

# ------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    
    for folder in ["fonts", "output"]:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    window = FontMixerApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()