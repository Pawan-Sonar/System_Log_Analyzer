"""Logs, analytics, alerts, reports, MITRE, geo API routers."""
from __future__ import annotations
import io
import csv
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query
from fastapi.responses import StreamingResponse, Response
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

from auth import get_current_user
import analytics
import log_parser
import geo
from mitre_data import TACTICS

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# ============== LOGS ==============
logs_router = APIRouter(prefix="/logs", tags=["logs"])


@logs_router.post("/upload")
async def upload_logs(request: Request, file: UploadFile = File(...), user=Depends(get_current_user)):
    db = request.app.state.db
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    name_lc = file.filename.lower()
    if not any(name_lc.endswith(ext) for ext in (".csv", ".json", ".txt", ".log")):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV, JSON, or TXT.")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")
    parsed = log_parser.parse(file.filename, content)
    if not parsed:
        raise HTTPException(status_code=400, detail="No valid log entries found")

    upload_id = secrets.token_hex(8)
    now = datetime.now(timezone.utc).isoformat()
    docs = []
    for p in parsed:
        docs.append({
            "id": secrets.token_hex(12),
            "user_id": user["id"],
            "timestamp": p["timestamp"],
            "ip_address": p["ip_address"],
            "username": p["username"],
            "event_type": p["event_type"],
            "status": p["status"],
            "risk_score": 0,
            "upload_id": upload_id,
            "created_at": now,
        })
    if docs:
        await db.logs.insert_many(docs)

    # Run analytics & persist alerts for this batch
    findings = analytics.detect(docs)
    alerts = []
    for a in findings.get("alerts", []):
        alerts.append({
            "id": secrets.token_hex(12),
            "user_id": user["id"],
            "type": a["type"],
            "severity": a["severity"],
            "message": a["message"],
            "ip_address": a.get("ip_address"),
            "username": a.get("username"),
            "mitre_id": a.get("mitre_id"),
            "timestamp": now,
            "acknowledged": False,
            "upload_id": upload_id,
        })
    if alerts:
        await db.alerts.insert_many(alerts)

    return {
        "upload_id": upload_id,
        "inserted": len(docs),
        "alerts_created": len(alerts),
        "risk_score": findings.get("risk_score", 0),
        "risk_level": findings.get("risk_level", "low"),
    }


