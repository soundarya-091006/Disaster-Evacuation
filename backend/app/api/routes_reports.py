"""
TwinEvac - Incident Reporting & Export Endpoints
Generates formal PDF and JSON evacuation strategy audits for Disaster Management Authorities.
"""

import io
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import Response, JSONResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.engine.rolling_optimizer import rolling_optimizer

router = APIRouter(prefix="/reports", tags=["Reporting & Export"])


@router.get("/export-json")
def export_json_report():
    """Generates comprehensive JSON audit snapshot of the current Digital Twin state."""
    state = rolling_optimizer.sim.get_current_state()
    return JSONResponse(
        content={
            "report_metadata": {
                "system": "TwinEvac Digital Twin SaaS",
                "generated_at": datetime.now().isoformat(),
                "jurisdiction": "Salem District Disaster Management Authority",
                "sim_minute": state.elapsed_sim_minutes
            },
            "summary_metrics": {
                "total_at_risk_population": state.total_at_risk_population,
                "total_evacuated": state.total_evacuated,
                "total_in_transit": state.total_in_transit,
                "clearance_percentage": state.evacuation_progress_pct,
                "estimated_evacuation_time_min": state.estimated_evacuation_time_minutes,
                "active_bottlenecks": state.active_bottlenecks_count,
                "average_speed_kmh": state.average_network_speed_kmh
            },
            "shelters": [s.model_dump() for s in state.shelters],
            "predictions_horizon": {k: v.model_dump() for k, v in state.predictions.items()},
            "active_advisories": [a.model_dump() for a in state.advisories]
        }
    )


@router.get("/export-pdf")
def export_pdf_report():
    """Generates official formatted PDF Evacuation Operations Audit Report."""
    state = rolling_optimizer.sim.get_current_state()
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
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
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=14
    )
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155")
    )

    elements = []

    # Title & Metadata
    elements.append(Paragraph("TWINEVAC — EMERGENCY EVACUATION AUDIT", title_style))
    elements.append(Paragraph(
        f"Jurisdiction: Salem Urban District Command | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Elapsed Sim Time: {state.elapsed_sim_minutes:.1f} mins",
        subtitle_style
    ))
    elements.append(Spacer(1, 8))

    # Executive Summary Table
    elements.append(Paragraph("1. Macro Evacuation Telemetry", h2_style))
    summary_data = [
        ["Metric", "Value", "Metric", "Value"],
        ["Total At-Risk Pop", f"{state.total_at_risk_population:,}", "Cleared Pop", f"{state.total_evacuated:,}"],
        ["Evacuees In-Transit", f"{state.total_in_transit:,}", "Clearance Rate", f"{state.evacuation_progress_pct:.1f}%"],
        ["Est. Evacuation Time", f"{state.estimated_evacuation_time_minutes:.1f} min", "Avg Corridor Speed", f"{state.average_network_speed_kmh} km/h"],
        ["Active Bottlenecks", f"{state.active_bottlenecks_count}", "Active Scenario", state.active_scenario.title if state.active_scenario else "Baseline Operations"]
    ]
    t_summary = Table(summary_data, colWidths=[130, 130, 130, 140])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 10))

    # Shelter Occupancy Table
    elements.append(Paragraph("2. Shelter & Quarantine Facility Status", h2_style))
    shelter_rows = [["Facility Name", "Type", "Occupied / Total", "Fill %", "Quarantine Beds"]]
    for s in state.shelters:
        shelter_rows.append([
            s.name[:32],
            s.type.replace("_", " ").title(),
            f"{s.occupied} / {s.total_capacity}",
            f"{s.occupancy_pct:.1f}%",
            f"{s.quarantine_beds_occupied} / {s.quarantine_beds_total}"
        ])
    t_shelter = Table(shelter_rows, colWidths=[180, 100, 110, 60, 80])
    t_shelter.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f766e")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#f0fdfa"), colors.white]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_shelter)
    elements.append(Spacer(1, 10))

    # Forward Horizon Predictions Table
    elements.append(Paragraph("3. Predictive Horizons (15m / 30m / 60m)", h2_style))
    pred_rows = [["Horizon", "Congested Roads", "Avg Speed (km/h)", "Congestion Index", "Model Confidence"]]
    for h_key, h_data in state.predictions.items():
        pred_rows.append([
            f"+{h_data.horizon_minutes} Minutes",
            str(h_data.predicted_congested_road_count),
            f"{h_data.predicted_average_speed_kmh} km/h",
            f"{h_data.predicted_network_congestion_pct:.1f}%",
            f"{h_data.confidence_pct:.1f}%"
        ])
    t_pred = Table(pred_rows, colWidths=[100, 110, 110, 110, 100])
    t_pred.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_pred)
    elements.append(Spacer(1, 10))

    # Tactical Advisories
    elements.append(Paragraph("4. Automated AI Tactical Advisories", h2_style))
    if state.advisories:
        for adv in state.advisories[:3]:
            elements.append(Paragraph(f"<b>[{adv.severity}] {adv.title}:</b> {adv.message} <i>(Recommended Action: {adv.recommended_action})</i>", body_style))
            elements.append(Spacer(1, 3))
    else:
        elements.append(Paragraph("No critical tactical advisories at this timestamp. Traffic flowing under acceptable impedance thresholds.", body_style))

    doc.build(elements)
    buffer.seek(0)
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=TwinEvac_Audit_Report_{int(datetime.now().timestamp())}.pdf"}
    )
