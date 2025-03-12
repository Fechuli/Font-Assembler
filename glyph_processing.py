"""
Modulo per il processamento e la miscelazione dei glifi.
Contiene algoritmi per combinare glifi da diversi font.
"""

import random
import traceback
from shapely.ops import unary_union
from shapely.geometry import MultiPolygon

# Importa le funzioni dai moduli
from geometry_utils import (
    polygon_from_contour, normalize_glyph_polygon,
    cut_polygon_at_y, cut_polygon_at_x,
    cut_polygon_quadrants
)

from font_utils import get_glyph_contours, polygon_to_glyph


def mix_multiple_polygons(polygons, cut_points):
    """
    Mixa più poligoni usando tagli orizzontali.
    Ogni sezione proviene da un font diverso.
    
    Args:
        polygons: Lista di poligoni Shapely
        cut_points: Lista di punti di taglio normalizzati (0-1000)
        
    Returns:
        Poligono Shapely risultante
    """
    if len(polygons) < 2:
        return polygons[0] if polygons else None

    # Ordina i punti di taglio
    sorted_cuts = sorted(cut_points)
    result = None
    
    for i, poly in enumerate(polygons):
        if poly is None or poly.is_empty:
            continue
            
        # Determina i limiti verticali per questa sezione
        lower = sorted_cuts[i-1] if i > 0 else 0
        upper = sorted_cuts[i] if i < len(sorted_cuts) else 1000
        
        # Estrai la sezione corrispondente
        _, temp = cut_polygon_at_y(poly, lower)
        if temp and not temp.is_empty:
            section, _ = cut_polygon_at_y(temp, upper)
            if section and not section.is_empty:
                # Unisci al risultato
                result = unary_union([result, section]) if result else section
    
    return result


