"""
Enterprise PDF Audit Report Generator
Generates executive-ready vendor risk audit certificates using ReportLab.
"""
import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

def generate_pdf_report(
    vendor_name: str,
    scorecard: dict,
    checklist: list,
    human_reviewer: str = "Lead Information Security Officer",
    decision: str = "Approved",
    comments: str = "",
    mcp_actions: list = None,
    output_path: str = None
) -> bytes:
    """
    Builds a professional executive audit report in PDF format.
    Returns the PDF file bytes and optionally writes to output_path.
    """
    buffer = io.BytesIO()
    doc_target = output_path if output_path else buffer
    
    doc = SimpleDocTemplate(
        doc_target,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#64748B'),
        alignment=TA_LEFT
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1E293B'),
        fontName='Helvetica-Bold',
        spaceBefore=10,
        spaceAfter=5
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    badge_style = ParagraphStyle(
        'Badge_Custom',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("OFFICIAL VENDOR RISK AUDIT REPORT", title_style))
    story.append(Spacer(1, 3))
    date_str = datetime.now().strftime("%B %d, %Y - %H:%M:%S UTC")
    clean_vendor = vendor_name.replace("_", " ").title()
    story.append(Paragraph(f"Target Vendor: <b>{clean_vendor}</b> &nbsp;|&nbsp; Generated on: {date_str}", subtitle_style))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2563EB'), spaceBefore=2, spaceAfter=10))

    # 2. Executive Summary Metrics Bar
    overall_risk = scorecard.get("overall_risk", "UNKNOWN")
    risk_score = scorecard.get("risk_score_numeric", 0)
    pass_cnt = scorecard.get("pass_count", 0)
    fail_cnt = scorecard.get("fail_count", 0)
    review_cnt = scorecard.get("review_count", 0)

    risk_hex = '#991B1B' if overall_risk == "HIGH" else ('#D97706' if overall_risk == "MEDIUM" else '#16A34A')

    summary_data = [
        [
            Paragraph(f"<b>Overall Risk</b><br/><font size='12' color='{risk_hex}'><b>{overall_risk}</b></font>", badge_style),
            Paragraph(f"<b>Risk Score</b><br/><font size='12'><b>{risk_score}/100</b></font>", badge_style),
            Paragraph(f"<b>Standards Passed</b><br/><font size='12' color='#16A34A'><b>{pass_cnt}/{len(checklist)}</b></font>", badge_style),
            Paragraph(f"<b>Violations</b><br/><font size='12' color='#DC2626'><b>{fail_cnt}</b></font>", badge_style),
            Paragraph(f"<b>Needs Legal Review</b><br/><font size='12' color='#D97706'><b>{review_cnt}</b></font>", badge_style)
        ]
    ]
    summary_table = Table(summary_data, colWidths=[108, 108, 108, 108, 108])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8))

    # Executive Summary Text
    exec_summary = scorecard.get("executive_summary", "")
    if exec_summary:
        story.append(Paragraph(f"<b>Executive Summary:</b> {exec_summary}", body_style))
        story.append(Spacer(1, 10))

    # 3. Compliance Matrix Table
    story.append(Paragraph("Detailed Security Compliance Matrix", h2_style))
    story.append(Spacer(1, 4))

    table_data = [
        [
            Paragraph("<b>Security Standard</b>", body_style),
            Paragraph("<b>Status</b>", badge_style),
            Paragraph("<b>Conf.</b>", badge_style),
            Paragraph("<b>Evaluation & Verbatim Evidence</b>", body_style)
        ]
    ]

    for item in checklist:
        st_val = item.get("status", "REVIEW")
        if st_val == "PASS":
            c_text = "<font color='#166534'><b>PASS</b></font>"
        elif st_val == "FAIL":
            c_text = "<font color='#991B1B'><b>FAIL</b></font>"
        else:
            c_text = "<font color='#B45309'><b>REVIEW</b></font>"

        cat_cell = Paragraph(f"<b>{item.get('category', '')}</b><br/><font color='#64748B' size='7'>{item.get('policy_requirement', '')}</font>", body_style)
        stat_cell = Paragraph(c_text, badge_style)
        conf_cell = Paragraph(f"{int(item.get('confidence', 0)*100)}%", badge_style)
        
        evidence_snippet = item.get('evidence', '').replace("\n", " ").strip()
        if len(evidence_snippet) > 160:
            evidence_snippet = evidence_snippet[:160] + "..."
        
        evidence_clean = evidence_snippet.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
        reasoning_clean = item.get('reasoning', '').replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")

        detail_cell = Paragraph(
            f"<b>Finding:</b> {reasoning_clean}<br/>"
            f"<b>Evidence:</b> <i>\"{evidence_clean}\"</i>",
            body_style
        )

        table_data.append([cat_cell, stat_cell, conf_cell, detail_cell])

    comp_table = Table(table_data, colWidths=[120, 50, 45, 325])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (1,0), (2,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 10))

    # 4. Human-in-the-Loop Sign-off Box
    story.append(Paragraph("Human-in-the-Loop Verification & Sign-off", h2_style))
    story.append(Spacer(1, 3))
    
    clean_notes = comments if comments else "Reviewed automated LangGraph compliance matrix. Actions authorized."
    hitl_data = [
        [
            Paragraph(f"<b>Authorized Security Officer:</b> {human_reviewer}", body_style),
            Paragraph(f"<b>Final Decision:</b> <b>{decision}</b>", body_style)
        ],
        [
            Paragraph(f"<b>Reviewer Notes:</b> {clean_notes}", body_style),
            Paragraph(f"<b>Audit Signature Hash:</b> <code>SEC-HITL-{datetime.now().strftime('%Y%m%d-%H%M%S')}</code>", body_style)
        ]
    ]
    hitl_table = Table(hitl_data, colWidths=[270, 270])
    hitl_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(hitl_table)

    # 5. MCP Tool Execution Trail
    if mcp_actions:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Model Context Protocol (MCP) Executed Tool Actions", h2_style))
        story.append(Spacer(1, 3))
        mcp_rows = [
            [Paragraph("<b>MCP Tool</b>", body_style), Paragraph("<b>Status</b>", badge_style), Paragraph("<b>Artifact / Result Details</b>", body_style)]
        ]
        for act in mcp_actions:
            tool_name = act.get("tool", "")
            res = act.get("result", {})
            status = res.get("status", "SUCCESS")
            detail = res.get("ticket_id") or res.get("file_path") or res.get("channel") or str(res)
            mcp_rows.append([
                Paragraph(f"<code>{tool_name}</code>", body_style),
                Paragraph(f"<font color='#16A34A'><b>{status}</b></font>", badge_style),
                Paragraph(str(detail), body_style)
            ])
        mcp_table = Table(mcp_rows, colWidths=[140, 70, 330])
        mcp_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(mcp_table)

    doc.build(story)
    
    if output_path:
        with open(output_path, "rb") as f:
            return f.read()
    else:
        buffer.seek(0)
        return buffer.getvalue()
