"""Creates a conspicuously fictitious, portable PDF for local homologation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from backend.fonts import styles_with_fonts

root=Path(__file__).resolve().parents[1]
def create():
    styles=styles_with_fonts();styles['Title'].textColor=colors.HexColor('#102542');styles['BodyText'].leading=17
    story=[Paragraph('Assina Brasil',styles['Title']),Paragraph('DOCUMENTO FICTÍCIO PARA HOMOLOGAÇÃO',styles['Heading2']),Spacer(1,24),Paragraph('Termo de teste da plataforma',styles['Heading1']),Spacer(1,14)]
    for text in ['Este documento foi criado exclusivamente para testar o fluxo do Assina Brasil. Não representa contrato, obrigação ou declaração de pessoa real.', '1. Revise este PDF na interface do participante.', '2. Leia o consentimento de homologação apresentado na tela.', '3. Registre uma intenção fictícia e examine o relatório gerado.', 'O fluxo não verifica identidade nem produz assinatura ICP-Brasil.', 'O original deve permanecer intacto, com seu hash SHA-256 preservado. A cópia final de teste recebe marca de homologação e relatório.', 'Nenhum dado real ou sensível deve ser inserido neste ambiente.']:
        story.extend([Paragraph(text,styles['BodyText']),Spacer(1,17)])
    box=Table([[Paragraph('HOMOLOGAÇÃO - SEM EFEITO JURÍDICO',styles['Heading3'])],[Paragraph('Não é assinatura digital, certificado ou carimbo de tempo confiável.',styles['BodyText'])]],colWidths=[475])
    box.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#fff3d8')),('LEFTPADDING',(0,0),(-1,-1),16),('RIGHTPADDING',(0,0),(-1,-1),16),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12)]));story.extend([Spacer(1,15),box])
    def footer(c,d):c.setFont('AssinaSans',8);c.setFillColor(colors.HexColor('#67778e'));c.drawString(44,30,'Assina Brasil | Exemplo fictício | Novembro de 2026')
    SimpleDocTemplate(str(root/'examples/exemplo-ficticio.pdf'),pagesize=A4,leftMargin=50,rightMargin=50,topMargin=65,bottomMargin=50).build(story,onFirstPage=footer)
if __name__=='__main__':create()
