"""
MediSafe — Hospital Bill Analyzer
Streamlit entry point.

Run with: streamlit run app.py
"""

import logging

import streamlit as st

from ingestion.ocr import extract_text_from_file
from ingestion.parsers import parse_bill, parse_discharge_summary, parse_policy
from ingestion.vector_store import index_policy
from output.letter_generator import generate_hospital_letter, generate_insurer_letter
from output.pdf_export import letter_to_pdf_bytes
from reasoning.bill_auditor import audit_bill
from reasoning.contradiction_detector import detect_contradictions
from reasoning.policy_checker import check_policy
from shared.models import ConfidenceLevel, FullAnalysis

logging.basicConfig(level=logging.INFO)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="MediSafe — Hospital Bill Analyzer",
    page_icon="🏥",
    layout="wide",
)

# ── Header ────────────────────────────────────────────────────────────────────

st.title("🏥 MediSafe")
st.subheader("Know what you're paying for. Challenge what's wrong.")
st.caption(
    "Upload your hospital bill, discharge summary, and insurance policy. "
    "Get a full analysis and ready-to-use dispute letters in under 10 minutes."
)
st.divider()

# ── Confidence legend ─────────────────────────────────────────────────────────

with st.expander("How to read the results"):
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown("🔴 **Verified overcharge**\nBenchmark data confirms overcharge >30%")
    col2.markdown("🟡 **Suspected overcharge**\nNo benchmark — item looks suspicious")
    col3.markdown("🟢 **Appears fair**\nAt or below benchmark rate")
    col4.markdown("⚪ **Unverifiable**\nNo benchmark data available")

# ── File upload ───────────────────────────────────────────────────────────────

st.markdown("### Step 1 — Upload your documents")
col1, col2, col3 = st.columns(3)

with col1:
    bill_file = st.file_uploader(
        "Hospital Bill",
        type=["pdf", "jpg", "jpeg", "png"],
        help="The final bill from the hospital, including all line items",
    )

with col2:
    discharge_file = st.file_uploader(
        "Discharge Summary",
        type=["pdf", "jpg", "jpeg", "png"],
        help="The discharge summary document given at the time of discharge",
    )

with col3:
    policy_file = st.file_uploader(
        "Insurance Policy",
        type=["pdf", "jpg", "jpeg", "png"],
        help="Your health insurance policy document",
    )

st.markdown("### Step 2 — Paste insurer rejection reasons")
rejection_input = st.text_area(
    "Paste the rejection reasons from the insurer's letter (one per line)",
    placeholder=(
        "Non-payable items as per Schedule IV\n"
        "Room rent capping applied\n"
        "Pre-existing condition exclusion"
    ),
    height=120,
)

# ── Analyze button ────────────────────────────────────────────────────────────

st.markdown("### Step 3 — Analyze")
ready = bill_file and discharge_file and policy_file
if not ready:
    st.info("Please upload all three documents to enable analysis.")

if st.button("Analyze Bill", type="primary", disabled=not ready):

    with st.status("Running analysis...", expanded=True) as status:

        st.write("📄 Reading documents...")
        bill_text = extract_text_from_file(bill_file.read(), bill_file.name)
        discharge_text = extract_text_from_file(discharge_file.read(), discharge_file.name)
        policy_text = extract_text_from_file(policy_file.read(), policy_file.name)

        st.write("🔍 Parsing documents...")
        parsed_bill = parse_bill(bill_text)
        parsed_discharge = parse_discharge_summary(discharge_text)
        parsed_policy = parse_policy(policy_text)

        st.write("📊 Indexing policy for semantic search...")
        index_policy(policy_text)

        st.write("💰 Auditing bill against CGHS benchmarks...")
        audit = audit_bill(parsed_bill)

        rejection_reasons = [r.strip() for r in rejection_input.split("\n") if r.strip()]
        st.write("📋 Checking insurer rejections against IRDAI rules...")
        policy_check = check_policy(parsed_bill, parsed_policy, rejection_reasons)

        st.write("🔎 Detecting contradictions between bill and discharge summary...")
        contradictions = detect_contradictions(parsed_bill, parsed_discharge)

        analysis = FullAnalysis(
            parsed_bill=parsed_bill,
            parsed_policy=parsed_policy,
            audit=audit,
            policy_check=policy_check,
            contradictions=contradictions,
            total_contestable_amount=(
                audit.verified_overcharge_total + policy_check.recoverable_amount
            ),
        )

        st.session_state["analysis"] = analysis
        status.update(label="Analysis complete!", state="complete")

# ── Results ───────────────────────────────────────────────────────────────────

