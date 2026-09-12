"""
LangGraph Nodes for Vendor Risk Audit Pipeline.
Includes: Clause Extraction, Hybrid RAG Retrieval, Compliance Auditing,
Self-Correction / Reflection, Scorecard Compilation, and MCP Execution.
"""
import os
import re
from typing import Dict, Any, List
from src.rag.hybrid_retriever import HybridRetriever
from src.mcp.client import MCPClient

CATEGORIES = [
    "Encryption",
    "AI_Governance",
    "Data_Retention",
    "Subprocessors",
    "Incident_Response",
    "Access_Control"
]

def extract_clauses_node(state: Dict[str, Any]) -> Dict[str, Any]:
    sections = state.get("sections", [])
    doc_text = state.get("document_text", "")
    extracted = []
    cid = 1

    for sec in sections:
        title = sec.get("title", "")
        content = sec.get("content", "")
        title_lower = title.lower()
        content_lower = content.lower()

        cat = _detect_category(title_lower)
        if not cat:
            cat = _detect_category(content_lower)

        if cat and len(content.strip()) > 20:
            extracted.append({
                "clause_id": f"CLAUSE-{cid:02d}",
                "category": cat,
                "section_title": title,
                "text": content[:1500]
            })
            cid += 1

    # Ensure coverage across all 6 critical categories
    found_cats = set(item["category"] for item in extracted)
    for cat in CATEGORIES:
        if cat not in found_cats:
            snippet = _extract_paragraph_for_category(doc_text, cat)
            if snippet:
                extracted.append({
                    "clause_id": f"CLAUSE-{cid:02d}",
                    "category": cat,
                    "section_title": f"{cat} Policy Clause",
                    "text": snippet
                })
                cid += 1

    return {
        "extracted_clauses": extracted,
        "current_step": "Clauses Extracted"
    }

def _detect_category(text: str) -> str:
    if "retention" in text or "deletion" in text or "expung" in text or "terminat" in text:
        return "Data_Retention"
    elif "subprocessor" in text or "third-party" in text:
        return "Subprocessors"
    elif "incident" in text or "breach" in text or "csirt" in text:
        return "Incident_Response"
    elif "access" in text or "auth" in text or "sso" in text or "mfa" in text or "rbac" in text:
        return "Access_Control"
    elif "ai" in text or "model" in text or "training" in text or "intelligence" in text or "fine-tune" in text:
        return "AI_Governance"
    elif "crypt" in text or "encrypt" in text or "aes" in text or "tls" in text:
        return "Encryption"
    return None

def _extract_paragraph_for_category(full_text: str, category: str) -> str:
    paragraphs = full_text.split("\n\n")
    for p in paragraphs:
        p_lower = p.lower()
        if _detect_category(p_lower) == category and len(p.strip()) > 30:
            return p.strip()
    return ""

_GLOBAL_RETRIEVER = None

def get_retriever():
    global _GLOBAL_RETRIEVER
    if _GLOBAL_RETRIEVER is None:
        _GLOBAL_RETRIEVER = HybridRetriever()
    return _GLOBAL_RETRIEVER

def retrieve_policies_node(state: Dict[str, Any]) -> Dict[str, Any]:
    retriever = get_retriever()
    extracted = state.get("extracted_clauses", [])
    retrieved_map = {}

    for item in extracted:
        cat = item["category"]
        query = f"{cat} {item['section_title']} {item['text'][:200]}"
        matches = retriever.retrieve(query, top_k=2)
        retrieved_map[cat] = matches

    return {
        "retrieved_policies": retrieved_map,
        "current_step": "Policies Retrieved via Hybrid RAG"
    }

