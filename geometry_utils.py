"""
Modulo per le operazioni geometriche sui poligoni.
Gestisce operazioni come taglio, unione e trasformazione di contorni di glifi.
"""

import traceback
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely.affinity import scale, translate

def polygon_from_contour(contour):
    """
    Crea un poligono Shapely da un contorno.
    Gestisce correttamente i contorni complessi e garantisce validità.
    
    Args:
        contour: Lista di punti (x, y)
        
    Returns:
        Oggetto Polygon Shapely o None in caso di errore
    """
    if not contour or len(contour) < 3:
        return None
    
    if contour[0] != contour[-1]:
        contour = contour + [contour[0]]
    
    try:
        poly = Polygon(contour)
        
        # Assicura che il contorno esterno segua l'orientamento corretto (antiorario)
        if poly.exterior.is_ccw:
            poly = Polygon(list(poly.exterior.coords)[::-1])
        
        # Correzione della validità del poligono
        if not poly.is_valid:
            poly = poly.buffer(0.1).simplify(0.1)
        
        return poly if not poly.is_empty else None
    
    except Exception as e:
        print(f"Errore creazione poligono: {str(e)}")
        return None


def polygon_to_contours(poly):
    """
    Converte un poligono Shapely in una lista di contorni.
    Supporta MultiPolygon per risultati complessi delle operazioni.
    Gestisce correttamente i buchi (contorni interni).
    
    Args:
        poly: Oggetto Polygon o MultiPolygon Shapely
        
    Returns:
        Lista di contorni, dove ogni contorno è una lista di tuple (x, y)
    """
    if not poly or poly.is_empty:
        return []
    
    contours = []
    
    if isinstance(poly, MultiPolygon):
        for geom in poly.geoms:
            contours.extend(polygon_to_contours(geom))
        return contours
    
    # Estrai contorno esterno - assicurandosi che sia chiuso e in senso antiorario (CCW)
    exterior = list(poly.exterior.coords)
    if exterior:
        # Verifica che il contorno sia chiuso (primo punto = ultimo punto)
        if exterior[0] != exterior[-1]:
            exterior.append(exterior[0])
        
        # Verifica l'orientamento (deve essere CCW per contorni esterni)
        # Se è in senso orario (CW), inverti
        area = 0
        for i in range(len(exterior) - 1):
            area += exterior[i][0] * exterior[i+1][1] - exterior[i+1][0] * exterior[i][1]
        
        if area < 0:  # Se l'area è negativa, il contorno è in senso orario (CW)
            exterior = exterior[::-1]  # Inverti l'ordine
        
        contours.append(exterior)
    
    # Estrai "buchi" interni - assicurandosi che siano in senso orario (CW)
    for interior in poly.interiors:
        hole = list(interior.coords)
        if hole:
            # Verifica che il contorno sia chiuso
            if hole[0] != hole[-1]:
                hole.append(hole[0])
            
            # Verifica l'orientamento (deve essere CW per buchi)
            # Se è in senso antiorario (CCW), inverti
            area = 0
            for i in range(len(hole) - 1):
                area += hole[i][0] * hole[i+1][1] - hole[i+1][0] * hole[i][1]
            
            if area > 0:  # Se l'area è positiva, il contorno è in senso antiorario (CCW)
                hole = hole[::-1]  # Inverti l'ordine
            
            contours.append(hole)
    
    # Debug
    if len(contours) > 1:
        print(f"Estratti {len(contours)} contorni (1 esterno + {len(contours)-1} buchi)")
    
    return contours


def cut_polygon_at_y(poly, y_cut):
    """
    Versione migliorata: Taglia un poligono ad un valore y specifico
    usando l'operazione di intersezione diretta con rettangoli.
    
    Args:
        poly: Oggetto Polygon o MultiPolygon Shapely
        y_cut: Valore y dove tagliare
        
    Returns:
        Tuple (top_part, bottom_part) con parti del poligono
    """
    from shapely.geometry import box
    
    if not poly or poly.is_empty:
        return None, None

    # Ottieni i limiti del poligono
    minx, miny, maxx, maxy = poly.bounds
    
    # Crea box per le parti superiore e inferiore con un margine di sicurezza
    margin = max(1000, (maxx - minx), (maxy - miny))
    
    # Box superiore: da y_cut a infinito
    top_box = box(minx - margin, y_cut, maxx + margin, maxy + margin)
    
    # Box inferiore: da -infinito a y_cut
    bottom_box = box(minx - margin, miny - margin, maxx + margin, y_cut)
    
    # Esegui le intersezioni
    try:
        top_part = poly.intersection(top_box)
        bottom_part = poly.intersection(bottom_box)
        
        # Aggiungi buffer per garantire validità
        if top_part and not top_part.is_empty:
            top_part = top_part.buffer(0)
        if bottom_part and not bottom_part.is_empty:
            bottom_part = bottom_part.buffer(0)
        
        # Verifica i risultati del taglio
        if top_part and not top_part.is_empty:
            print(f"  Taglio Y={y_cut}: parte superiore ha bounds {top_part.bounds}")
        else:
            print(f"  Taglio Y={y_cut}: parte superiore è vuota")
            
        if bottom_part and not bottom_part.is_empty:
            print(f"  Taglio Y={y_cut}: parte inferiore ha bounds {bottom_part.bounds}")
        else:
            print(f"  Taglio Y={y_cut}: parte inferiore è vuota")
            
        return top_part, bottom_part
        
    except Exception as e:
        print(f"Errore nel taglio a Y={y_cut}: {e}")
        traceback.print_exc()
        return None, None


