"""
routers/servers.py
CRUD endpoints for the monitored server registry.
POST /servers        – register a new server
GET  /servers        – list all servers
POST /servers/import – bulk import from SSMS .regsrvr XML file
GET  /servers/{id}   – get one server
PUT  /servers/{id}   – update a server
DELETE /servers/{id} – remove a server
POST /servers/{id}/test – test connection
"""

import xml.etree.ElementTree as ET
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from database import get_db, MonitoredServer, AuthType, ServerRole
from crypto import encrypt, decrypt
from connections.manager import pool

router = APIRouter(prefix="/api/servers", tags=["servers"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ServerCreate(BaseModel):
    display_name:  str          = Field(..., max_length=120)
    host:          str          = Field(..., max_length=255)
    port:          int          = Field(1433, ge=1, le=65535)
    instance_name: Optional[str] = None
    auth_type:     AuthType
    username:      Optional[str] = None
    password:      Optional[str] = None     # sent in plaintext, stored encrypted
    cert_path:     Optional[str] = None
    encrypt:       bool          = False
    trust_cert:    bool          = True
    role:          ServerRole    = ServerRole.standalone
    cluster_name:  Optional[str] = None
    poll_interval: int           = Field(60, ge=10, le=3600)
    notes:         Optional[str] = None
    enabled:       bool          = True


class ServerUpdate(BaseModel):
    display_name:  Optional[str]       = None
    host:          Optional[str]       = None
    port:          Optional[int]       = None
    instance_name: Optional[str]       = None
    auth_type:     Optional[AuthType]  = None
    username:      Optional[str]       = None
    password:      Optional[str]       = None
    cert_path:     Optional[str]       = None
    encrypt:       Optional[bool]      = None
    trust_cert:    Optional[bool]      = None
    role:          Optional[ServerRole] = None
    cluster_name:  Optional[str]       = None
    poll_interval: Optional[int]       = None
    notes:         Optional[str]       = None
    enabled:       Optional[bool]      = None


class ServerResponse(BaseModel):
    id:            int
    display_name:  str
    host:          str
    port:          int
    instance_name: Optional[str]
    auth_type:     AuthType
    username:      Optional[str]       # returned as-is (still encrypted)
    cert_path:     Optional[str]
    encrypt:       bool
    trust_cert:    bool
    role:          ServerRole
    cluster_name:  Optional[str]
    poll_interval: int
    enabled:       bool
    notes:         Optional[str]
    created_at:    datetime
    updated_at:    datetime

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
def create_server(payload: ServerCreate, db: Session = Depends(get_db)):
    server = MonitoredServer(
        display_name  = payload.display_name,
        host          = payload.host,
        port          = payload.port,
        instance_name = payload.instance_name,
        auth_type     = payload.auth_type,
        username      = encrypt(payload.username)  if payload.username  else None,
        password      = encrypt(payload.password)  if payload.password  else None,
        cert_path     = payload.cert_path,
        encrypt       = payload.encrypt,
        trust_cert    = payload.trust_cert,
        role          = payload.role,
        cluster_name  = payload.cluster_name,
        poll_interval = payload.poll_interval,
        notes         = payload.notes,
        enabled       = payload.enabled,
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return server


@router.post("/import", status_code=status.HTTP_200_OK)
async def import_servers(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Bulk imports servers from an SSMS .regsrvr XML file."""
    content = await file.read()
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        raise HTTPException(status_code=400, detail="Invalid XML file format.")

    imported_count = 0

    # SSMS files contain namespaces, so we search by matching the end of the tag name
    for elem in root.iter():
        tag = elem.tag.split('}')[-1]  # Strip out the XML namespace
        if tag == "RegisteredServer":
            display_name = "Imported Server"
            host = "localhost"
            instance_name = None
            port = 1433
            auth_type = AuthType.windows
            username = None

            # Look through the properties of this specific server
            for child in elem.iter():
                ctag = child.tag.split('}')[-1]
                if ctag == "Name" and child.text:
                    display_name = child.text
                elif ctag == "ServerName" and child.text:
                    raw_host = child.text
                    # Check for instance name (Host\Instance)
                    if "\\" in raw_host:
                        host, instance_name = raw_host.split("\\", 1)
                    # Check for custom port (Host,1433)
                    elif "," in raw_host:
                        host, port_str = raw_host.split(",", 1)
                        try:
                            port = int(port_str)
                        except ValueError:
                            pass
                    else:
                        host = raw_host
                elif ctag == "LoginSecure" and child.text:
                    # 'false' or '0' means SQL Authentication
                    if child.text.lower() in ['false', '0']:
                        auth_type = AuthType.sql
                elif ctag == "Login" and child.text:
                    username = child.text

            # Save to database
            server = MonitoredServer(
                display_name=display_name,
                host=host,
                port=port,
                instance_name=instance_name,
                auth_type=auth_type,
                username=encrypt(username) if username else None,
                encrypt=False,
                trust_cert=True,
                role=ServerRole.standalone,
                poll_interval=60,
                enabled=True
            )
            db.add(server)
            imported_count += 1

    db.commit()
    return {"message": f"Successfully imported {imported_count} servers."}


@router.get("/", response_model=list[ServerResponse])
def list_servers(db: Session = Depends(get_db)):
    return db.query(MonitoredServer).order_by(MonitoredServer.display_name).all()


@router.get("/{server_id}", response_model=ServerResponse)
def get_server(server_id: int, db: Session = Depends(get_db)):
    srv = db.query(MonitoredServer).filter(MonitoredServer.id == server_id).first()
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")
    return srv


@router.put("/{server_id}", response_model=ServerResponse)
def update_server(server_id: int, payload: ServerUpdate, db: Session = Depends(get_db)):
    srv = db.query(MonitoredServer).filter(MonitoredServer.id == server_id).first()
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "password" and value is not None:
            value = encrypt(value)
        elif field == "username" and value is not None:
            value = encrypt(value)
        setattr(srv, field, value)

    srv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(srv)

    # Invalidate the connection pool entry so next poll reconnects
    pool.remove(server_id)
    return srv


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_server(server_id: int, db: Session = Depends(get_db)):
    srv = db.query(MonitoredServer).filter(MonitoredServer.id == server_id).first()
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")
    pool.remove(server_id)
    db.delete(srv)
    db.commit()


@router.post("/{server_id}/test")
def test_connection(server_id: int, db: Session = Depends(get_db)):
    srv = db.query(MonitoredServer).filter(MonitoredServer.id == server_id).first()
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")
    result = pool.test_connection(srv)
    return result