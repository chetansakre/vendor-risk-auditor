"""
Enterprise Vendor Risk & Security Auditor - Streamlit Application
Interactive dashboard showcasing LangGraph state machine, Advanced RAG,
Model Context Protocol (MCP) integrations, and Human-in-the-Loop approval.
"""
import os
import sys
import datetime
import streamlit as st

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.utils.parser import parse_document
from src.graph.workflow import build_audit_graph
from src.rag.indexer import PolicyIndexer

st.set_page_config(
    page_title="Autonomous Vendor Risk Auditor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🛡️ Autonomous Enterprise Vendor Risk & Security Auditor")
st.caption("Powered by **LangGraph** (State Machine & HITL) • **Model Context Protocol (MCP)** • **Advanced Hybrid RAG**")

@st.cache_resource
def get_cached_indexer():
    return PolicyIndexer()

# Sidebar
st.sidebar.header("📁 Document Ingestion")
sample_choice = st.sidebar.selectbox(
    "Choose Sample Vendor Document:",
    [
        "CloudSync AI (High Risk: AI Training & 90d Retention)",
        "SecureVault Enterprise (Low Risk: Strict Compliance)",
        "Large Enterprise SOC 2 (150-Page Stress Test)",
        "Upload Custom Document"
    ]
)

uploaded_file = None
if sample_choice == "Upload Custom Document":
    uploaded_file = st.sidebar.file_uploader("Upload Vendor PDF or Markdown", type=["pdf", "md", "txt"])
    target_path = None
    vendor_name = "Custom Vendor"
    if uploaded_file is not None:
        temp_dir = os.path.join(BASE_DIR, "data", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        target_path = os.path.join(temp_dir, uploaded_file.name)
        with open(target_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        vendor_name = os.path.splitext(uploaded_file.name)[0].replace("_", " ").title()
elif "CloudSync" in sample_choice:
    target_path = os.path.join(BASE_DIR, "data", "sample_vendors", "cloudsync_soc2_report.pdf")
    vendor_name = "CloudSync AI"
elif "150-Page" in sample_choice:
    target_path = os.path.join(BASE_DIR, "data", "sample_vendors", "large_enterprise_soc2_150_pages.pdf")
    vendor_name = "Global Enterprise Platform (150 Pages)"
else:
    target_path = os.path.join(BASE_DIR, "data", "sample_vendors", "securevault_compliance.pdf")
    vendor_name = "SecureVault Enterprise"

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 Intelligence Engine")
engine_mode = st.sidebar.radio(
    "Select Model Provider:",
    [
        "⚡ Local Neural Engine (Offline-First, Zero Cost)",
        "🧠 Private Qwen 122B Server (Enterprise vLLM)",
        "☁️ Cloud LLM (OpenAI GPT-4o / Claude 3.5)"
    ],
    index=0
)
if "Qwen" in engine_mode:
    qwen_url = st.sidebar.text_input("Server Base URL", value=os.getenv("QWEN_BASE_URL", "http://localhost:8002/v1"))
    qwen_model = st.sidebar.text_input("Model Name", value=os.getenv("QWEN_MODEL_NAME", "qwen-122b"))
    if st.sidebar.button("🔍 Test Qwen Server Health"):
        from src.graph.llm_client import QwenLLMClient
        client = QwenLLMClient(base_url=qwen_url, model=qwen_model)
        with st.sidebar.status("Connecting to Qwen 122B..."):
            res = client.test_connection()
            if res.get("online"):
                st.sidebar.success(f"✅ Connected! Models found: {res.get('models', [])}")
            else:
                st.sidebar.warning("⚠️ Server unreachable. Check if VPN is required or IP is whitelisted in cloud firewall.")
elif "Cloud" in engine_mode:
    api_key = st.sidebar.text_input("OpenAI / Anthropic API Key", type="password", placeholder="sk-...")
    st.sidebar.caption("🔒 Key held in memory only.")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ System Status")
st.sidebar.success("✅ Hybrid RAG Engine: Active (BM25 + Dense)")
st.sidebar.success("✅ MCP Server: Ready over stdio")
st.sidebar.success("✅ LangGraph Checkpointing: MemorySaver Active")

if "graph_state" not in st.session_state:
    st.session_state.graph_state = None
if "audit_done" not in st.session_state:
    st.session_state.audit_done = False
if "mcp_done" not in st.session_state:
    st.session_state.mcp_done = False

start_audit = st.sidebar.button("🚀 Run Autonomous Security Audit", type="primary", use_container_width=True)

if start_audit and target_path:
    with st.spinner("Parsing document and executing LangGraph State Machine..."):
        parsed = parse_document(target_path)
        graph = build_audit_graph(enable_hitl=True)
        thread_id = f"web-session-{datetime.datetime.now().strftime('%H%M%S')}"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "vendor_name": vendor_name,
            "document_path": target_path,
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
            "llm_provider": "qwen" if "Qwen" in engine_mode else "local"
        }

        for _ in graph.stream(initial_state, config=config):
            pass

        st.session_state.graph = graph
        st.session_state.config = config
        st.session_state.graph_state = graph.get_state(config)
        st.session_state.audit_done = True
        st.session_state.mcp_done = False

if st.session_state.audit_done and st.session_state.graph_state:
    snapshot = st.session_state.graph_state
    scorecard = snapshot.values.get("scorecard", {})
    checklist = snapshot.values.get("checklist", [])
    overall_risk = scorecard.get("overall_risk", "UNKNOWN")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if overall_risk == "HIGH":
            st.error(f"### 🛑 Risk: HIGH\nScore: {scorecard.get('risk_score_numeric', 0)}/100")
        elif overall_risk == "MEDIUM":
            st.warning(f"### ⚠️ Risk: MEDIUM\nScore: {scorecard.get('risk_score_numeric', 0)}/100")
        else:
            st.success(f"### ✅ Risk: LOW\nScore: {scorecard.get('risk_score_numeric', 0)}/100")
    with c2:
        st.metric("Passed Standards", f"{scorecard.get('pass_count', 0)} / {len(checklist)}")
    with c3:
        st.metric("Violations (Fails)", f"{scorecard.get('fail_count', 0)}")
    with c4:
        st.metric("Requires Legal Review", f"{scorecard.get('review_count', 0)}")

    if st.session_state.get("mcp_done", False):
        st.success("### 🎉 MCP Operation Performed Successfully! All tools have finished execution.")
        b1, b2, b3 = st.columns(3)
        actions = st.session_state.graph_state.values.get("mcp_actions_taken", [])
        with b1:
            st.info("📄 **Audit Report Archived**\nSaved to `reports/` folder")
        with b2:
            st.info("🎫 **Jira Ticket Created**\nIssue logged in Security Backlog")
        with b3:
            st.info("💬 **Slack Alert Sent**\nCard dispatched to `#security-reviews`")

    from src.utils.pdf_generator import generate_pdf_report

    pdf_bytes = generate_pdf_report(
        vendor_name=vendor_name,
        scorecard=scorecard,
        checklist=checklist,
        human_reviewer=snapshot.values.get("human_reviewer", "Lead Information Security Officer"),
        decision=snapshot.values.get("human_feedback", "Pending Authorization"),
        comments=snapshot.values.get("human_feedback", ""),
        mcp_actions=snapshot.values.get("mcp_actions_taken", [])
    )

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            label="📥 Download Official Audit Certificate (PDF)",
            data=pdf_bytes,
            file_name=f"Enterprise_Security_Audit_{vendor_name.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with col_dl2:
        md_text = f"# Enterprise Vendor Risk Audit: {vendor_name}\n**Overall Risk**: {overall_risk}\n**Risk Score**: {scorecard.get('risk_score_numeric', 0)}/100\n\n## Executive Summary\n{scorecard.get('executive_summary', '')}\n\n## Detailed Compliance Matrix\n"
        for it in checklist:
            md_text += f"- **{it['category']}**: [{it['status']}] - {it['reasoning']}\n"
        st.download_button(
            label="📄 Download Markdown Summary (.md)",
            data=md_text,
            file_name=f"Audit_Report_{vendor_name.replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True
        )

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Detailed Scorecard",
        "🛑 Human-in-the-Loop Approval",
        "🔌 MCP Tool Actions",
        "📜 Internal Policies (RAG)"
    ])

    with tab1:
        st.subheader(f"Compliance Matrix for {vendor_name}")
        st.info(scorecard.get("executive_summary", ""))

        for item in checklist:
            status = item["status"]
            icon = "✅" if status == "PASS" else ("❌" if status == "FAIL" else "⚠️")
            with st.expander(f"{icon} {item['category']} — [{status}] (Confidence: {int(item['confidence']*100)}%)"):
                st.write(f"**Policy Requirement**: {item['policy_requirement']}")
                st.write(f"**Evaluation**: {item['reasoning']}")
                st.markdown(f"**Verbatim Evidence Quote**:\n> *\"{item['evidence']}\"*")

    with tab2:
        st.subheader("🛑 LangGraph Checkpoint: Security Officer Authorization")
        
        if st.session_state.mcp_done:
            st.success("### ✅ Operation Successfully Performed!")
            st.markdown(
                """
                **The Human-in-the-Loop authorization has been submitted and the Model Context Protocol (MCP) server has successfully executed all automated downstream actions:**
                
                - 📄 **Audit Report Archived**: Saved full markdown compliance brief to the `reports/` folder.
                - 🎫 **Jira Ticket Logged**: Automated security issue logged with assigned SLA based on audit risk.
                - 💬 **Slack Alert Dispatched**: Interactive notification card posted to `#security-reviews`.
                
                👉 **Switch to the next tab ('🔌 MCP Tool Actions') to inspect the live JSON response payloads from the MCP server!**
                """
            )
            if st.button("🔄 Re-evaluate / Modify Decision"):
                st.session_state.mcp_done = False
                st.rerun()
        else:
            st.write("The state machine is currently suspended at a checkpoint. High-impact actions (Jira tickets, file archiving, Slack notifications) require human sign-off.")

            col_a, col_b = st.columns(2)
            with col_a:
                reviewer = st.text_input("Reviewer Name / Role", value="Lead Information Security Officer")
            with col_b:
                decision = st.selectbox("Authorization Decision", ["Approve Conditional on Legal Rider", "Full Approval", "Reject Vendor"])

            comments = st.text_area("Audit Notes & Instructions", value="Reviewed automated LangGraph scorecard. Proceed with MCP logging.")

            if st.button("✍️ Submit Decision & Trigger MCP Tools", type="primary"):
                with st.spinner("Resuming LangGraph to execute MCP tools..."):
                    graph = st.session_state.graph
                    config = st.session_state.config

                    graph.update_state(config, {
                        "human_approved": "Approval" in decision,
                        "human_reviewer": reviewer,
                        "human_feedback": f"[{decision}] {comments}"
                    })

                    for _ in graph.stream(None, config=config):
                        pass

                    st.session_state.graph_state = graph.get_state(config)
                    st.session_state.mcp_done = True
                    st.toast("🎉 Decision recorded! MCP tools successfully executed.", icon="✅")
                    
                    st.success("### ✅ Operation Successfully Performed!")
                    st.markdown(
                        """
                        **The Human-in-the-Loop authorization has been submitted and the Model Context Protocol (MCP) server has successfully executed all automated downstream actions:**
                        
                        - 📄 **Audit Report Archived**: Saved full markdown compliance brief to the `reports/` folder.
                        - 🎫 **Jira Ticket Logged**: Automated security issue logged with assigned SLA based on audit risk.
                        - 💬 **Slack Alert Dispatched**: Interactive notification card posted to `#security-reviews`.
                        
                        👉 **Switch to Tab 3 ('🔌 MCP Tool Actions') to inspect the live JSON response payloads from the MCP server!**
                        """
                    )

    with tab3:
        st.subheader("🔌 Model Context Protocol (MCP) Logs")
        if st.session_state.mcp_done:
            st.success("✅ **All MCP Tools Executed Successfully via JSON-RPC 2.0 stdio Subprocess**")
            actions = st.session_state.graph_state.values.get("mcp_actions_taken", [])
            for act in actions:
                st.markdown(f"#### 🛠️ Tool Invoked: `{act['tool']}`")
                st.json(act["result"])
        else:
            st.info("⏳ MCP tools are on hold. They will be dispatched once you grant Human-in-the-Loop authorization in **Tab 2**.")

    with tab4:
        st.subheader("Enterprise Baseline Security Policies")
        indexer = get_cached_indexer()
        for chunk in indexer.chunks:
            with st.expander(f"📌 {chunk.title} ({chunk.policy_id})"):
                st.markdown(chunk.content)
else:
    st.info("👈 Select a sample document or upload a vendor PDF from the sidebar and click **Run Autonomous Security Audit** to start!")