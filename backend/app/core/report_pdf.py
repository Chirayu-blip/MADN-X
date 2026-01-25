from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from datetime import datetime
import json

def generate_pdf_report(patient_case: dict, agent_outputs: dict, consensus: dict, file_path: str):
    """
    Creates a clinical-style PDF report.
    """

    doc = SimpleDocTemplate(file_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>MADN-X Diagnostic Report</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>Patient Input Summary</b>", styles["Heading2"]))
    story.append(Paragraph(json.dumps(patient_case, indent=2), styles["Code"]))
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>Agent Outputs</b>", styles["Heading2"]))
    for agent, out in agent_outputs.items():
        story.append(Paragraph(f"<b>{agent}</b>", styles["Heading3"]))
        story.append(Paragraph(json.dumps(out, indent=2), styles["Code"]))
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Final Consensus Diagnosis</b>", styles["Heading2"]))
    story.append(Paragraph(json.dumps(consensus, indent=2), styles["Code"]))

    doc.build(story)
    return file_path