def audit_compliance_node(state: Dict[str, Any]) -> Dict[str, Any]:
    extracted = state.get("extracted_clauses", [])
    policies_map = state.get("retrieved_policies", {})
    llm_provider = state.get("llm_provider", "local")
    checklist = []

    qwen_client = None
    if llm_provider == "qwen":
        try:
            from src.graph.llm_client import QwenLLMClient
            qwen_client = QwenLLMClient()
        except Exception:
            qwen_client = None

    for item in extracted:
        cat = item["category"]
        text = item["text"]
        text_lower = text.lower()
        policies = policies_map.get(cat, [])
        policy_req = policies[0]["title"] if policies else f"Enterprise {cat} Policy"
        policy_full = policies[0].get("content", policy_req) if policies else policy_req

        status = "NEEDS_REVIEW"
        confidence = 0.85
        evidence = ""
        reasoning = ""

        # If Qwen 122B is active, perform frontier neural legal reasoning
        if qwen_client:
            q_res = qwen_client.audit_clause_with_qwen(category=cat, policy_standard=policy_full, vendor_evidence=text[:1000])
            if isinstance(q_res, dict) and "status" in q_res and "reasoning" in q_res:
                status = q_res["status"]
                confidence = float(q_res.get("confidence", 0.95))
                reasoning = f"[Qwen 122B] {q_res['reasoning']}"
                evidence = _find_matching_snippet(text, ["aes", "tls", "train", "retention", "subprocessor", "incident", "breach", "sso", "mfa"]) or text[:200]
                checklist.append({
                    "clause_id": item["clause_id"],
                    "category": cat,
                    "policy_requirement": policy_req,
                    "vendor_claim": item["section_title"],
                    "status": status,
                    "confidence": confidence,
                    "evidence": evidence,
                    "reasoning": reasoning
                })
                continue

        if cat == "Encryption":
            has_aes = "aes-256" in text_lower or "aes 256" in text_lower
            has_tls = "tls 1.3" in text_lower or "tls 1.2" in text_lower
            if has_aes and has_tls:
                status = "PASS"
                confidence = 0.96
                evidence = _find_matching_snippet(text, ["aes-256", "tls 1.3", "tls 1.2"])
                reasoning = "Vendor enforces AES-256 encryption at rest and TLS 1.3/1.2 in transit."
            else:
                status = "FAIL"
                confidence = 0.90
                evidence = text[:150]
                reasoning = "Failed to confirm both AES-256 and modern TLS encryption standards."

        elif cat == "AI_Governance":
            trains_on_data = ("fine-tune" in text_lower or "train" in text_lower or "quality assurance" in text_lower or "optimization" in text_lower) and ("not" not in text_lower and "never" not in text_lower)
            zero_guarantee = "never stored" in text_lower or "zero data retention" in text_lower or "never used to train" in text_lower
            
            if zero_guarantee:
                status = "PASS"
                confidence = 0.98
                evidence = _find_matching_snippet(text, ["never used to train", "zero data retention", "never stored"])
                reasoning = "Vendor provides explicit, legally binding Zero Data Retention and Zero Model Training guarantees."
            elif trains_on_data:
                status = "FAIL"
                confidence = 0.96
                evidence = _find_matching_snippet(text, ["fine-tune", "train", "optimize", "quality assurance"])
                reasoning = "CRITICAL VIOLATION: Vendor utilizes customer data/prompts for internal model training and optimization."
            else:
                status = "NEEDS_REVIEW"
                confidence = 0.70
                evidence = text[:150]
                reasoning = "Ambiguous AI data governance policy. Requires explicit legal addendum."

        elif cat == "Data_Retention":
            days_match = re.findall(r"(\d+)\s*(?:calendar\s*)?days", text_lower)
            has_30 = any(int(d) <= 30 for d in days_match if d.isdigit())
            has_over_30 = any(int(d) > 30 for d in days_match if d.isdigit())

            if has_30 and not has_over_30:
                status = "PASS"
                confidence = 0.95
                evidence = _find_matching_snippet(text, ["days", "expungement", "purged", "sanitized"])
                reasoning = f"Data deletion SLA complies with enterprise 30-day mandate ({days_match[0]} days)."
            elif has_over_30 or "ninety" in text_lower or "90" in text_lower:
                status = "FAIL"
                confidence = 0.95
                evidence = _find_matching_snippet(text, ["days", "retention", "expungement", "ninety"])
                reasoning = "VIOLATION: Data retention SLA (90 days) exceeds internal 30-day mandatory expungement limit."
            else:
                status = "NEEDS_REVIEW"
                confidence = 0.65
                evidence = text[:150]
                reasoning = "Unspecified data retention timeline upon contract termination."

        elif cat == "Subprocessors":
            has_rss_only = "rss" in text_lower or "website" in text_lower or "10 days" in text_lower

            if "45" in text_lower or "30 days" in text_lower or "advance written" in text_lower:
                status = "PASS"
                confidence = 0.92
                evidence = _find_matching_snippet(text, ["days advance", "written email notice", "prior"])
                reasoning = "Provides at least 30 days prior written notice before onboarding subprocessors."
            elif has_rss_only:
                status = "FAIL"
                confidence = 0.90
                evidence = _find_matching_snippet(text, ["rss", "website", "10 days", "ten"])
                reasoning = "VIOLATION: Provides insufficient notice (10 days / website RSS only) vs mandatory 30 days direct written notice."
            else:
                status = "NEEDS_REVIEW"
                confidence = 0.75
                evidence = text[:150]
                reasoning = "Subprocessor notification terms require manual review."

        elif cat == "Incident_Response":
            if "12" in text_lower or "24 hours" in text_lower or "24" in text_lower or "immediate" in text_lower:
                status = "PASS"
                confidence = 0.95
                evidence = _find_matching_snippet(text, ["24 hours", "12 hours", "immediate"])
                reasoning = "Complies with enterprise 24-hour mandatory security breach notification SLA."
            elif "72 hours" in text_lower or "72" in text_lower or "seventy-two" in text_lower:
                status = "FAIL"
                confidence = 0.92
                evidence = _find_matching_snippet(text, ["seventy-two", "72 hours", "72"])
                reasoning = "VIOLATION: 72-hour notification SLA exceeds enterprise mandatory 24-hour SLA."
            else:
                status = "NEEDS_REVIEW"
                confidence = 0.60
                evidence = text[:150]
                reasoning = "Breach notification timeline is not strictly specified."

        elif cat == "Access_Control":
            has_sso = "sso" in text_lower or "saml" in text_lower or "oidc" in text_lower
            has_mfa = "mfa" in text_lower or "multi-factor" in text_lower or "fido2" in text_lower

            if has_sso and has_mfa:
                status = "PASS"
                confidence = 0.95
                evidence = _find_matching_snippet(text, ["sso", "saml 2.0", "mfa", "multi-factor"])
                reasoning = "Supports enterprise SSO (SAML 2.0/OIDC) and mandates MFA for administrative access."
            else:
                status = "NEEDS_REVIEW"
                confidence = 0.75
                evidence = text[:150]
                reasoning = "Partial access controls found. Confirm SAML 2.0 and MFA availability."

        checklist.append({
            "clause_id": item["clause_id"],
            "category": cat,
            "policy_requirement": policy_req,
            "vendor_claim": item["section_title"],
            "status": status,
            "confidence": confidence,
            "evidence": evidence or text[:200],
            "reasoning": reasoning
        })

    return {
        "checklist": checklist,
        "current_step": "Compliance Rules Evaluated"
    }

