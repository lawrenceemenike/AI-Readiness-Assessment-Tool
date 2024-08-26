from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO

def generate_pdf_report(assessment):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("AI Readiness Assessment Report", styles['Title']))
    elements.append(Spacer(1, 12))

    # Summary
    elements.append(Paragraph("Summary", styles['Heading1']))
    elements.append(Paragraph(f"Total Score: {assessment.total_score}", styles['Normal']))
    elements.append(Paragraph(f"Readiness Level: {assessment.readiness_level}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Scores Table
    data = [
        ["Category", "Score"],
        ["Strategy", assessment.strategy_score],
        ["Governance", assessment.governance_score],
        ["Data & Infrastructure", assessment.data_infrastructure_score],
        ["Organization", assessment.organization_score]
    ]
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    # Recommendations
    elements.append(Paragraph("Recommendations", styles['Heading1']))
    if assessment.strategy_score < 15:
        elements.append(Paragraph("• Focus on developing a comprehensive AI strategy aligned with business goals.", styles['Normal']))
    if assessment.governance_score < 13:
        elements.append(Paragraph("• Strengthen AI governance frameworks and ethical guidelines.", styles['Normal']))
    if assessment.data_infrastructure_score < 16:
        elements.append(Paragraph("• Invest in improving data quality and infrastructure to support AI initiatives.", styles['Normal']))
    if assessment.organization_score < 13:
        elements.append(Paragraph("• Enhance AI skills and promote a culture of innovation within the organization.", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return buffer