def cut_polygon_at_x(poly, x_cut):
    """
    Versione migliorata: Taglia un poligono ad un valore x specifico
    usando l'operazione di intersezione diretta con rettangoli.
    
    Args:
        poly: Oggetto Polygon o MultiPolygon Shapely
        x_cut: Valore x dove tagliare
        
    Returns:
        Tuple (left_part, right_part) con parti del poligono
    """
    from shapely.geometry import box
    
    if not poly or poly.is_empty:
        return None, None

    # Ottieni i limiti del poligono
    minx, miny, maxx, maxy = poly.bounds
    
    # Crea box per le parti sinistra e destra con un margine di sicurezza
    margin = max(1000, (maxx - minx), (maxy - miny))
    
    # Box sinistro: da -infinito a x_cut
    left_box = box(minx - margin, miny - margin, x_cut, maxy + margin)
    
    # Box destro: da x_cut a infinito
    right_box = box(x_cut, miny - margin, maxx + margin, maxy + margin)
    
    # Esegui le intersezioni
    try:
        left_part = poly.intersection(left_box)
        right_part = poly.intersection(right_box)
        
        # Aggiungi buffer per garantire validità
        if left_part and not left_part.is_empty:
            left_part = left_part.buffer(0)
        if right_part and not right_part.is_empty:
            right_part = right_part.buffer(0)
        
        # Verifica i risultati del taglio
        if left_part and not left_part.is_empty:
            print(f"  Taglio X={x_cut}: parte sinistra ha bounds {left_part.bounds}")
        else:
            print(f"  Taglio X={x_cut}: parte sinistra è vuota")
            
        if right_part and not right_part.is_empty:
            print(f"  Taglio X={x_cut}: parte destra ha bounds {right_part.bounds}")
        else:
            print(f"  Taglio X={x_cut}: parte destra è vuota")
            
        return left_part, right_part
        
    except Exception as e:
        print(f"Errore nel taglio a X={x_cut}: {e}")
        traceback.print_exc()
        return None, None


# Per compatibilità con il codice esistente
def cut_polygon_quadrants(poly, x_cut, y_cut):
    """
    Taglia un poligono in quattro quadranti usando tagli sia orizzontali che verticali.
    
    Args:
        poly: Oggetto Polygon o MultiPolygon Shapely
        x_cut: Valore x dove tagliare
        y_cut: Valore y dove tagliare
        
    Returns:
        Tuple (top_left, top_right, bottom_left, bottom_right) con parti del poligono
    """
    from shapely.geometry import box
    
    if not poly or poly.is_empty:
        return None, None, None, None
    
    # Ottieni i limiti del poligono
    minx, miny, maxx, maxy = poly.bounds
    
    # Crea i 4 rettangoli per i quadranti
    top_left_box = box(minx, y_cut, x_cut, maxy)
    top_right_box = box(x_cut, y_cut, maxx, maxy)
    bottom_left_box = box(minx, miny, x_cut, y_cut)
    bottom_right_box = box(x_cut, miny, maxx, y_cut)
    
    # Esegui le intersezioni
    try:
        top_left = poly.intersection(top_left_box).buffer(0)
        top_right = poly.intersection(top_right_box).buffer(0)
        bottom_left = poly.intersection(bottom_left_box).buffer(0)
        bottom_right = poly.intersection(bottom_right_box).buffer(0)
        
        return top_left, top_right, bottom_left, bottom_right
    except Exception as e:
        print(f"Errore nel taglio in quadranti: {e}")
        return None, None, None, None


def normalize_glyph_polygon(poly, target_height=1000):
    """
    Normalizza un poligono di glifo mantenendo le proporzioni.
    
    Args:
        poly: Oggetto Polygon o MultiPolygon Shapely
        target_height: Altezza target per la normalizzazione
        
    Returns:
        Poligono normalizzato
    """
    if poly is None or poly.is_empty:
        return poly

    minx, miny, maxx, maxy = poly.bounds
    width = maxx - minx
    height = maxy - miny

    if height == 0 or width == 0:
        return poly

    # Fattore di scala per mantenere le proporzioni
    scale_factor = min(target_height / height, target_height / width)

    # Centratura e ridimensionamento
    centered = translate(poly, -minx - width/2, -miny - height/2)
    scaled = scale(centered, xfact=scale_factor, yfact=scale_factor)
    
    return translate(scaled, target_height/2, target_height/2)