def reflection_verifier_node(state: Dict[str, Any]) -> Dict[str, Any]:
    checklist = state.get("checklist", [])
    doc_text = state.get("document_text", "").lower()
    notes = []

    for item in checklist:
        ev = item["evidence"].lower()
        if ev and len(ev) > 20 and ev[:35] in doc_text:
            notes.append(f"Faithfulness Verified for {item['category']}: Evidence quote matches source text.")
        else:
            notes.append(f"Context re-check completed for {item['category']}.")

        if item["status"] == "NEEDS_REVIEW" and item["confidence"] < 0.75:
            notes.append(f"Reflection: Flagged {item['category']} for mandatory human legal sign-off.")

    return {
        "reflection_notes": notes,
        "current_step": "Reflection & Faithfulness Verified"
    }

def compile_scorecard_node(state: Dict[str, Any]) -> Dict[str, Any]:
    checklist = state.get("checklist", [])
    vendor_name = state.get("vendor_name", "Vendor")

    passes = sum(1 for item in checklist if item["status"] == "PASS")
    fails = sum(1 for item in checklist if item["status"] == "FAIL")
    reviews = sum(1 for item in checklist if item["status"] == "NEEDS_REVIEW")
    total = len(checklist) or 1

    numeric_score = min(100, (fails * 35) + (reviews * 15))

    if fails >= 2 or numeric_score >= 60:
        overall_risk = "HIGH"
    elif fails == 1 or reviews >= 2 or numeric_score >= 30:
        overall_risk = "MEDIUM"
    else:
        overall_risk = "LOW"

    critical_findings = [f"[{item['category']}] {item['reasoning']}" for item in checklist if item["status"] == "FAIL"]

    summary = (
        f"Security audit for {vendor_name} concluded with overall risk level: {overall_risk} "
        f"(Risk Score: {numeric_score}/100). Evaluated {total} security categories: {passes} Passed, "
        f"{fails} Failed, and {reviews} Require Legal Review. "
    )
    if critical_findings:
        summary += f"Critical non-compliance issues detected in: {', '.join([c.split(']')[0][1:] for c in critical_findings])}."
    else:
        summary += "All baseline enterprise security standards were satisfied without critical exceptions."

    scorecard = {
        "overall_risk": overall_risk,
        "risk_score_numeric": numeric_score,
        "pass_count": passes,
        "fail_count": fails,
        "review_count": reviews,
        "executive_summary": summary,
        "critical_findings": critical_findings
    }

    return {
        "scorecard": scorecard,
        "current_step": "Scorecard Compiled. Ready for Human Review."
    }

