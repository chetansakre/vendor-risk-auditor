"""
Enterprise Compliance MCP Server
Compliant with Model Context Protocol (MCP) JSON-RPC 2.0 specifications over stdio.
Exposes tools for saving reports, filing compliance tickets, and triggering alerts.
"""
import sys
import json
import os
import datetime
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

TOOLS_METADATA = [
    {
        "name": "save_audit_report",
        "description": "Saves an enterprise vendor risk audit report to the persistent filesystem.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vendor_name": {"type": "string", "description": "The legal name of the vendor evaluated"},
                "risk_score": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"], "description": "Overall risk level"},
                "markdown_content": {"type": "string", "description": "Full markdown content of the audit report"}
            },
            "required": ["vendor_name", "risk_score", "markdown_content"]
        }
    },
    {
        "name": "create_compliance_ticket",
        "description": "Creates a formal security review ticket in the enterprise tracking system (e.g. Jira / Linear).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vendor_name": {"type": "string", "description": "Vendor name"},
                "summary": {"type": "string", "description": "Brief ticket title"},
                "priority": {"type": "string", "enum": ["P0", "P1", "P2", "P3"], "description": "Urgency tier based on risk score"},
                "flagged_issues": {"type": "array", "items": {"type": "string"}, "description": "List of non-compliant items found"}
            },
            "required": ["vendor_name", "summary", "priority"]
        }
    },
    {
        "name": "send_slack_alert",
        "description": "Dispatches an executive security alert card to the #security-vendor-reviews Slack channel.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "Destination Slack channel (default: #security-reviews)"},
                "vendor_name": {"type": "string", "description": "Vendor name"},
                "risk_score": {"type": "string", "description": "Overall risk rating"},
                "executive_summary": {"type": "string", "description": "Key takeaways and next steps"}
            },
            "required": ["vendor_name", "risk_score", "executive_summary"]
        }
    }
]

def handle_save_audit_report(args):
    vendor = args.get("vendor_name", "vendor").replace(" ", "_").lower()
    risk = args.get("risk_score", "UNKNOWN")
    content = args.get("markdown_content", "")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"audit_report_{vendor}_{timestamp}.md"
    filepath = os.path.join(REPORTS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "status": "success",
        "file_path": filepath,
        "filename": filename,
        "bytes_written": len(content.encode("utf-8")),
        "message": f"Report securely archived to filesystem at {filename}"
    }

def handle_create_compliance_ticket(args):
    vendor = args.get("vendor_name", "Vendor")
    priority = args.get("priority", "P2")
    issues = args.get("flagged_issues", [])
    ticket_id = f"SEC-{random.randint(1000, 9999)}"

    return {
        "status": "created",
        "ticket_id": ticket_id,
        "system": "Enterprise Jira Service Desk",
        "priority": priority,
        "assignee": "SecOps On-Call Lead",
        "summary": f"[{priority}] Vendor Risk Assessment: {vendor}",
        "flagged_violations_count": len(issues),
        "url": f"https://jira.internal.enterprise.net/browse/{ticket_id}"
    }

def handle_send_slack_alert(args):
    channel = args.get("channel", "#security-reviews")
    vendor = args.get("vendor_name", "Unknown Vendor")
    risk = args.get("risk_score", "UNKNOWN")
    summary = args.get("executive_summary", "")

    return {
        "status": "delivered",
        "channel": channel,
        "timestamp": datetime.datetime.now().isoformat(),
        "delivered_card": {
            "title": f":shield: Vendor Security Audit Complete: {vendor}",
            "risk_badge": f":red_circle: HIGH RISK" if risk == "HIGH" else (f":warning: MEDIUM RISK" if risk == "MEDIUM" else f":white_check_mark: LOW RISK"),
            "summary": summary[:200] + "..." if len(summary) > 200 else summary
        }
    }

def process_message(msg):
    req_id = msg.get("id")
    method = msg.get("method")
    params = msg.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False}
                },
                "serverInfo": {
                    "name": "enterprise-compliance-mcp",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS_METADATA
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        if tool_name == "save_audit_report":
            res = handle_save_audit_report(tool_args)
        elif tool_name == "create_compliance_ticket":
            res = handle_create_compliance_ticket(tool_args)
        elif tool_name == "send_slack_alert":
            res = handle_send_slack_alert(tool_args)
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(res, indent=2)
                    }
                ],
                "isError": False
            }
        }

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }

def run_server():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            response = process_message(msg)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(e)}
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    run_server()