if "analysis" in st.session_state:
    analysis: FullAnalysis = st.session_state["analysis"]

    st.divider()
    st.markdown("## Results")

    # Summary banner
    contestable = analysis.total_contestable_amount
    if contestable > 0:
        st.error(
            f"⚠️ Total contestable amount: **₹{contestable:,.0f}** "
            f"(verified overcharges + wrongful insurance rejections)"
        )
    else:
        st.success("No significant overcharges or wrongful rejections detected.")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["💰 Bill Audit", "📋 Policy Check", "🔎 Contradictions", "📝 Dispute Letters"]
    )

    # ── Tab 1: Bill Audit ─────────────────────────────────────────────────────
    with tab1:
        st.subheader("Bill audit summary")
        st.info(analysis.audit.summary)

        m1, m2, m3 = st.columns(3)
        m1.metric(
            "Verified overcharges",
            f"₹{analysis.audit.verified_overcharge_total:,.0f}",
            help="Confirmed by CGHS/NPPA benchmark data",
        )
        m2.metric(
            "Suspected overcharges",
            f"₹{analysis.audit.suspected_overcharge_total:,.0f}",
            help="No benchmark, but items are suspiciously vague or high",
        )
        m3.metric(
            "Unverifiable",
            f"₹{analysis.audit.unverifiable_total:,.0f}",
            help="No benchmark data available for these items",
        )

        st.markdown("#### Line-by-line breakdown")
        for item in analysis.audit.line_items:
            icon = {
                ConfidenceLevel.VERIFIED_OVERCHARGE: "🔴",
                ConfidenceLevel.SUSPECTED_OVERCHARGE: "🟡",
                ConfidenceLevel.APPEARS_FAIR: "🟢",
                ConfidenceLevel.UNVERIFIABLE: "⚪",
            }[item.confidence]

            label = f"{icon} **{item.description}** — ₹{item.billed_amount:,.0f}"
            with st.expander(label):
                cols = st.columns(3)
                cols[0].metric("Billed", f"₹{item.billed_amount:,.0f}")
                if item.cghs_rate:
                    cols[1].metric("CGHS benchmark", f"₹{item.cghs_rate:,.0f}")
                if item.overcharge_amount:
                    cols[2].metric(
                        "Overcharge",
                        f"₹{item.overcharge_amount:,.0f}",
                        delta=f"-₹{item.overcharge_amount:,.0f}",
                        delta_color="inverse",
                    )
                if item.flag_reason:
                    st.caption(f"Reason: {item.flag_reason}")
                st.caption(f"Confidence: `{item.confidence.value}`")

    # ── Tab 2: Policy Check ───────────────────────────────────────────────────
    with tab2:
        st.subheader("Insurance policy check")
        st.info(analysis.policy_check.summary)

        if analysis.policy_check.wrongful_rejections:
            st.error(f"**{len(analysis.policy_check.wrongful_rejections)} wrongful rejection(s) found**")
            for r in analysis.policy_check.wrongful_rejections:
                st.markdown(f"- {r}")

        if analysis.policy_check.irdai_violations:
            st.warning("**IRDAI regulatory violations by insurer:**")
            for v in analysis.policy_check.irdai_violations:
                st.markdown(f"- {v}")

        if analysis.policy_check.valid_rejections:
            with st.expander("Valid rejections (not contested)"):
                for r in analysis.policy_check.valid_rejections:
                    st.markdown(f"- {r}")

        st.metric(
            "Estimated recoverable from insurer",
            f"₹{analysis.policy_check.recoverable_amount:,.0f}",
        )

    # ── Tab 3: Contradictions ─────────────────────────────────────────────────
    with tab3:
        st.subheader("Bill vs discharge summary")
        st.info(analysis.contradictions.summary)

        if analysis.contradictions.specialist_discrepancy:
            st.error(f"**Specialist count mismatch:** {analysis.contradictions.specialist_discrepancy}")
        if analysis.contradictions.medicine_discrepancy:
            st.warning(f"**Medicine discrepancy:** {analysis.contradictions.medicine_discrepancy}")
        if analysis.contradictions.procedure_discrepancy:
            st.warning(f"**Procedure discrepancy:** {analysis.contradictions.procedure_discrepancy}")
        if not analysis.contradictions.contradictions_found:
            st.success("No significant contradictions detected between the bill and discharge summary.")

    # ── Tab 4: Letters ────────────────────────────────────────────────────────
    with tab4:
        st.subheader("Dispute letters")
        st.caption(
            "Generate ready-to-use letters. Hand the hospital letter to the billing manager. "
            "Send the insurer notice to the grievance cell."
        )

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**Hospital dispute letter**")
            st.caption("Cite specific overcharges. Request itemized breakdown within 2 hours.")
            if st.button("Generate hospital letter", key="hosp_btn"):
                with st.spinner("Drafting..."):
                    letter = generate_hospital_letter(analysis)
                st.session_state["hospital_letter"] = letter

            if "hospital_letter" in st.session_state:
                st.text_area(
                    "Hospital letter",
                    st.session_state["hospital_letter"],
                    height=400,
                    key="hosp_text",
                )
                pdf_bytes = letter_to_pdf_bytes(
                    st.session_state["hospital_letter"], "Hospital Dispute Letter"
                )
                st.download_button(
                    "⬇️ Download as PDF",
                    data=pdf_bytes,
                    file_name="hospital_dispute_letter.pdf",
                    mime="application/pdf",
                )

        with col_b:
            st.markdown("**Insurer escalation notice**")
            st.caption("Cites IRDAI circulars. Send to insurer grievance cell.")
            if st.button("Generate insurer notice", key="ins_btn"):
                with st.spinner("Drafting..."):
                    letter = generate_insurer_letter(analysis)
                st.session_state["insurer_letter"] = letter

            if "insurer_letter" in st.session_state:
                st.text_area(
                    "Insurer notice",
                    st.session_state["insurer_letter"],
                    height=400,
                    key="ins_text",
                )
                pdf_bytes = letter_to_pdf_bytes(
                    st.session_state["insurer_letter"], "Insurer Escalation Notice"
                )
                st.download_button(
                    "⬇️ Download as PDF",
                    data=pdf_bytes,
                    file_name="insurer_escalation_notice.pdf",
                    mime="application/pdf",
                )

    st.divider()
    st.caption(
        "⚠️ This analysis is based on publicly available CGHS rate data and IRDAI guidelines. "
        "Rates may lag 6–18 months. This is not legal advice. "
        "Consult a professional for formal consumer court proceedings."
    )