def mix_fonts_deterministic(polygons, h_cuts, v_cuts=None):
    """
    Mixa i font in modo deterministico, assicurando che parti di ogni font 
    siano visibili nel risultato finale.
    
    Args:
        polygons: Lista di poligoni Shapely
        h_cuts: Lista di punti di taglio orizzontali
        v_cuts: Lista di punti di taglio verticali (opzionale)
        
    Returns:
        Poligono Shapely risultante
    """
    from shapely.ops import unary_union
    from shapely.geometry import box

    if not polygons or len(polygons) < 2:
        return polygons[0] if polygons else None
    
    valid_polygons = [p for p in polygons if p and not p.is_empty]
    if not valid_polygons:
        return None
        
    print(f"Mixing {len(valid_polygons)} font deterministically")
    
    # Definisci lo spazio totale come il bound di tutti i poligoni validi
    mins_x = []
    mins_y = []
    maxs_x = []
    maxs_y = []
    
    for poly in valid_polygons:
        minx, miny, maxx, maxy = poly.bounds
        mins_x.append(minx)
        mins_y.append(miny)
        maxs_x.append(maxx)
        maxs_y.append(maxy)
    
    min_x = min(mins_x)
    min_y = min(mins_y)
    max_x = max(maxs_x)
    max_y = max(maxs_y)
    
    # Assicurati che ci siano punti di taglio coerenti
    if not h_cuts:
        h_cuts = [500]  # Dividi a metà orizzontalmente
    
    use_vertical = v_cuts and len(v_cuts) > 0
    
    # Normalizza i punti di taglio da 0-1000 a coordinate reali
    h_cuts_real = [min_y + (max_y - min_y) * cut / 1000.0 for cut in h_cuts]
    
    if use_vertical:
        v_cuts_real = [min_x + (max_x - min_x) * cut / 1000.0 for cut in v_cuts]
        # Aggiungi i bordi
        all_h_cuts = [min_y] + h_cuts_real + [max_y]
        all_v_cuts = [min_x] + v_cuts_real + [max_x]
        
        # Determina la dimensione della griglia
        rows = len(all_h_cuts) - 1
        cols = len(all_v_cuts) - 1
        
        print(f"Creating a {rows}x{cols} grid with vertical cuts")
        print(f"Horizontal cuts: {all_h_cuts}")
        print(f"Vertical cuts: {all_v_cuts}")
        
        # Prepara la matrice di assegnazione
        font_assignments = []
        num_fonts = len(valid_polygons)
        
        if num_fonts == 2:
            # Schema a 4 quadranti alternati per 2 font
            font_assignments = [
                [0, 1],
                [1, 0]
            ]
        elif num_fonts == 3:
            # Schema per 3 font
            font_assignments = [
                [0, 1, 2],
                [2, 0, 1]
            ]
        elif num_fonts == 4:
            # Schema per 4 font
            font_assignments = [
                [0, 1, 2, 3],
                [3, 2, 1, 0]
            ]
        else:
            # Schema generico
            for i in range(rows):
                row_assignments = []
                for j in range(cols):
                    row_assignments.append((i + j) % num_fonts)
                font_assignments.append(row_assignments)
        
        # Adatta la matrice alla dimensione effettiva della griglia
        while len(font_assignments) < rows:
            font_assignments.append(font_assignments[-1])
        font_assignments = font_assignments[:rows]
        
        for i in range(rows):
            while len(font_assignments[i]) < cols:
                font_assignments[i].append(font_assignments[i][-1])
            font_assignments[i] = font_assignments[i][:cols]
        
        print("Font assignment matrix:")
        for row in font_assignments:
            print(row)
        
        # Crea le parti e uniscile
        result_polygons = []
        
        for i in range(rows):
            for j in range(cols):
                # Determina quale font usare per questa cella
                font_idx = font_assignments[i][j]
                if font_idx >= len(valid_polygons):
                    continue
                    
                poly = valid_polygons[font_idx]
                
                # Crea un rettangolo per questa cella
                cell_box = box(all_v_cuts[j], all_h_cuts[i], all_v_cuts[j+1], all_h_cuts[i+1])
                
                # Interseca il poligono del font con la cella
                cell_part = poly.intersection(cell_box)
                
                if cell_part and not cell_part.is_empty:
                    print(f"Cell [{i},{j}] using font {font_idx} - intersection success")
                    result_polygons.append(cell_part)
                else:
                    print(f"Cell [{i},{j}] using font {font_idx} - empty intersection")
    else:
        # Mixaggio orizzontale senza tagli verticali
        print(f"Creating horizontal slices with {len(h_cuts_real)+1} sections")
        print(f"Horizontal cuts: {h_cuts_real}")
        
        # Aggiungi i bordi
        all_h_cuts = [min_y] + h_cuts_real + [max_y]
        result_polygons = []
        
        # Per ogni sezione orizzontale...
        for i in range(len(all_h_cuts) - 1):
            # Seleziona il font da usare per questa sezione (in modo ciclico)
            font_idx = i % len(valid_polygons)
            poly = valid_polygons[font_idx]
            
            # Crea un rettangolo per questa sezione
            section_box = box(min_x, all_h_cuts[i], max_x, all_h_cuts[i+1])
            
            # Interseca il poligono del font con la sezione
            section_part = poly.intersection(section_box)
            
            if section_part and not section_part.is_empty:
                print(f"Section {i} using font {font_idx} - intersection success")
                result_polygons.append(section_part)
            else:
                print(f"Section {i} using font {font_idx} - empty intersection")
    
    # Unisci tutte le parti
    if result_polygons:
        result = unary_union(result_polygons)
        print(f"Final mixed polygon has bounds: {result.bounds}")
        return result
    
    # Fallback
    print("WARNING: Mixing failed, returning first valid polygon")
    return valid_polygons[0]


def mix_polygons_quadrants(polygons, x_cut, y_cut):
    """
    Mixa poligoni dividendoli in quattro quadranti.
    Prende un quadrante diverso da ogni font in modo pseudo-casuale.
    
    Args:
        polygons: Lista di poligoni Shapely
        x_cut: Punto di taglio orizzontale
        y_cut: Punto di taglio verticale
        
    Returns:
        Poligono Shapely risultante
    """
    print("mix_polygons_quadrants è deprecata, uso mix_fonts_deterministic")
    # Converti i punti di taglio in liste per la nuova funzione
    h_cuts = [y_cut]
    v_cuts = [x_cut]
    return mix_fonts_deterministic(polygons, h_cuts, v_cuts)


