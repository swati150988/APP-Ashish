import io

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ----------------------------- PAGE SETUP ---------------------------------
st.set_page_config(
    page_title="UPSC APFC Selection Engine",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎯 UPSC APFC Selection Engine & Analytics Dashboard")
st.markdown(
    """
    Track mock-test performance, estimate topic mastery, review subject-wise
    progress, and export a PDF report. The estimates below are planning aids,
    not official UPSC predictions or verified historical cut-offs.
    """
)

# ----------------------------- MODEL DATA ---------------------------------
MODEL_METADATA = {
    "Industrial Relations & Labour Laws (IRL)": {
        "weight": 37.5,
        "topics": {
            "New Labour Codes (Wages, IR, SS, OSH)": 15.0,
            "Core IR Acts (IDA, TUA, etc.)": 10.0,
            "Social Security Schemes & Core Concepts": 7.5,
            "Constitutional Provisions & Labour History": 5.0,
        },
    },
    "Accountancy, Auditing & Insurance (AAI)": {
        "weight": 37.5,
        "topics": {
            "Accounting Principles & Corporate Accounting": 17.5,
            "Auditing Practices & Standards": 12.5,
            "Basic Insurance & Risk Management Concepts": 7.5,
        },
    },
    "Governance & Indian Polity (POL)": {
        "weight": 22.5,
        "topics": {
            "Fundamental Rights, DPSPs & Fundamental Duties": 10.0,
            "Union & State Executive, Legislature & Judiciary": 7.5,
            "Statutory, Non-Statutory Bodies & Governance Issues": 5.0,
        },
    },
    "Culture, Heritage & Freedom Movement (HIS)": {
        "weight": 25.0,
        "topics": {
            "Modern Indian Freedom Struggle (Post 1857)": 15.0,
            "Indian Art, Culture, Architecture & Literature": 7.5,
            "Ancient & Medieval Chronology Markers": 2.5,
        },
    },
    "Present Trends in Economy & Development (ECO)": {
        "weight": 20.0,
        "topics": {
            "Fiscal & Monetary Policy Frameworks": 7.5,
            "Population, Growth, Globalization & Development": 7.5,
            "Banking Sector & Financial System Trends": 5.0,
        },
    },
    "Math, Quant, Stats & Mental Ability (MQS)": {
        "weight": 37.5,
        "topics": {
            "Core Arithmetic & Quantitative Techniques": 17.5,
            "Data Interpretation Arrays": 12.5,
            "Probability & Descriptive/Inferential Statistics": 7.5,
        },
    },
    "General English Competency (ENG)": {
        "weight": 50.0,
        "topics": {
            "Vocabulary Matrices (Synonyms, Antonyms, Idioms)": 20.0,
            "Applied Grammar & Error Spotting Protocols": 17.5,
            "Sentence Rearrangement & Comprehension Precision": 12.5,
        },
    },
    "General Science & Computer Applications (SCI)": {
        "weight": 42.5,
        "topics": {
            "Computer Fundamentals & Architecture/Networking": 22.5,
            "General Science Basic Applied Principles": 20.0,
        },
    },
}

# ----------------------------- SESSION STATE ------------------------------
if "test_history" not in st.session_state:
    st.session_state.test_history = pd.DataFrame(
        columns=["Mock Test Name", "Written Score", "Interview Score", "Predicted Total"]
    )

for subject_data in MODEL_METADATA.values():
    for topic in subject_data["topics"]:
        st.session_state.setdefault(f"mastery_{topic}", 0.60)

# ----------------------------- SIDEBAR ------------------------------------
st.sidebar.header("📊 Global Parameters")
interview_mastery = st.sidebar.slider(
    "Interview Mastery (x_INT)", 0.0, 1.0, 0.50, 0.05
)
error_term = st.sidebar.slider(
    "Exam-Day Adjustment (marks)", -30.0, 10.0, -10.0, 0.5
)
intercept = st.sidebar.number_input("Model Intercept (marks)", value=0.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🏆 Target Benchmark")
st.sidebar.info(
    "**Illustrative target zone:** 240–250 marks out of 400. "
    "This is a user-configurable planning benchmark, not a guaranteed or "
    "official selection threshold."
)

# ----------------------------- TABS ---------------------------------------
tracker_tab, models_tab, dashboard_tab, charts_tab = st.tabs(
    [
        "📝 Mock Test Tracker",
        "🧬 Subject Mastery Models",
        "📈 Dashboard & Prediction",
        "📊 Performance Trends",
    ]
)

# ----------------------------- MOCK TRACKER -------------------------------
with tracker_tab:
    st.header("📝 Topic-Wise Mock Test Tracker")
    st.caption(
        "Enter correct and incorrect answers. Mastery is estimated as "
        "(correct − incorrect/3) ÷ attempted questions, bounded between 0 and 1."
    )
    test_name = st.text_input(
        "Mock Test Log Label",
        value=f"Mock Test #{len(st.session_state.test_history) + 1}",
    )
    selected_subject = st.selectbox(
        "Select subject to log", list(MODEL_METADATA.keys())
    )

    st.markdown(f"#### Subtopic scores: {selected_subject}")
    col1, col2 = st.columns(2)
    topic_items = list(MODEL_METADATA[selected_subject]["topics"].items())

    for idx, (topic, weight) in enumerate(topic_items):
        with (col1 if idx % 2 == 0 else col2):
            st.markdown(f"**{topic}**")
            c1, c2 = st.columns(2)
            correct = c1.number_input(
                f"Correct — {topic}", min_value=0, value=6, step=1,
                key=f"correct_{topic}",
            )
            incorrect = c2.number_input(
                f"Incorrect — {topic}", min_value=0, value=3, step=1,
                key=f"incorrect_{topic}",
            )
            attempted = correct + incorrect
            if attempted:
                mastery = max(0.0, min(1.0, (correct - incorrect / 3) / attempted))
            else:
                mastery = 0.60
            st.caption(f"Estimated mastery: **{mastery:.2f}**")
            st.session_state[f"pending_mastery_{topic}"] = mastery

    if st.button("💾 Apply tracker scores and save mock test", type="primary"):
        for topic, _ in topic_items:
            st.session_state[f"mastery_{topic}"] = st.session_state[
                f"pending_mastery_{topic}"
            ]
        st.session_state["save_mock_test"] = True
        st.success("Tracker scores applied. The dashboard and report now use these values.")

# ----------------------------- MANUAL MASTERY -----------------------------
with models_tab:
    st.header("🧬 Manual Subject Mastery Adjustments")
    st.caption("Adjust any topic between 0% and 100%. These values feed the dashboard.")
    for subject, data in MODEL_METADATA.items():
        with st.expander(f"📚 {subject} — allocation: {data['weight']:.1f} marks"):
            left, right = st.columns([3, 1])
            subject_total = 0.0
            for topic, weight in data["topics"].items():
                value = left.slider(
                    f"{topic} (weight: {weight:g})",
                    min_value=0.0,
                    max_value=1.0,
                    value=float(st.session_state[f"mastery_{topic}"]),
                    step=0.01,
                    key=f"manual_{topic}",
                )
                st.session_state[f"mastery_{topic}"] = value
                contribution = value * weight
                subject_total += contribution
                right.metric(topic[:24] + ("…" if len(topic) > 24 else ""), f"{contribution:.2f}")
            st.markdown(
                f"**Estimated subject yield:** {subject_total:.2f} / {data['weight']:.2f} marks"
            )

# ----------------------------- SCORE CALCULATION --------------------------
mastery_scores = {
    topic: float(st.session_state[f"mastery_{topic}"])
    for data in MODEL_METADATA.values()
    for topic in data["topics"]
}

written_yields = {}
total_written_score = 0.0
for subject, data in MODEL_METADATA.items():
    subject_score = sum(
        mastery_scores[topic] * weight
        for topic, weight in data["topics"].items()
    )
    written_yields[subject] = subject_score
    total_written_score += subject_score

interview_yield = interview_mastery * 100.0
final_predicted_y = (
    intercept + total_written_score + interview_yield + error_term
)

breakdown_data = []
for subject, data in MODEL_METADATA.items():
    max_marks = data["weight"]
    actual_yield = written_yields[subject]
    realization_pct = actual_yield / max_marks * 100 if max_marks else 0.0
    breakdown_data.append(
        {
            "Subject Domain Cluster": subject,
            "Max Marks": max_marks,
            "Estimated Score": round(actual_yield, 2),
            "Realization": f"{realization_pct:.1f}%",
        }
    )

breakdown_data.append(
    {
        "Subject Domain Cluster": "Interview / Personality Stage",
        "Max Marks": 100.0,
        "Estimated Score": round(interview_yield, 2),
        "Realization": f"{interview_mastery * 100:.1f}%",
    }
)

urgency_rows = []
for subject, data in MODEL_METADATA.items():
    for topic, weight in data["topics"].items():
        urgency_rows.append(
            {
                "Topic": topic,
                "Subject": subject,
                "Potential Gain": (1.0 - mastery_scores[topic]) * weight,
                "Current Mastery": mastery_scores[topic],
            }
        )
urgency_df = pd.DataFrame(urgency_rows).sort_values(
    "Potential Gain", ascending=False
).head(5)

# ----------------------------- SAVE TEST ----------------------------------
if st.session_state.pop("save_mock_test", False):
    new_row = {
        "Mock Test Name": test_name,
        "Written Score": round(total_written_score, 2),
        "Interview Score": round(interview_yield, 2),
        "Predicted Total": round(final_predicted_y, 2),
    }
    st.session_state.test_history = pd.concat(
        [st.session_state.test_history, pd.DataFrame([new_row])],
        ignore_index=True,
    )

# ----------------------------- DASHBOARD ----------------------------------
with dashboard_tab:
    st.header("📈 Predictive Analytics Dashboard")
    k1, k2, k3 = st.columns(3)
    k1.metric("Written Test Yield (out of 300)", f"{total_written_score:.2f}")
    k2.metric("Interview Yield (out of 100)", f"{interview_yield:.2f}")
    if final_predicted_y >= 240:
        k3.metric(
            "Predicted Total (out of 400)",
            f"{final_predicted_y:.2f}",
            delta="At or above illustrative benchmark",
        )
    else:
        k3.metric(
            "Predicted Total (out of 400)",
            f"{final_predicted_y:.2f}",
            delta=f"{240 - final_predicted_y:.2f} below illustrative benchmark",
            delta_color="inverse",
        )

    progress = max(0.0, min(1.0, final_predicted_y / 240.0))
    st.markdown(f"**Progress toward 240-mark benchmark:** {progress * 100:.1f}%")
    st.progress(progress)

    st.subheader("📋 Subject Breakdown")
    st.dataframe(pd.DataFrame(breakdown_data), use_container_width=True)

    st.subheader("⚡ Highest-Potential Revision Priorities")
    st.dataframe(
        urgency_df[["Topic", "Subject", "Current Mastery", "Potential Gain"]],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("📄 Export Progress Report")
    st.write("Generate a PDF snapshot of the current dashboard and revision priorities.")

    def generate_pdf_report():
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            spaceAfter=15,
            textColor=colors.HexColor("#1B365D"),
        )
        heading_style = ParagraphStyle(
            "ReportHeading",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            spaceBefore=12,
            spaceAfter=8,
            textColor=colors.HexColor("#2C3E50"),
        )
        body_style = ParagraphStyle(
            "ReportBody", parent=styles["BodyText"], fontSize=9, leading=12
        )
        story = [
            Paragraph("UPSC APFC Selection Engine — Progress Report", title_style),
            Paragraph(
                f"Estimated aggregate score: {final_predicted_y:.2f} / 400",
                body_style,
            ),
            Paragraph(
                f"Written estimate: {total_written_score:.2f} / 300 | "
                f"Interview estimate: {interview_yield:.2f} / 100",
                body_style,
            ),
            Paragraph(f"Exam-day adjustment: {error_term:.2f} marks", body_style),
            Paragraph("Subject score breakdown", heading_style),
        ]
        table_data = [["Subject", "Maximum", "Estimated yield", "Realization"]]
        for row in breakdown_data:
            table_data.append(
                [
                    row["Subject Domain Cluster"],
                    f'{row["Max Marks"]:.1f}',
                    f'{row["Estimated Score"]:.2f}',
                    row["Realization"],
                ]
            )
        report_table = Table(
            table_data,
            colWidths=[245, 65, 80, 75],
            repeatRows=1,
        )
        report_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B365D")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5DDE5")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6F9")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(report_table)
        story.append(Paragraph("Top revision priorities", heading_style))
        for _, row in urgency_df.iterrows():
            story.append(
                Paragraph(
                    f'{row["Topic"]} ({row["Subject"]}) — '
                    f'Mastery: {row["Current Mastery"] * 100:.1f}%; '
                    f'potential gain: {row["Potential Gain"]:.2f} marks',
                    body_style,
                )
            )
        story.extend(
            [
                Spacer(1, 16),
                Paragraph(
                    "Disclaimer: This is an illustrative study-planning estimate, "
                    "not an official UPSC score prediction or selection guarantee.",
                    body_style,
                ),
            ]
        )
        doc.build(story)
        buffer.seek(0)
        return buffer

    st.download_button(
        "📥 Download PDF Progress Report",
        data=generate_pdf_report(),
        file_name="APFC_Performance_Report.pdf",
        mime="application/pdf",
    )

# ----------------------------- PERFORMANCE CHARTS ------------------------
with charts_tab:
    st.header("📊 Performance Trends")
    history = st.session_state.test_history
    if history.empty:
        st.info("Save a mock-test run in the tracker tab to see your score trend.")
    else:
        st.subheader("Predicted total across saved mock tests")
        chart_data = history.copy()
        chart_data.index = range(1, len(chart_data) + 1)
        st.line_chart(chart_data["Predicted Total"])
        st.subheader("Saved mock-test history")
        st.dataframe(history, use_container_width=True, hide_index=True)

