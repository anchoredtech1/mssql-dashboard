"""
routers/alerts.py
Alert rule CRUD + alert event history.

GET    /alerts/rules              – list all alert rules
POST   /alerts/rules              – create a rule
PUT    /alerts/rules/{id}         – update a rule
DELETE /alerts/rules/{id}         – delete a rule

GET    /alerts/events             – recent fired alerts (all servers)
GET    /alerts/events/{server_id} – recent alerts for one server
POST   /alerts/events/{id}/ack    – acknowledge an alert
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta

from database import get_db, AlertRule, AlertEvent, AlertSeverity

router = APIRouter(prefix="/alerts", tags=["alerts"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class AlertRuleCreate(BaseModel):
    server_id:  Optional[int]    = None    # None = applies to all
    metric:     str              = Field(..., max_length=80)
    operator:   str              = Field("gt", pattern="^(gt|lt|eq)$")
    threshold:  float
    severity:   AlertSeverity    = AlertSeverity.warning
    enabled:    bool             = True


class AlertRuleResponse(BaseModel):
    id:         int
    server_id:  Optional[int]
    metric:     str
    operator:   str
    threshold:  float
    severity:   AlertSeverity
    enabled:    bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertEventResponse(BaseModel):
    id:           int
    server_id:    int
    rule_id:      Optional[int]
    fired_at:     datetime
    resolved_at:  Optional[datetime]
    severity:     AlertSeverity
    metric:       str
    value:        float
    threshold:    float
    message:      str
    acknowledged: bool

    class Config:
        from_attributes = True


# ── Rules ─────────────────────────────────────────────────────────────────────

@router.get("/rules", response_model=list[AlertRuleResponse])
def list_rules(db: Session = Depends(get_db)):
    return db.query(AlertRule).order_by(AlertRule.id).all()


@router.post("/rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(payload: AlertRuleCreate, db: Session = Depends(get_db)):
    rule = AlertRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
def update_rule(rule_id: int, payload: AlertRuleCreate, db: Session = Depends(get_db)):
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, value in payload.model_dump().items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()


# ── Events ────────────────────────────────────────────────────────────────────

@router.get("/events", response_model=list[AlertEventResponse])
def list_events(hours: int = 24, db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(hours=min(hours, 720))
    return (
        db.query(AlertEvent)
        .filter(AlertEvent.fired_at >= since)
        .order_by(AlertEvent.fired_at.desc())
        .limit(500)
        .all()
    )


@router.get("/events/{server_id}", response_model=list[AlertEventResponse])
def server_events(server_id: int, hours: int = 24, db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(hours=min(hours, 720))
    return (
        db.query(AlertEvent)
        .filter(
            AlertEvent.server_id == server_id,
            AlertEvent.fired_at >= since
        )
        .order_by(AlertEvent.fired_at.desc())
        .limit(200)
        .all()
    )


@router.post("/events/{event_id}/ack", status_code=status.HTTP_200_OK)
def acknowledge_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(AlertEvent).filter(AlertEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.acknowledged = True
    db.commit()
    return {"acknowledged": True}


# ── Unacknowledged count (used for badge) ────────────────────────────────────

@router.get("/unacked-count")
def unacked_count(db: Session = Depends(get_db)):
    count = db.query(AlertEvent).filter(AlertEvent.acknowledged == False).count()
    return {"count": count}
