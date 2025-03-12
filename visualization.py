"""
Modulo per la visualizzazione dei glifi e dell'alfabeto.
Contiene widget personalizzati per la visualizzazione dei contorni.
"""

from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtGui import QPainter, QColor, QPen, QImage, QPainterPath, QTransform, QFont
from PyQt5.QtCore import Qt, QRectF, QPointF


class LetterPreviewWidget(QWidget):
    """
    Widget per la visualizzazione dell'anteprima di una singola lettera.
    Mostra il glifo con le linee di taglio.
    """
    def __init__(self, letter="A", parent=None):
        super().__init__(parent)
        self.letter = letter
        self.contours = []
        self.h_cut_lines = []  
        self.v_cut_lines = []  
        self.setMinimumSize(120, 150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def setContours(self, contours):
        """Imposta i contorni da visualizzare"""
        self.contours = contours
        self.update()
        
    def setCutLines(self, cut_points):
        """Imposta le linee di taglio orizzontali"""
        self.h_cut_lines = cut_points
        self.update()
    
    def setVerticalCutLines(self, cut_points):
        """Imposta le linee di taglio verticali"""
        self.v_cut_lines = cut_points
        self.update()
        
    def paintEvent(self, event):
        """
        Disegna il glifo e le linee di taglio.
        Gestisce anche il caso di contorni mancanti.
        """
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
            
        # Disegna le linee di taglio orizzontali
        painter.setPen(QPen(QColor(255, 0, 0, 160), 1, Qt.DashLine))
        for cut in self.h_cut_lines:
            # Normalizza il valore di cut da 0-1 a coordinate dello schermo
            # Nota: le coordinate dello schermo hanno l'origine in alto a sinistra
            y_pos = draw_rect.top() + (1.0 - cut) * draw_rect.height()
            painter.drawLine(
                QPointF(draw_rect.left(), y_pos),
                QPointF(draw_rect.right(), y_pos)
            )
            
        # Disegna le linee di taglio verticali
        painter.setPen(QPen(QColor(0, 0, 255, 160), 1, Qt.DashLine))
        for cut in self.v_cut_lines:
            # Normalizza il valore di cut da 0-1 a coordinate dello schermo
            x_pos = draw_rect.left() + cut * draw_rect.width()
            painter.drawLine(
                QPointF(x_pos, draw_rect.top()),
                QPointF(x_pos, draw_rect.bottom())
            )
            
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


class AlphabetPreviewWidget(QWidget):
    """
    Widget per la visualizzazione dell'anteprima dell'intero alfabeto.
    Mostra tutte le lettere in una griglia.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.letters_dict = {}  # {'A': contours, 'B': contours, ...}
        self.setMinimumSize(600, 200)
        
    def setLetters(self, letters_dict):
        """Imposta le lettere da visualizzare"""
        self.letters_dict = letters_dict
        self.update()
        
    def paintEvent(self, event):
        """
        Disegna una griglia di lettere.
        Ogni cella contiene una lettera dell'alfabeto.
        """
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
            
        # Dividi l'area in due sezioni: maiuscole e minuscole
        uppercase_rect = QRectF(0, 0, self.width(), self.height() / 2)
        lowercase_rect = QRectF(0, self.height() / 2, self.width(), self.height() / 2)
        
        # Disegna un separatore
        painter.setPen(QPen(Qt.lightGray, 1, Qt.DashLine))
        painter.drawLine(0, int(self.height() / 2), self.width(), int(self.height() / 2))
        
        # Calcola la disposizione delle lettere maiuscole
        uppercase_letters = [letter for letter in sorted(self.letters_dict.keys()) if letter.isupper()]
        num_uppercase = len(uppercase_letters)
        cols_uppercase = min(13, num_uppercase)  # Max 13 lettere per riga
        rows_uppercase = (num_uppercase + cols_uppercase - 1) // cols_uppercase
        
        cell_width_uppercase = uppercase_rect.width() / cols_uppercase
        cell_height_uppercase = uppercase_rect.height() / rows_uppercase
        
        # Disegna le lettere maiuscole
        self._draw_letters_section(painter, uppercase_rect, uppercase_letters, cols_uppercase)
        
        # Calcola la disposizione delle lettere minuscole
        lowercase_letters = [letter for letter in sorted(self.letters_dict.keys()) if letter.islower()]
        if lowercase_letters:  # Se ci sono lettere minuscole
            num_lowercase = len(lowercase_letters)
            cols_lowercase = min(13, num_lowercase)  # Max 13 lettere per riga
            
            # Disegna le lettere minuscole
            self._draw_letters_section(painter, lowercase_rect, lowercase_letters, cols_lowercase)
    
    def _draw_letters_section(self, painter, section_rect, letters, cols):
        """Helper per disegnare una sezione di lettere (maiuscole o minuscole)"""
        num_letters = len(letters)
        rows = (num_letters + cols - 1) // cols
        
        cell_width = section_rect.width() / cols
        cell_height = section_rect.height() / rows
        
        for i, letter in enumerate(letters):
            row = i // cols
            col = i % cols
            
            x = section_rect.x() + col * cell_width
            y = section_rect.y() + row * cell_height
            
            letter_rect = QRectF(x, y, cell_width, cell_height)
            
            painter.save()
            painter.setClipRect(letter_rect)
            
            contours = self.letters_dict[letter]
            if not contours:
                # Lettera vuota
                painter.setPen(Qt.lightGray)
                painter.drawRect(letter_rect.adjusted(2, 2, -2, -2))
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


def glyph_to_image(contours, width=200, height=200, padding=10):
    """
    Converte contorni di un glifo in un'immagine QImage.
    Utile per visualizzare i glifi in anteprima.
    
    Args:
        contours: Lista di contorni
        width: Larghezza dell'immagine
        height: Altezza dell'immagine
        padding: Padding attorno al glifo
        
    Returns:
        Oggetto QImage
    """
    # Crea un'immagine vuota se non ci sono contorni
    if not contours:
        image = QImage(width, height, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        return image
    
    # Calcola i limiti del glifo
    all_points = [pt for c in contours for pt in c]
    min_x = min(p[0] for p in all_points)
    max_x = max(p[0] for p in all_points)
    min_y = min(p[1] for p in all_points)
    max_y = max(p[1] for p in all_points)
    
    # Calcola dimensioni effettive
    glyph_width = max_x - min_x
    glyph_height = max_y - min_y
    
    # Crea l'immagine con canale alpha
    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # Calcola il fattore di scala mantenendo le proporzioni
    content_width = width - 2 * padding
    content_height = height - 2 * padding
    scale_x = content_width / glyph_width if glyph_width > 0 else 1
    scale_y = content_height / glyph_height if glyph_height > 0 else 1
    scale = min(scale_x, scale_y) * 0.95  # Lascia un piccolo margine
    
    # Crea una singola trasformazione affine combinata
    transform = QTransform()
    transform.translate(width/2, height/2)          # Centra nel widget
    transform.scale(scale, -scale)                  # Inverti l'asse Y
    transform.translate(
        -((min_x + max_x) / 2),                    # Centra orizzontalmente
        -((min_y + max_y) / 2)                     # Centra verticalmente
    )
    painter.setTransform(transform)
    
    # Configura penna e pennello
    pen = QPen(QColor(0, 0, 0, 200))               # Nero semi-trasparente
    pen.setWidthF(10.0 / scale)                    # Larghezza linea proporzionata
    painter.setPen(pen)
    painter.setBrush(QColor(0, 0, 0, 50))          # Riempimento trasparente
    
    # Crea un unico path per tutti i contorni
    path = QPainterPath()
    
    for contour in contours:
        if len(contour) < 2:
            continue
            
        # Inizia nuovo sottopath
        start_point = QPointF(contour[0][0], contour[0][1])
        path.moveTo(start_point)
        
        # Aggiungi tutti i punti del contorno
        for x, y in contour[1:]:
            path.lineTo(x, y)
            
        # Chiudi il contorno se necessario
        if contour[0] != contour[-1]:
            path.lineTo(contour[0][0], contour[0][1])
            
        path.closeSubpath()
    
    # Disegna tutto in una singola operazione
    painter.drawPath(path)
    painter.end()
    
    return image