@logs_router.get("")
async def list_logs(
    request: Request,
    user=Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    ip: Optional[str] = None,
    username: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    db = request.app.state.db
    q: dict = {"user_id": user["id"]}
    if event_type:
        q["event_type"] = event_type
    if status:
        q["status"] = status
    if ip:
        q["ip_address"] = {"$regex": ip, "$options": "i"}
    if username:
        q["username"] = {"$regex": username, "$options": "i"}
    if start or end:
        ts: dict = {}
        if start:
            ts["$gte"] = start
        if end:
            ts["$lte"] = end
        q["timestamp"] = ts
    total = await db.logs.count_documents(q)
    cursor = db.logs.find(q, {"_id": 0}).sort("timestamp", -1).skip((page - 1) * page_size).limit(page_size)
    items = await cursor.to_list(length=page_size)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@logs_router.get("/by-ip/{ip}")
async def logs_by_ip(ip: str, request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    cursor = db.logs.find({"user_id": user["id"], "ip_address": ip}, {"_id": 0}).sort("timestamp", -1).limit(500)
    items = await cursor.to_list(length=500)
    geo_info = await geo.lookup(ip)
    return {"ip": ip, "geo": geo_info, "items": items, "total": len(items)}


@logs_router.delete("")
async def clear_logs(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    r1 = await db.logs.delete_many({"user_id": user["id"]})
    r2 = await db.alerts.delete_many({"user_id": user["id"]})
    return {"logs_deleted": r1.deleted_count, "alerts_deleted": r2.deleted_count}


@logs_router.post("/seed-demo")
async def seed_demo(request: Request, user=Depends(get_current_user)):
    """Seed a demo set of logs so the dashboard is immediately useful."""
    import random
    db = request.app.state.db
    now = datetime.now(timezone.utc)
    upload_id = secrets.token_hex(8)
    docs = []
    users = ["alice", "bob", "charlie", "diana", "eve", "frank", "grace"]
    normal_ips = [f"10.0.0.{i}" for i in range(2, 25)]
    bad_ip = "185.220.101.42"
    bad_ip2 = "45.155.205.233"
    # Successful normal traffic
    for i in range(120):
        ts = now.timestamp() - random.randint(0, 86400 * 3)
        docs.append({
            "id": secrets.token_hex(12), "user_id": user["id"],
            "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            "ip_address": random.choice(normal_ips),
            "username": random.choice(users),
            "event_type": "login", "status": "success",
            "risk_score": 0, "upload_id": upload_id,
        })
    # Logouts
    for i in range(80):
        ts = now.timestamp() - random.randint(0, 86400 * 3)
        docs.append({
            "id": secrets.token_hex(12), "user_id": user["id"],
            "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            "ip_address": random.choice(normal_ips),
            "username": random.choice(users),
            "event_type": "logout", "status": "success",
            "risk_score": 0, "upload_id": upload_id,
        })
    # Brute force from bad_ip (35 failures)
    base_ts = now.timestamp() - 3600
    for i in range(35):
        docs.append({
            "id": secrets.token_hex(12), "user_id": user["id"],
            "timestamp": datetime.fromtimestamp(base_ts + i * 15, tz=timezone.utc).isoformat(),
            "ip_address": bad_ip,
            "username": random.choice(users),
            "event_type": "failed_login", "status": "failure",
            "risk_score": 0, "upload_id": upload_id,
        })
    # Burst against single user
    base_ts2 = now.timestamp() - 7200
    for i in range(12):
        docs.append({
            "id": secrets.token_hex(12), "user_id": user["id"],
            "timestamp": datetime.fromtimestamp(base_ts2 + i * 40, tz=timezone.utc).isoformat(),
            "ip_address": bad_ip2,
            "username": "diana",
            "event_type": "failed_login", "status": "failure",
            "risk_score": 0, "upload_id": upload_id,
        })
    # Unusual hour successful logins (2 AM UTC)
    for i in range(5):
        midnight = now.replace(hour=2, minute=random.randint(0, 59), second=0, microsecond=0)
        docs.append({
            "id": secrets.token_hex(12), "user_id": user["id"],
            "timestamp": midnight.isoformat(),
            "ip_address": random.choice(normal_ips),
            "username": "eve",
            "event_type": "login", "status": "success",
            "risk_score": 0, "upload_id": upload_id,
        })
    # Password resets
    for i in range(8):
        ts = now.timestamp() - random.randint(0, 86400 * 3)
        docs.append({
            "id": secrets.token_hex(12), "user_id": user["id"],
            "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            "ip_address": random.choice(normal_ips),
            "username": random.choice(users),
            "event_type": "password_reset", "status": "success",
            "risk_score": 0, "upload_id": upload_id,
        })

    await db.logs.insert_many(docs)
    findings = analytics.detect(docs)
    alerts = []
    iso_now = now.isoformat()
    for a in findings.get("alerts", []):
        alerts.append({
            "id": secrets.token_hex(12), "user_id": user["id"],
            "type": a["type"], "severity": a["severity"], "message": a["message"],
            "ip_address": a.get("ip_address"), "username": a.get("username"),
            "mitre_id": a.get("mitre_id"), "timestamp": iso_now,
            "acknowledged": False, "upload_id": upload_id,
        })
    if alerts:
        await db.alerts.insert_many(alerts)
    return {"inserted": len(docs), "alerts_created": len(alerts)}


# ============== ANALYTICS / DASHBOARD ==============
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _all_user_logs(db, user_id: str) -> list[dict]:
    return await db.logs.find({"user_id": user_id}, {"_id": 0}).to_list(length=100000)


@analytics_router.get("/kpi")
async def get_kpi(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    logs = await _all_user_logs(db, user["id"])
    findings = analytics.detect(logs)
    return {
        "total_logs": len(logs),
        "failed_logins": findings.get("failed_logins", 0),
        "suspicious_ips": findings.get("suspicious_ips_count", 0),
        "risk_score": findings.get("risk_score", 0),
        "risk_level": findings.get("risk_level", "low"),
    }


@analytics_router.get("/dashboard")
async def get_dashboard(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    logs = await _all_user_logs(db, user["id"])
    findings = analytics.detect(logs)
    ts = analytics.timeseries(logs, "hour")
    dist = analytics.event_distribution(logs)
    return {
        "kpi": {
            "total_logs": len(logs),
            "failed_logins": findings.get("failed_logins", 0),
            "success_logins": findings.get("success_logins", 0),
            "suspicious_ips": findings.get("suspicious_ips_count", 0),
            "risk_score": findings.get("risk_score", 0),
            "risk_level": findings.get("risk_level", "low"),
        },
        "timeseries": ts,
        "event_distribution": dist,
        "top_suspicious_ips": findings.get("top_suspicious_ips", []),
        "brute_force_ips": findings.get("brute_force_ips", []),
        "failed_per_user": findings.get("failed_per_user", []),
        "unusual_hours": findings.get("unusual_hours", []),
    }


@analytics_router.get("/run")
async def run_analysis(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    logs = await _all_user_logs(db, user["id"])
    findings = analytics.detect(logs)
    now = datetime.now(timezone.utc).isoformat()
    report = {
        "id": secrets.token_hex(12),
        "user_id": user["id"],
        "report_date": now,
        "risk_score": findings.get("risk_score", 0),
        "risk_level": findings.get("risk_level", "low"),
        "total_logs": len(logs),
        "failed_logins": findings.get("failed_logins", 0),
        "suspicious_ips": findings.get("suspicious_ips_count", 0),
        "summary": f"Detected {len(findings.get('alerts', []))} threats across {len(logs)} log entries.",
        "top_threats": findings.get("top_suspicious_ips", [])[:5],
    }
    await db.reports.insert_one(report)
    report.pop("_id", None)
    return {**report, "findings": findings}


# ============== ALERTS ==============
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])


@alerts_router.get("")
async def list_alerts(
    request: Request,
    user=Depends(get_current_user),
    severity: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    db = request.app.state.db
    q: dict = {"user_id": user["id"]}
    if severity:
        q["severity"] = severity
    items = await db.alerts.find(q, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(length=limit)
    return {"items": items, "total": len(items)}


@alerts_router.post("/{alert_id}/acknowledge")
async def acknowledge(alert_id: str, request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    r = await db.alerts.update_one(
        {"id": alert_id, "user_id": user["id"]},
        {"$set": {"acknowledged": True}},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "ok"}


# ============== REPORTS ==============
reports_router = APIRouter(prefix="/reports", tags=["reports"])


@reports_router.get("")
async def list_reports(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    items = await db.reports.find({"user_id": user["id"]}, {"_id": 0}).sort("report_date", -1).limit(50).to_list(50)
    return {"items": items}


def _severity_color(level: str):
    return {
        "critical": colors.HexColor("#EF4444"),
        "high": colors.HexColor("#F59E0B"),
        "medium": colors.HexColor("#3B82F6"),
        "low": colors.HexColor("#10B981"),
    }.get(level, colors.grey)


@reports_router.get("/pdf")
async def export_pdf(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    logs = await _all_user_logs(db, user["id"])
    findings = analytics.detect(logs)
    alerts = await db.alerts.find({"user_id": user["id"]}, {"_id": 0}).sort("timestamp", -1).limit(200).to_list(200)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=42, bottomMargin=36)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"], textColor=colors.HexColor("#3B82F6"), fontSize=22)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=colors.HexColor("#111827"))
    body = styles["BodyText"]
    elements: list = []
    elements.append(Paragraph("Security Log Analyzer — Threat Report", title_style))
    elements.append(Paragraph(datetime.now(timezone.utc).strftime("Generated: %Y-%m-%d %H:%M UTC"), body))
    elements.append(Spacer(1, 12))

    # Executive summary
    elements.append(Paragraph("Executive Summary", h2))
    summary = (
        f"Analyzed <b>{len(logs)}</b> log entries. Risk Score: "
        f"<font color='{_severity_color(findings.get('risk_level','low')).hexval()}'>"
        f"<b>{findings.get('risk_score',0)}/100 ({findings.get('risk_level','low').upper()})</b></font>."
        f" Detected {len(findings.get('alerts', []))} security findings."
    )
    elements.append(Paragraph(summary, body))
    elements.append(Spacer(1, 12))

    # KPIs table
    elements.append(Paragraph("Key Metrics", h2))
    kpi_data = [
        ["Metric", "Value"],
        ["Total Log Entries", str(len(logs))],
        ["Successful Logins", str(findings.get("success_logins", 0))],
        ["Failed Logins", str(findings.get("failed_logins", 0))],
        ["Suspicious IPs", str(findings.get("suspicious_ips_count", 0))],
        ["Risk Score", f"{findings.get('risk_score',0)}/100"],
        ["Risk Level", findings.get("risk_level", "low").upper()],
    ]
    t = Table(kpi_data, hAlign="LEFT", colWidths=[2.5 * inch, 2.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F9FAFB"), colors.white]),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 14))

    # Top threats
    elements.append(Paragraph("Top Suspicious IPs", h2))
    if findings.get("top_suspicious_ips"):
        data = [["IP Address", "Failed Attempts"]]
        for it in findings["top_suspicious_ips"][:10]:
            data.append([it["ip"], str(it["count"])])
        t = Table(data, hAlign="LEFT", colWidths=[3 * inch, 2 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("No suspicious IPs detected.", body))
    elements.append(Spacer(1, 14))

    # Alerts
    elements.append(Paragraph("Recent Alerts", h2))
    if alerts:
        data = [["Severity", "Type", "Message"]]
        for a in alerts[:25]:
            data.append([a["severity"].upper(), a["type"], a["message"][:80]])
        t = Table(data, hAlign="LEFT", colWidths=[0.9 * inch, 1.5 * inch, 4.0 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("No alerts.", body))

    # Recommendations
    elements.append(Spacer(1, 14))
    elements.append(Paragraph("Recommendations", h2))
    recs = [
        "Block or rate-limit IP addresses exhibiting brute force behavior.",
        "Enforce strong passwords (≥12 chars) and require multi-factor authentication.",
        "Investigate user accounts with repeated failed logins for compromise.",
        "Monitor and alert on logins outside business hours (00:00–05:00).",
        "Implement geo-fencing for sensitive accounts.",
    ]
    for r_ in recs:
        elements.append(Paragraph(f"• {r_}", body))

    doc.build(elements)
    buf.seek(0)
    headers = {"Content-Disposition": "attachment; filename=security-report.pdf"}
    return StreamingResponse(buf, media_type="application/pdf", headers=headers)


@reports_router.get("/csv/{kind}")
async def export_csv(kind: str, request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    if kind not in {"logs", "alerts"}:
        raise HTTPException(status_code=400, detail="kind must be 'logs' or 'alerts'")
    buf = io.StringIO()
    writer = csv.writer(buf)
    if kind == "logs":
        items = await db.logs.find({"user_id": user["id"]}, {"_id": 0}).sort("timestamp", -1).to_list(50000)
        writer.writerow(["timestamp", "ip_address", "username", "event_type", "status"])
        for i in items:
            writer.writerow([i.get("timestamp"), i.get("ip_address"), i.get("username"),
                             i.get("event_type"), i.get("status")])
    else:
        items = await db.alerts.find({"user_id": user["id"]}, {"_id": 0}).sort("timestamp", -1).to_list(50000)
        writer.writerow(["timestamp", "severity", "type", "ip_address", "username", "mitre_id", "message"])
        for i in items:
            writer.writerow([i.get("timestamp"), i.get("severity"), i.get("type"),
                             i.get("ip_address"), i.get("username"), i.get("mitre_id"),
                             i.get("message")])
    content = buf.getvalue().encode("utf-8")
    headers = {"Content-Disposition": f"attachment; filename={kind}.csv"}
    return Response(content=content, media_type="text/csv", headers=headers)


# ============== MITRE ==============
mitre_router = APIRouter(prefix="/mitre", tags=["mitre"])


@mitre_router.get("/matrix")
async def get_matrix(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    pipeline = [
        {"$match": {"user_id": user["id"], "mitre_id": {"$ne": None}}},
        {"$group": {"_id": "$mitre_id", "count": {"$sum": 1}}},
    ]
    cursor = db.alerts.aggregate(pipeline)
    counts = {doc["_id"]: doc["count"] async for doc in cursor}
    # Enrich tactics with hit counts
    out = []
    for tac in TACTICS:
        techs = []
        for tech in tac["techniques"]:
            techs.append({**tech, "hits": counts.get(tech["id"], 0)})
        out.append({**tac, "techniques": techs})
    return {"tactics": out}


# ============== GEO ==============
geo_router = APIRouter(prefix="/geo", tags=["geo"])


@geo_router.get("/{ip}")
async def geo_lookup(ip: str, user=Depends(get_current_user)):
    return await geo.lookup(ip)


@geo_router.post("/batch")
async def geo_batch(payload: dict, user=Depends(get_current_user)):
    ips = payload.get("ips", [])
    if not isinstance(ips, list):
        raise HTTPException(status_code=400, detail="ips must be a list")
    return await geo.lookup_many(ips[:50])
