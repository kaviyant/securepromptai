import io
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class ReportService:
    @staticmethod
    async def generate_json_report(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
        """
        Gathers high-level stats and list of warnings/blocks to form a JSON compliance report.
        """
        # Fetch stats
        stats_pipeline = [
            {
                "$group": {
                    "_id": "$action",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        actions = {"ALLOW": 0, "WARN": 0, "BLOCK": 0}
        cursor = db.prompts_history.aggregate(stats_pipeline)
        async for doc in cursor:
            action_name = doc["_id"]
            if action_name in actions:
                actions[action_name] = doc["count"]

        # Fetch latest 50 security violations
        violations_cursor = db.prompts_history.find(
            {"action": {"$in": ["WARN", "BLOCK"]}}
        ).sort("timestamp", -1).limit(50)
        
        violations_list = []
        async for doc in violations_cursor:
            violations_list.append({
                "timestamp": doc["timestamp"].isoformat() if isinstance(doc["timestamp"], datetime) else str(doc["timestamp"]),
                "username": doc["username"],
                "department": doc["department"],
                "website": doc["website"],
                "risk_score": doc["riskScore"],
                "risk_level": doc["riskLevel"],
                "action": doc["action"],
                "reason": doc["reason"],
                "flagged_terms": doc["flaggedTerms"]
            })

        return {
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_scans": sum(actions.values()),
                "allowed_count": actions["ALLOW"],
                "warnings_count": actions["WARN"],
                "blocked_count": actions["BLOCK"],
                "compliance_ratio": f"{(actions['ALLOW'] / max(1, sum(actions.values()))) * 100:.2f}%"
            },
            "recent_violations": violations_list
        }

    @classmethod
    async def generate_pdf_report(db: AsyncIOMotorDatabase, request_user: str) -> io.BytesIO:
        """
        Compiles audit data and writes a stylized PDF file using ReportLab platypus layouts.
        """
        # 1. Fetch Summary Stats
        total_scans = await db.prompts_history.count_documents({})
        allowed = await db.prompts_history.count_documents({"action": "ALLOW"})
        warned = await db.prompts_history.count_documents({"action": "WARN"})
        blocked = await db.prompts_history.count_documents({"action": "BLOCK"})

        # Fetch latest 15 blocked or warned records
        cursor = db.prompts_history.find(
            {"action": {"$in": ["WARN", "BLOCK"]}}
        ).sort("timestamp", -1).limit(15)

        violations = []
        async for doc in cursor:
            violations.append(doc)

        # 2. Build PDF Document in Buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()
        
        # Modify default styles for sleek visual hierarchy
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=6
        )
        
        meta_style = ParagraphStyle(
            'ReportMeta',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=24
        )

        heading_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor=colors.HexColor('#1E293B'),
            spaceBefore=14,
            spaceAfter=8
        )

        cell_text_style = ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor('#334155'),
            leading=11
        )

        cell_hdr_style = ParagraphStyle(
            'CellHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=colors.white
        )

        story = []

        # Header Block
        story.append(Paragraph("SecurePrompt AI - Security Compliance Audit", title_style))
        gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        story.append(Paragraph(f"Report generated: {gen_time} | Requestor: {request_user}", meta_style))

        # Metrics Card Table Layout
        story.append(Paragraph("Executive Compliance Summary", heading_style))
        
        metrics_data = [
            [
                Paragraph("<b>Total Scans</b>", cell_text_style), 
                Paragraph("<b>Allowed</b>", cell_text_style), 
                Paragraph("<b>Warnings</b>", cell_text_style), 
                Paragraph("<b>Blocked</b>", cell_text_style)
            ],
            [
                str(total_scans), 
                str(allowed), 
                str(warned), 
                str(blocked)
            ]
        ]
        
        metrics_table = Table(metrics_data, colWidths=[130, 130, 130, 130])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('FONTSIZE', (0,1), (-1,1), 16),
            ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 15))

        # Incidents List Table
        story.append(Paragraph("Recent Intercepted Incidents (Warnings & Blocks)", heading_style))
        
        table_data = [[
            Paragraph("Timestamp", cell_hdr_style),
            Paragraph("User", cell_hdr_style),
            Paragraph("AI Portal", cell_hdr_style),
            Paragraph("Verdict", cell_hdr_style),
            Paragraph("Risk", cell_hdr_style),
            Paragraph("Flagged Category / Reason", cell_hdr_style)
        ]]

        for record in violations:
            ts = record["timestamp"].strftime("%m-%d %H:%M") if isinstance(record["timestamp"], datetime) else str(record["timestamp"])
            user = record["username"]
            site = record["siteKey"]
            verdict = record["action"]
            score = f"{record['riskScore']}/100"
            reason = record["reason"] or record["category"]
            
            table_data.append([
                Paragraph(ts, cell_text_style),
                Paragraph(user, cell_text_style),
                Paragraph(site, cell_text_style),
                Paragraph(verdict, cell_text_style),
                Paragraph(score, cell_text_style),
                Paragraph(reason, cell_text_style)
            ])

        incidents_table = Table(table_data, colWidths=[70, 75, 75, 60, 50, 210])
        incidents_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAF5')]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
        ]))
        
        story.append(incidents_table)
        
        # Build Document
        doc.build(story)
        buffer.seek(0)
        return buffer
