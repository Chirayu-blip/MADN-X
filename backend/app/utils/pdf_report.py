# app/utils/pdf_report.py
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import os
from typing import Dict, Any

def _kv_table(title: str, pairs: Dict[str, Any]):
    data = [["Field", "Value"]]
    for k, v in pairs.items():
        data.append([str(k), str(v)])
    t = Table(data, colWidths=[120, 360])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f0f3f7")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 10),
        ("INNERGRID", (0,0), (-1,-1), 0.25, colors.HexColor("#d5dbe3")),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#ccd3db")),
        ("BACKGROUND", (0,1), (-1,-1), colors.white),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    return [Paragraph(f"<b>{title}</b>", getSampleStyleSheet()["Heading4"]), Spacer(1, 6), t, Spacer(1, 10)]

def generate_pdf_report(
    out_path: str,
    *,
    case_id: str,
    patient_case: Dict[str, Any],
    consensus: Dict[str, Any],
    agents: Dict[str, Any],
):
    """
    out_path: full path to write (e.g. 'reports/report_x.pdf')
    case_id: your identifier
    patient_case: dict with radiology/ecg/symptoms_text/lab_text
    consensus: { 'diagnoses': {label: prob}, 'top': str, 'rationale': [..] or str }
    agents: { 'radiologist': {...}, 'cardiologist': {...}, ... } (strings or dicts ok)
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    styles = getSampleStyleSheet()
    title = Paragraph("MADN-X — Easy Read Report", styles["Title"])
    sub = Paragraph(f"Case ID: {case_id}", styles["Heading2"])
    intro = Paragraph(
        "This report summarizes multiple specialist AIs working together. "
        "It is written for non-medical readers. Any uncertain cases should be reviewed by a clinician.",
        ParagraphStyle("intro", parent=styles["BodyText"], leading=14)
    )

    story = [title, Spacer(1, 6), sub, Spacer(1, 12), intro, Spacer(1, 16)]

    # Section: Inputs (plain language)
    inputs_show = {
        "Radiology note": (patient_case or {}).get("radiology", "") or "—",
        "ECG note": (patient_case or {}).get("ecg", "") or "—",
        "Symptoms": (patient_case or {}).get("symptoms_text", "") or "—",
        "Lab summary": (patient_case or {}).get("lab_text", "") or "—",
    }
    story += _kv_table("What information was considered?", inputs_show)

    # Section: Consensus
    cons = consensus or {}
    diag_dict = cons.get("diagnoses", {}) or {}
    top = cons.get("top") or cons.get("top_diagnosis") or "—"
    rationale = cons.get("rationale", [])
    if isinstance(rationale, (list, tuple)):
        rationale = "; ".join(map(str, rationale))
    consensus_pairs = {"Top diagnosis": top}
    for k, v in diag_dict.items():
        consensus_pairs[f"Probability — {k}"] = f"{float(v):.2f}"
    if rationale:
        consensus_pairs["Why (short)"] = rationale
    story += _kv_table("Overall conclusion", consensus_pairs)

    # Section: Agent Snapshots (short & simple)
    story.append(Paragraph("<b>Specialist snapshots</b>", styles["Heading4"]))
    story.append(Spacer(1, 6))
    for name, rep in (agents or {}).items():
        # rep can be string (JSON) or dict
        if isinstance(rep, dict):
            expl = rep.get("explanation") or rep.get("explanations") or ""
            top_d = rep.get("top_diagnosis") or rep.get("top") or ""
            conf = rep.get("confidence")
        else:
            # fall back to string display
            expl = str(rep)[:700]
            top_d, conf = "", None
        pairs = {
            "Agent": name.capitalize(),
            "Top finding": top_d or "—",
            "Confidence": f"{float(conf):.2f}" if isinstance(conf, (int, float)) else "—",
            "Short note": expl or "—",
        }
        story += _kv_table("", pairs)

    doc = SimpleDocTemplate(out_path, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    doc.build(story)
