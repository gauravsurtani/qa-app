import asyncio
import base64
import logging
from dataclasses import dataclass

import httpx

from app.config import get_settings

logger = logging.getLogger("qa.email")

RESEND_URL = "https://api.resend.com/emails"


@dataclass
class EmailAttachment:
    filename: str
    content_b64: str
    content_type: str = "text/csv"


async def send_session_ended_email(
    *,
    to_address: str,
    subject: str,
    html_body: str,
    csv_attachment: bytes,
    csv_filename: str,
    max_retries: int = 3,
) -> bool:
    s = get_settings()
    if not s.email_api_key:
        logger.warning("EMAIL_API_KEY not configured; skipping send")
        return False
    payload = {
        "from": f"{s.email_from_name} <{s.email_from_address}>",
        "to": [to_address],
        "subject": subject,
        "html": html_body,
        "attachments": [
            {
                "filename": csv_filename,
                "content": base64.b64encode(csv_attachment).decode("ascii"),
            }
        ],
    }
    delay = 2.0
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=15.0) as http:
                r = await http.post(
                    RESEND_URL,
                    json=payload,
                    headers={"Authorization": f"Bearer {s.email_api_key}"},
                )
            if 200 <= r.status_code < 300:
                return True
            logger.error("resend non-2xx", extra={"status": r.status_code, "body": r.text})
        except httpx.RequestError as e:
            logger.error("resend request error", extra={"err": str(e)})
        if attempt < max_retries - 1:
            await asyncio.sleep(delay)
            delay *= 4
    return False
