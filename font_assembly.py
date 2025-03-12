"""
Modulo per l'assemblaggio e la creazione di font.
Gestisce la creazione di un font TTF completo a partire dai contorni dei glifi.
"""

import os
import time
import traceback
from string import ascii_uppercase

from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables.O_S_2f_2 import Panose
from fontTools.ttLib.tables._n_a_m_e import NameRecord
from fontTools.ttLib.tables._c_m_a_p import cmap_format_4

from font_utils import contours_to_glyph
from geometry_utils import polygon_to_contours


def create_alphabet_font(letters_dict, output_path, font_name="MixedFont"):
    """
    Crea un font TTF con le lettere specificate.
    
    Args:
        letters_dict: { 'A': [contorni], 'B': [contorni], ... }
        output_path: percorso dove salvare il file TTF
        font_name: nome del font
        
    Returns:
        Tuple (success, result) con success=True/False e result=path/error_message
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
        head_table.created = int(time.time() - time.timezone)  # Usa il timestamp corrente
        head_table.modified = int(time.time() - time.timezone)
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
        
        # =============== .notdef - VERSIONE MIGLIORATA
        from fontTools.pens.ttGlyphPen import TTGlyphPen
        pen = TTGlyphPen(None)
        
        # Rettangolo esterno
        pen.moveTo((100, 0))
        pen.lineTo((500, 0)) 
        pen.lineTo((500, 700))
        pen.lineTo((100, 700))
        pen.closePath()
        
        # Rettangolo interno (spazio negativo)
        pen.moveTo((200, 100))
        pen.lineTo((200, 600))
        pen.lineTo((400, 600))
        pen.lineTo((400, 100))
        pen.closePath()
        
        notdef_glyph = pen.glyph()
        
        setattr(new_font["glyf"], "glyphs", {})
        new_font["glyf"].glyphOrder = glyph_order
        new_font["glyf"].glyphs[".notdef"] = notdef_glyph
        new_font["hmtx"].metrics[".notdef"] = (600, 100)
        
        # =============== LETTERE
        for letter, contours in letters_dict.items():
            if not contours:
                # Crea un glifo vuoto se non ci sono contorni
                g = TTGlyphPen(None).glyph()
                new_font["hmtx"].metrics[letter] = (500, 0)
            else:
                # Converti i contorni in glifo
                g = contours_to_glyph(contours)
            
                # Calcolo avanzamento corretto
                all_points = [pt for c in contours for pt in c]
                if all_points:
                    max_x = max(p[0] for p in all_points)
                    min_x = min(p[0] for p in all_points)
                    width = max_x - min_x
                    
                    # Larghezza avanzamento con padding del 20%
                    advance = int(width * 1.2)
                    lsb = max(0, int(min_x - (width * 0.1)))
                    
                    # Assicurati che ci sia un minimo ragionevole
                    advance = max(advance, 500)
                    new_font["hmtx"].metrics[letter] = (advance, lsb)
                else:
                    # Default per glifi senza punti
                    new_font["hmtx"].metrics[letter] = (500, 0)

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
        new_font["name"].names.append(_makeName(f"{font_name} Regular", 3))  # Unique identifier
        new_font["name"].names.append(_makeName(font_name, 4))  # Full font name
        new_font["name"].names.append(_makeName("Version 1.000", 5))  # Version string
        new_font["name"].names.append(_makeName(f"{font_name}-Regular", 6))  # PostScript name
        new_font["name"].names.append(_makeName("Generated with FontMixer", 7))  # Trademark
        new_font["name"].names.append(_makeName("FontMixer", 8))  # Manufacturer
        new_font["name"].names.append(_makeName("FontMixer", 9))  # Designer
        
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
        
        # =============== LOCA
        new_font["loca"] = newTable("loca")
        
        # =============== CALCOLA I VALORI MIN/MAX CORRETTI
        for gname in new_font.getGlyphOrder():
            g = new_font["glyf"][gname]
            if g is not None:
                g.recalcBounds(None)
        
        all_xmin = []
        all_xmax = []
        all_ymin = []
        all_ymax = []
        
        for gname in new_font.getGlyphOrder():
            g = new_font["glyf"][gname]
            if g is not None and hasattr(g, "xMin") and g.xMin is not None:
                all_xmin.append(g.xMin)
                all_xmax.append(g.xMax)
                all_ymin.append(g.yMin)
                all_ymax.append(g.yMax)
        
        # Aggiorna i valori nella tabella head
        head_table.xMin = min(all_xmin) if all_xmin else 0
        head_table.xMax = max(all_xmax) if all_xmax else 0
        head_table.yMin = min(all_ymin) if all_ymin else 0
        head_table.yMax = max(all_ymax) if all_ymax else 0
        
        # =============== SALVA IL FONT CON GESTIONE DEGLI ERRORI
        
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