"""
Modulo per la gestione e manipolazione di font.
Contiene funzioni per estrarre contorni dai glifi e normalizzarli.
"""

import traceback
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from shapely.ops import unary_union

def get_glyph_contours(font: TTFont, glyph_name: str):
    """
    Estrae i contorni di un glifo da un font TTF o OTF.
    Gestisce in modo corretto sia font TrueType che OpenType/CFF.
    
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
    """
    Estrae i contorni di un glifo da un font TrueType.
    Gestisce correttamente i glifi compositi.
    
    Args:
        font: oggetto TTFont
        glyph_name: nome del glifo (es. "A")
        
    Returns:
        Lista di contorni, dove ogni contorno è una lista di tuple (x, y)
    """
    try:
        glyf_table = font["glyf"]
        if glyph_name not in glyf_table:
            return []
            
        glyph = glyf_table[glyph_name]
        
        # Gestione dei glifi compositi
        if glyph.isComposite():
            components = []
            for comp in glyph.components:
                base_contours = get_ttf_glyph_contours(font, comp.glyphName)
                
                # Trasforma le coordinate secondo la matrice di trasformazione
                transformed_contours = []
                for contour in base_contours:
                    transformed_contour = [
                        (x * comp.transform[0] + y * comp.transform[2] + comp.transform[4], 
                         x * comp.transform[1] + y * comp.transform[3] + comp.transform[5])
                        for x, y in contour
                    ]
                    transformed_contours.append(transformed_contour)
                
                components.extend(transformed_contours)
            return components
        
        # Gestione dei glifi semplici
        if not hasattr(glyph, "coordinates") or glyph.numberOfContours <= 0:
            return []
        
        coordinates = glyph.coordinates
        end_pts = glyph.endPtsOfContours
        
        contours = []
        start = 0
        
        for end in end_pts:
            points = []
            for i in range(start, end + 1):
                x, y = coordinates[i]
                points.append((x, y))
                
            # Chiudi il contorno se necessario
            if points and points[0] != points[-1]:
                points.append(points[0])
                
            contours.append(points)
            start = end + 1
        
        return contours
    
    except Exception as e:
        print(f"Errore estrazione TTF: {str(e)}")
        traceback.print_exc()
        return []


def get_cff_glyph_contours(font: TTFont, glyph_name: str):
    """
    Estrae i contorni di un glifo da un font OpenType (CFF).
    Approssima le curve di Bézier con segmenti lineari.
    
    Args:
        font: oggetto TTFont
        glyph_name: nome del glifo (es. "A")
        
    Returns:
        Lista di contorni, dove ogni contorno è una lista di tuple (x, y)
    """
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
                if current_contour:
                    contours.append(current_contour)
                current_contour = [tuple(operands[0])]  # Converti a tuple
                
            # Approssimazione curves con alta risoluzione
            elif operator == "curveTo":
                if current_contour:
                    p0 = current_contour[-1]
                    p1, p2, p3 = (tuple(op) for op in operands)
                    
                    # Aumenta la risoluzione
                    steps = 20
                    for t in (i/steps for i in range(1, steps+1)):
                        x = (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
                        y = (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
                        current_contour.append((x, y))
                        
            # Approssimazione per curve quadratiche
            elif operator == "qCurveTo":
                if current_contour and operands:
                    p0 = current_contour[-1]
                    control_points = operands
                    
                    # L'ultimo punto è il punto finale
                    for i in range(len(control_points) - 1):
                        p1 = tuple(control_points[i])
                        p2 = tuple(control_points[i+1])
                        
                        # Approssimazione
                        steps = 10
                        for t in (i/steps for i in range(1, steps+1)):
                            x = (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0]
                            y = (1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t**2 * p2[1]
                            current_contour.append((x, y))
                            
                        p0 = p2  # Preparati per il prossimo segmento
                        
            elif operator == "lineTo":
                if current_contour:
                    current_contour.append(tuple(operands[0]))
                    
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
        
        return contours
    except Exception as e:
        print(f"Errore CFF: {str(e)}")
        traceback.print_exc()
        return []


def normalize_glyph_contours(contours, target_height=1000):
    """
    Normalizza i contorni per adattarli a un'altezza target.
    
    Args:
        contours: Lista di contorni
        target_height: Altezza target per la normalizzazione
        
    Returns:
        Lista di contorni normalizzati
    """
    if not contours:
        return []
    
    # Trova min/max per normalizzare
    all_points = [pt for c in contours for pt in c]
    min_x = min(p[0] for p in all_points)
    max_x = max(p[0] for p in all_points)
    min_y = min(p[1] for p in all_points)
    max_y = max(p[1] for p in all_points)
    
    # Calcola il fattore di scala
    height = max_y - min_y
    width = max_x - min_x
    if height == 0 or width == 0:
        return contours  # Evita divisione per zero
    
    # Calcola il fattore di scala mantenendo le proporzioni
    scale = min(target_height / height, target_height / width)
    
    # Calcola l'offset per centrare
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    
    normalized = []
    for contour in contours:
        new_contour = []
        for x, y in contour:
            # Centra, scala e sposta
            new_x = (x - center_x) * scale + target_height/2
            new_y = (y - center_y) * scale + target_height/2
            new_contour.append((new_x, new_y))
        normalized.append(new_contour)
    
    return normalized


def contours_to_glyph(contours):
    """
    Converte una lista di contorni in un oggetto Glyph per FontTools.
    Gestisce correttamente i buchi interni delle lettere.
    
    Args:
        contours: Lista di contorni
        
    Returns:
        Oggetto Glyph
    """
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    
    # Controlla se abbiamo contorni validi
    if not contours:
        print("Nessun contorno da convertire in glifo")
        return TTGlyphPen(None).glyph()
        
    print(f"Conversione di {len(contours)} contorni in glifo")
    
    # 1. Separa i contorni esterni e interni (buchi)
    # I contorni esterni sono in senso antiorario (CCW)
    # I contorni interni (buchi) sono in senso orario (CW)
    exteriors = []
    interiors = []
    
    for c in contours:
        if not c or len(c) < 3:
            continue
            
        # Calcola l'orientamento del contorno (segno dell'area)
        # Se l'area è negativa, il contorno è in senso orario (CW)
        area = 0
        for i in range(len(c) - 1):
            area += c[i][0] * c[i+1][1] - c[i+1][0] * c[i][1]
            
        # Assicura che il contorno sia chiuso
        if c[0] != c[-1]:
            c = c + [c[0]]
        
        if area < 0:  # Senso orario (CW) - buco interno
            interiors.append(c)
            print(f"  Contorno interno rilevato con {len(c)} punti")
        else:  # Senso antiorario (CCW) - contorno esterno
            exteriors.append(c)
            print(f"  Contorno esterno rilevato con {len(c)} punti")
    
    print(f"  Totale: {len(exteriors)} contorni esterni, {len(interiors)} contorni interni")
    
    # 2. Ordina i contorni esterni per area (i più grandi prima)
    sorted_exteriors = []
    if exteriors:
        exterior_areas = []
        for c in exteriors:
            # Calcola l'area del contorno
            area = 0
            for i in range(len(c) - 1):
                area += c[i][0] * c[i+1][1] - c[i+1][0] * c[i][1]
            exterior_areas.append(abs(area) / 2)
            
        # Ordina i contorni esterni per area decrescente
        sorted_exteriors = [c for _, c in sorted(zip(exterior_areas, exteriors), 
                                              key=lambda pair: -pair[0])]
    
    # 3. Crea il glifo usando la penna
    pen = TTGlyphPen(None)
    
    # Disegna prima i contorni esterni
    for c in sorted_exteriors:
        pen.moveTo(c[0])
        for pt in c[1:]:
            pen.lineTo(pt)
        pen.closePath()
    
    # Poi disegna i contorni interni (buchi)
    for c in interiors:
        pen.moveTo(c[0])
        for pt in c[1:]:
            pen.lineTo(pt)
        pen.closePath()
    
    # Converti in glifo TTF
    return pen.glyph()


def polygon_to_glyph(poly):
    """
    Converte un poligono Shapely in un oggetto Glyph per FontTools.
    
    Args:
        poly: Oggetto Polygon o MultiPolygon Shapely
        
    Returns:
        Oggetto Glyph
    """
    from geometry_utils import polygon_to_contours
    contours = polygon_to_contours(poly)
    return contours_to_glyph(contours)