def assemble_letter_multiple_fonts(font_paths, glyph_name, h_cuts=None, v_cuts=None, normalize=True, cut_method="horizontal"):
    """
    Assembla un glifo da più font con diversi metodi di taglio.
    
    Args:
        font_paths: Lista di percorsi ai font
        glyph_name: Nome del glifo da assemblare (es. "A")
        h_cuts: Punti di taglio orizzontali (0-1 normalizzati)
        v_cuts: Punti di taglio verticali (0-1 normalizzati)
        normalize: Se True, normalizza le dimensioni dei glifi
        cut_method: Metodo di taglio ("horizontal", "checkerboard", "quadrants")
    
    Returns:
        Poligono Shapely assemblato
    """
    polygons = []
    
    # Verifica i parametri di input
    print(f"\n=== Assemblaggio lettera '{glyph_name}' con {len(font_paths)} font ===")
    print(f"Metodo di taglio: {cut_method}")
    print(f"Tagli orizzontali: {h_cuts}")
    print(f"Tagli verticali: {v_cuts}")
    
    # Converti i punti di taglio a coordinate interne (0-1000)
    normalized_h_cuts = [y * 1000 for y in h_cuts] if h_cuts else []
    normalized_v_cuts = [x * 1000 for x in v_cuts] if v_cuts else []
    
    # Leggi i contorni da ogni font
    for i, font_path in enumerate(font_paths):
        try:
            print(f"Lettura font {i+1}: {os.path.basename(font_path)}")
            font = TTFont(font_path)
            contours = get_glyph_contours(font, glyph_name)
            font.close()
            
            # Debug: mostra quanti contorni sono stati estratti
            print(f"  Font {i+1}: Estratti {len(contours)} contorni per '{glyph_name}'")
            
            # Converti contorni in poligono
            poly = None
            try:
                # Crea un poligono per ogni contorno e uniscili
                contour_polys = [polygon_from_contour(c) for c in contours if c and len(c) >= 3]
                # Filtra i poligoni nulli o vuoti
                valid_polys = [p for p in contour_polys if p and not p.is_empty]
                
                if valid_polys:
                    poly = unary_union(valid_polys)
                    print(f"  Poligono creato con bounds: {poly.bounds}")
                else:
                    print(f"  Nessun poligono valido creato dai contorni")
            except Exception as e:
                print(f"Errore nella conversione dei contorni in poligono: {str(e)}")
                traceback.print_exc()
                poly = None
                
            polygons.append(poly)
        except Exception as e:
            print(f"Errore nel leggere font {font_path}: {str(e)}")
            traceback.print_exc()
            polygons.append(None)
    
    # Filtriamo i poligoni nulli
    valid_polygons = [p for p in polygons if p and not p.is_empty]
    if not valid_polygons:
        print(f"Nessun poligono valido per il glifo '{glyph_name}'")
        return None
    
    print(f"Ottenuti {len(valid_polygons)} poligoni validi su {len(polygons)} totali")
    
    # Normalizza la dimensione dei glifi se richiesto
    if normalize:
        normalized_polygons = []
        for i, poly in enumerate(valid_polygons):
            normalized = normalize_glyph_polygon(poly, target_height=1000)
            if normalized and not normalized.is_empty:
                normalized_polygons.append(normalized)
                print(f"  Poligono {i+1} normalizzato con bounds: {normalized.bounds}")
            else:
                print(f"  Errore nella normalizzazione del poligono {i+1}")
        
        valid_polygons = normalized_polygons
        if not valid_polygons:
            print(f"Errore: tutti i poligoni sono stati persi durante la normalizzazione")
            return None
    
    # Usa il nuovo metodo di mixaggio deterministico
    use_vertical = cut_method == "checkerboard" or len(normalized_v_cuts) > 0
    
    print(f"Usando il nuovo metodo di mixaggio deterministico")
    print(f"Tagli orizzontali: {normalized_h_cuts}")
    print(f"Tagli verticali: {normalized_v_cuts if use_vertical else 'nessuno'}")
    
    result = mix_fonts_deterministic(
        valid_polygons,
        normalized_h_cuts,
        normalized_v_cuts if use_vertical else None
    )
    
    if result is None or result.is_empty:
        print(f"Avviso: mixaggio fallito per '{glyph_name}', uso il primo poligono valido")
        return valid_polygons[0]
    
    print(f"Mixaggio completato con successo per '{glyph_name}'")
    return result
    
import os


from fontTools.ttLib import TTFont