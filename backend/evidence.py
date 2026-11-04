"""Produces test artifacts only. No cryptographic PDF signing or ICP-Brasil."""
import io
from html import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from pypdf import PdfReader, PdfWriter
from .security import TERMS, TERMS_VERSION
from .fonts import styles_with_fonts

LABEL='HOMOLOGAÇÃO - NÃO É ASSINATURA ICP-BRASIL'

def report_pdf(envelope, signers, chain_head):
    output=io.BytesIO()
    doc=SimpleDocTemplate(output,pagesize=A4,rightMargin=44,leftMargin=44,topMargin=50,bottomMargin=50)
    styles=styles_with_fonts()
    styles['Title'].textColor=colors.HexColor('#102542')
    styles['BodyText'].leading=16
    story=[]
    def para(text,style='BodyText'):
        story.append(Paragraph(escape(str(text)),styles[style]));story.append(Spacer(1,12))
    para('Assina Brasil | Relatório de teste','Title')
    para(LABEL,'Heading2')
    para('Não homologado para uso jurídico. Este relatório registra intenções autodeclaradas em ambiente de teste. Não certifica identidade, não contém PAdES ou carimbo de tempo confiável.')
    para(envelope['title'],'Heading2')
    para('Envelope: '+envelope['id'])
    para('SHA-256 do original: '+envelope['original_sha256'])
    para('Cabeça da cadeia no registro da conclusão: '+chain_head)
    for signer in signers:
        para('Participante '+str(signer['position']),'Heading2')
        para('Nome autodeclarado: '+(signer['declared_name'] or ''))
        para('Confirmação registrada (UTC): '+(signer['confirmed_at'] or ''))
    para('Consentimento: '+TERMS_VERSION,'Heading2')
    para(TERMS)
    para('O PDF original permanece preservado em armazenamento privado. Este arquivo é uma cópia com marca de homologação e relatório. Verifique hashes e cadeia com o manifesto JSON. SHA-256 não demonstra identidade ou autoridade de tempo.')
    def footer(canvas,doc):
        canvas.setFont('AssinaSans',8);canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(44,28,'Assina Brasil | Homologação | Página '+str(doc.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()

def final_pdf(original,envelope,signers,chain_head):
    writer=PdfWriter()
    for page in PdfReader(io.BytesIO(original)).pages:
        # Every copied page visibly states it is a test artifact.
        from reportlab.pdfgen import canvas
        writer.add_page(page)
        page=writer.pages[-1]
        overlay=io.BytesIO()
        c=canvas.Canvas(overlay,pagesize=(float(page.mediabox.width),float(page.mediabox.height)))
        c.setFillColor(colors.HexColor('#fff3cd'))
        c.rect(0,float(page.mediabox.height)-30,float(page.mediabox.width),30,fill=1,stroke=0)
        c.setFillColor(colors.HexColor('#7a4e00'));c.setFont('AssinaSans-Bold',9)
        c.drawString(12,float(page.mediabox.height)-19,'HOMOLOGACAO - NAO HOMOLOGADO PARA USO JURIDICO - SEM ICP-BRASIL')
        c.save();overlay.seek(0)
        page.merge_page(PdfReader(overlay).pages[0])
    writer.append(io.BytesIO(report_pdf(envelope,signers,chain_head)))
    writer.add_metadata({'/Title':'Assina Brasil - artefato de homologação','/Subject':LABEL})
    output=io.BytesIO();writer.write(output)
    return output.getvalue()
