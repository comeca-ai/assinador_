"""Embed ReportLab's bundled Vera fonts so PDF output is portable."""
from pathlib import Path
import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

font_dir=Path(reportlab.__file__).parent/'fonts'
pdfmetrics.registerFont(TTFont('AssinaSans',str(font_dir/'Vera.ttf')))
pdfmetrics.registerFont(TTFont('AssinaSans-Bold',str(font_dir/'VeraBd.ttf')))
pdfmetrics.registerFontFamily('AssinaSans',normal='AssinaSans',bold='AssinaSans-Bold',italic='AssinaSans',boldItalic='AssinaSans-Bold')

def styles_with_fonts():
    from reportlab.lib.styles import getSampleStyleSheet
    styles=getSampleStyleSheet()
    for name in styles.byName:
        styles[name].fontName='AssinaSans-Bold' if name.startswith('Heading') or name=='Title' else 'AssinaSans'
    return styles
