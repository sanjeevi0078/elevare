"""
Connection Management API
Handles cofounder connection requests, tracking, and communication
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from db.database import get_db
from models.user_models import User
from logger import logger
from config import settings

router = APIRouter(prefix="/connect", tags=["connections"])


class ConnectionRequest(BaseModel):
    """Request to connect with a potential cofounder"""
    sender_id: int
    recipient_id: int
    message: str
    idea_context: Optional[str] = None


class ConnectionResponse(BaseModel):
    success: bool
    message: str
    connection_method: str  # 'email', 'linkedin', 'github'
    contact_info: Optional[str] = None


@router.post("/send", response_model=ConnectionResponse)
async def send_connection_request(
    request: ConnectionRequest,
    db: Session = Depends(get_db)
):
    """
    Send a connection request to a potential cofounder.
    Tries multiple channels: email, LinkedIn, GitHub.
    """
    try:
        # Get sender and recipient
        sender = db.query(User).filter(User.id == request.sender_id).first()
        recipient = db.query(User).filter(User.id == request.recipient_id).first()
        
        if not sender or not recipient:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Build personalized message
        subject = f"Cofounder Opportunity from {sender.name} via Elevare"
        body = f"""
Hi {recipient.name},

{request.message}

{f"Context: {request.idea_context}" if request.idea_context else ""}

Best regards,
{sender.name}
{sender.email if sender.email else ""}

---
This message was sent via Elevare - AI-Powered Cofounder Matching
Reply directly to this email to connect.
"""
        
        # Priority 1: Send email if available
        if recipient.email and recipient.email != "not_set":
            try:
                send_email(
                    to_email=recipient.email,
                    subject=subject,
                    body=body,
                    from_name=sender.name
                )
                logger.info(f"✅ Connection request sent via email to {recipient.email}")
                return ConnectionResponse(
                    success=True,
                    message=f"Connection request sent to {recipient.name} via email",
                    connection_method="email",
                    contact_info=recipient.email
                )
            except Exception as e:
                logger.error(f"Email sending failed: {e}")
        
        # Priority 2: LinkedIn (return URL for user to open)
        if hasattr(recipient, 'linkedin_url') and recipient.linkedin_url:
            return ConnectionResponse(
                success=True,
                message=f"Open LinkedIn to connect with {recipient.name}",
                connection_method="linkedin",
                contact_info=recipient.linkedin_url
            )
        
        # Priority 3: GitHub (return profile URL)
        if hasattr(recipient, 'github_username') and recipient.github_username:
            github_url = f"https://github.com/{recipient.github_username}"
            return ConnectionResponse(
                success=True,
                message=f"Visit GitHub to connect with {recipient.name}",
                connection_method="github",
                contact_info=github_url
            )
        
        # Fallback: No contact method available
        return ConnectionResponse(
            success=False,
            message=f"No contact information available for {recipient.name}",
            connection_method="none",
            contact_info=None
        )
        
    except Exception as e:
        logger.error(f"Connection request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def send_email(to_email: str, subject: str, body: str, from_name: str = "Elevare"):
    """
    Send email using SMTP (configure in production with SendGrid/AWS SES)
    """
    # For development: Log email instead of sending
    if settings.ENVIRONMENT.value == "development":
        logger.info(f"📧 [DEV MODE] Email to {to_email}:\nSubject: {subject}\n{body}")
        return
    
    # Production email sending (requires SMTP configuration)
    if not hasattr(settings, 'SMTP_SERVER'):
        logger.warning("SMTP not configured - email not sent")
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{from_name} <noreply@elevare.ai>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
            
        logger.info(f"✅ Email sent to {to_email}")
    except Exception as e:
        logger.error(f"❌ Email sending failed: {e}")
        raise


@router.get("/history/{user_id}")
async def get_connection_history(user_id: int, db: Session = Depends(get_db)):
    """
    Get connection request history for a user
    (Future: Store in database for tracking)
    """
    # TODO: Implement database storage for connection history
    return {
        "user_id": user_id,
        "sent_requests": [],
        "received_requests": [],
        "message": "Connection history tracking coming soon"
    }