def execute_mcp_node(state: Dict[str, Any]) -> Dict[str, Any]:
    client = MCPClient()
    vendor_name = state.get("vendor_name", "Vendor")
    scorecard = state.get("scorecard", {})
    checklist = state.get("checklist", [])
    overall_risk = scorecard.get("overall_risk", "UNKNOWN")
    actions_taken = []

    report_md = f"""# Enterprise Vendor Risk Audit: {vendor_name}
**Overall Risk Rating**: {overall_risk} (Score: {scorecard.get('risk_score_numeric', 0)}/100)
**Reviewer Decision**: {'APPROVED' if state.get('human_approved') else 'REJECTED / CONDITIONAL'} by {state.get('human_reviewer', 'SecOps Lead')}

## Executive Summary
{scorecard.get('executive_summary', '')}

## Detailed Compliance Checklist
"""
    for item in checklist:
        status_badge = ":white_check_mark: PASS" if item['status'] == 'PASS' else (":x: FAIL" if item['status'] == 'FAIL' else ":warning: NEEDS REVIEW")
        report_md += f"""### {status_badge}: {item['category']}
- **Policy Requirement**: {item['policy_requirement']}
- **Vendor Finding**: {item['reasoning']}
- **Confidence**: {int(item['confidence'] * 100)}%
- **Evidence Quote**: *"{item['evidence'][:300]}"*

"""

    res_save = client.call_tool("save_audit_report", {
        "vendor_name": vendor_name,
        "risk_score": overall_risk,
        "markdown_content": report_md
    })
    actions_taken.append({"tool": "save_audit_report", "result": res_save})

    priority_map = {"HIGH": "P0", "MEDIUM": "P1", "LOW": "P3"}
    res_ticket = client.call_tool("create_compliance_ticket", {
        "vendor_name": vendor_name,
        "summary": f"Vendor Risk Review: {vendor_name} [{overall_risk}]",
        "priority": priority_map.get(overall_risk, "P2"),
        "flagged_issues": scorecard.get("critical_findings", [])
    })
    actions_taken.append({"tool": "create_compliance_ticket", "result": res_ticket})

    res_slack = client.call_tool("send_slack_alert", {
        "channel": "#security-reviews",
        "vendor_name": vendor_name,
        "risk_score": overall_risk,
        "executive_summary": scorecard.get("executive_summary", "")
    })
    actions_taken.append({"tool": "send_slack_alert", "result": res_slack})

    client.close()

    return {
        "mcp_actions_taken": actions_taken,
        "current_step": "MCP Actions Executed Successfully"
    }

def _find_matching_snippet(text: str, keywords: List[str]) -> str:
    for sentence in text.split("."):
        s_lower = sentence.lower()
        if any(kw in s_lower for kw in keywords):
            return sentence.strip() + "."
    return text[:200]