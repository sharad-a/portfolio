"""
Lambda handler for portfolio contact form.

Environment variables required:
  SES_SENDER_EMAIL  – verified SES sender address (e.g. hello@yourdomain.com)
  NOTIFY_EMAIL      – address that receives the notification
  ALLOWED_ORIGIN    – frontend origin for CORS (e.g. https://yourdomain.com)
                      set to * only during development
"""

import json
import os
import re
import boto3
from botocore.exceptions import ClientError

ses = boto3.client("ses")

SENDER_EMAIL  = os.environ["SES_SENDER_EMAIL"]
NOTIFY_EMAIL  = os.environ["NOTIFY_EMAIL"]
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ── helpers ──────────────────────────────────────────────────────────────────

def cors_headers(origin: str) -> dict:
    allowed = ALLOWED_ORIGIN if ALLOWED_ORIGIN == "*" else ALLOWED_ORIGIN
    return {
        "Access-Control-Allow-Origin":  allowed,
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
    }


def response(status: int, body: dict, origin: str = "") -> dict:
    return {
        "statusCode": status,
        "headers": {**cors_headers(origin), "Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def validate(data: dict) -> str | None:
    """Return an error message or None when data is valid."""
    for field in ("name", "email", "subject", "message"):
        if not data.get(field, "").strip():
            return f"Missing required field: {field}"

    if not EMAIL_RE.match(data["email"].strip()):
        return "Invalid email address"

    if len(data["message"]) > 5_000:
        return "Message is too long (max 5 000 characters)"

    return None


def build_email(data: dict) -> dict:
    name    = data["name"].strip()
    email   = data["email"].strip()
    subject = data["subject"].strip()
    message = data["message"].strip()

    html_body = f"""
    <html><body style="font-family:sans-serif;color:#222;max-width:600px;margin:auto">
      <h2 style="color:#6c63ff">New contact form message</h2>
      <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:8px;font-weight:bold;width:90px">From</td>
            <td style="padding:8px">{name} &lt;{email}&gt;</td></tr>
        <tr style="background:#f5f5f5">
            <td style="padding:8px;font-weight:bold">Subject</td>
            <td style="padding:8px">{subject}</td></tr>
        <tr><td style="padding:8px;font-weight:bold;vertical-align:top">Message</td>
            <td style="padding:8px;white-space:pre-wrap">{message}</td></tr>
      </table>
      <p style="color:#888;font-size:12px;margin-top:24px">
        Sent via portfolio contact form
      </p>
    </body></html>
    """

    text_body = (
        f"New contact form message\n\n"
        f"From:    {name} <{email}>\n"
        f"Subject: {subject}\n\n"
        f"{message}\n"
    )

    return {
        "Source": SENDER_EMAIL,
        "Destination": {"ToAddresses": [NOTIFY_EMAIL]},
        "ReplyToAddresses": [email],
        "Message": {
            "Subject": {"Data": f"[Portfolio] {subject}", "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": text_body, "Charset": "UTF-8"},
                "Html": {"Data": html_body, "Charset": "UTF-8"},
            },
        },
    }

# ── handler ───────────────────────────────────────────────────────────────────

def handler(event: dict, context) -> dict:
    origin = (event.get("headers") or {}).get("origin", "")

    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return response(200, {"message": "ok"}, origin)

    # Parse body
    try:
        body = event.get("body") or "{}"
        data = json.loads(body)
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON"}, origin)

    # Validate
    err = validate(data)
    if err:
        return response(400, {"error": err}, origin)

    # Send email via SES
    try:
        ses.send_email(**build_email(data))
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        print(f"SES error [{code}]: {exc}")

        if code == "MessageRejected":
            return response(400, {"error": "Email address not verified with SES"}, origin)
        if code in ("Throttling", "SendingPausedException"):
            return response(429, {"error": "Too many requests — try again later"}, origin)

        return response(500, {"error": "Failed to send email"}, origin)

    return response(200, {"message": "Message sent successfully"}, origin)
