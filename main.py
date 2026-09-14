"""
Enterprise Vendor Risk Auditor - CLI Runner
Usage:
    python main.py --demo                      # Run audit on demo vendor (CloudSync AI)
    python main.py --demo-clean                # Run audit on compliant vendor (SecureVault)
    python main.py --file path/to/doc.pdf      # Run audit on any custom document
    python main.py --demo -y                   # Auto-approve without interactive prompts
"""
import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from src.utils.parser import parse_document
from src.graph.workflow import build_audit_graph

console = Console(legacy_windows=False)


def run_audit(file_path: str, vendor_name: str = None, auto_approve: bool = False):
    if not os.path.exists(file_path):
        console.print(f"[bold red]Error: File not found at {file_path}[/bold red]")
        sys.exit(1)

    if vendor_name is None:
        base = os.path.basename(file_path)
        vendor_name = os.path.splitext(base)[0].replace("_", " ").title()

    console.print(Panel.fit(
        f"[bold cyan]Autonomous Enterprise Vendor Risk & Security Auditor[/bold cyan]\n"
        f"Target Document: [yellow]{os.path.basename(file_path)}[/yellow]\n"
        f"Vendor: [bold green]{vendor_name}[/bold green]\n"
        f"Orchestration Engine: [magenta]LangGraph[/magenta] | Protocol: [blue]MCP[/blue] | Memory: [green]Hybrid RAG[/green]",
        title="Auditor Initialized", border_style="cyan"
    ))

    with console.status("[bold green]Parsing document sections..."):
        parsed = parse_document(file_path)

    console.print(f"[bold green]Parsed[/bold green] [bold]{len(parsed['sections'])}[/bold] sections from {parsed['filename']}.")

    graph = build_audit_graph(enable_hitl=True)
    thread_id = f"cli-audit-{datetime.datetime.now().strftime('%H%M%S')}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "vendor_name": vendor_name,
        "document_path": file_path,
        "document_text": parsed["full_text"],
        "sections": parsed["sections"],
        "extracted_clauses": [],
        "retrieved_policies": {},
        "checklist": [],
        "reflection_notes": [],
        "scorecard": {},
        "human_approved": False,
        "human_reviewer": "",
        "human_feedback": "",
        "mcp_actions_taken": [],
        "current_step": "Initialized",
        # FIX: llm_provider was missing from main.py initial_state — CLI always ran
        # heuristic mode even when the user expected otherwise. Now explicitly set.
        "llm_provider": "local"
    }

    with console.status("[bold cyan]Executing LangGraph state machine..."):
        for output in graph.stream(initial_state, config=config):
            for node_name, state_update in output.items():
                if isinstance(state_update, dict):
                    console.print(f"  -> [dim]Node: {node_name}[/dim] -> [cyan]{state_update.get('current_step')}[/cyan]")

    snapshot = graph.get_state(config)
    scorecard = snapshot.values.get("scorecard", {})
    checklist = snapshot.values.get("checklist", [])

    table = Table(title=f"Compliance Scorecard: {vendor_name}", header_style="bold magenta")
    table.add_column("Category", style="cyan", width=18)
    table.add_column("Status", width=14)
    table.add_column("Confidence", justify="right", width=12)
    table.add_column("Finding / Evidence", style="white")

    for item in checklist:
        status = item["status"]
        if status == "PASS":
            status_text = "[bold green]PASS[/bold green]"
        elif status == "FAIL":
            status_text = "[bold red]FAIL[/bold red]"
        else:
            status_text = "[bold yellow]REVIEW[/bold yellow]"
        conf = f"{int(item['confidence'] * 100)}%"
        table.add_row(item["category"], status_text, conf, item["reasoning"])

    console.print("\n")
    console.print(table)

    risk = scorecard.get("overall_risk", "UNKNOWN")
    risk_color = "red" if risk == "HIGH" else ("yellow" if risk == "MEDIUM" else "green")
    console.print(Panel(
        f"[bold {risk_color}]Overall Risk Level: {risk} (Score: {scorecard.get('risk_score_numeric', 0)}/100)[/bold {risk_color}]\n\n"
        f"{scorecard.get('executive_summary', '')}",
        title="Executive Risk Assessment", border_style=risk_color
    ))

    console.print("\n[bold yellow]LangGraph Checkpoint Reached: Human Review Required[/bold yellow]")
    console.print("The agent is currently paused. No destructive or logging tools have been executed.")

    if auto_approve:
        approve = True
        reviewer_name = "Lead Security Engineer (Automated Sign-off)"
        feedback = "Auto-approved via CLI flag."
        console.print(f"[bold green]Auto-approving audit as {reviewer_name}...[/bold green]")
    else:
        approve = Confirm.ask(f"Do you want to authorize approval and trigger MCP tools for {vendor_name}?")
        reviewer_name = Prompt.ask("Enter Reviewer Name", default="Lead Security Engineer")
        feedback = Prompt.ask("Enter Reviewer Comments", default="Audit reviewed via CLI.")

    graph.update_state(config, {
        "human_approved": approve,
        "human_reviewer": reviewer_name,
        "human_feedback": feedback
    })

    console.print("\n[bold green]Resuming LangGraph execution to execute MCP tools...[/bold green]")
    for output in graph.stream(None, config=config):
        for node_name, state_update in output.items():
            if isinstance(state_update, dict):
                console.print(f"  -> [dim]Node: {node_name}[/dim] -> [green]{state_update.get('current_step')}[/green]")

    final_snapshot = graph.get_state(config)
    mcp_actions = final_snapshot.values.get("mcp_actions_taken", [])

    console.print("\n[bold cyan]Model Context Protocol (MCP) Execution Log:[/bold cyan]")
    for act in mcp_actions:
        tool = act["tool"]
        res = act["result"]
        console.print(f"  [bold]{tool}[/bold]: [green]{res}[/green]")

    console.print("\n[bold green]Audit Complete! All reports and tickets archived.[/bold green]\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous Enterprise Vendor Risk Auditor")
    parser.add_argument("--demo", action="store_true", help="Run demo on CloudSync AI (High Risk)")
    parser.add_argument("--demo-clean", action="store_true", help="Run demo on SecureVault (Low Risk)")
    parser.add_argument("--file", type=str, help="Path to vendor document (PDF or Markdown)")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-approve without interactive prompt")
    args = parser.parse_args()

    if args.demo:
        sample_path = os.path.join(BASE_DIR, "data", "sample_vendors", "cloudsync_soc2_report.pdf")
        run_audit(sample_path, "CloudSync AI", auto_approve=args.yes)
    elif args.demo_clean:
        sample_path = os.path.join(BASE_DIR, "data", "sample_vendors", "securevault_compliance.pdf")
        run_audit(sample_path, "SecureVault Enterprise", auto_approve=args.yes)
    elif args.file:
        run_audit(args.file, auto_approve=args.yes)
    else:
        sample_path = os.path.join(BASE_DIR, "data", "sample_vendors", "cloudsync_soc2_report.pdf")
        run_audit(sample_path, "CloudSync AI", auto_approve=args.yes)
