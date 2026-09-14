"""
LangGraph State Definitions for Vendor Risk Auditor.
"""
from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


class ChecklistItem(BaseModel):
    clause_id: str
    category: str
    policy_requirement: str
    vendor_claim: str
    status: str = Field(description="PASS, FAIL, or NEEDS_REVIEW")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    evidence: str = Field(description="Direct verbatim quote from vendor doc")
    reasoning: str = Field(description="Explanation of why it passed or failed")


class RiskScorecard(BaseModel):
    overall_risk: str = Field(description="LOW, MEDIUM, or HIGH")
    risk_score_numeric: int = Field(description="0 to 100, where 0 is safest, 100 is highest risk")
    pass_count: int = 0
    fail_count: int = 0
    review_count: int = 0
    executive_summary: str = ""
    critical_findings: List[str] = []


class RiskAuditState(TypedDict):
    vendor_name: str
    document_path: str
    document_text: str
    sections: List[Dict[str, str]]
    extracted_clauses: List[Dict[str, Any]]
    retrieved_policies: Dict[str, Any]
    checklist: List[Dict[str, Any]]
    reflection_notes: List[str]
    scorecard: Dict[str, Any]
    human_approved: bool
    human_reviewer: str
    human_feedback: str
    mcp_actions_taken: List[Dict[str, Any]]
    current_step: str
    llm_provider: str  # FIX: was missing — caused TypedDict violation when app.py passed this key
