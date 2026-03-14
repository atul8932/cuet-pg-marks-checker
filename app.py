import streamlit as st
import fitz
import re
import pandas as pd
import altair as alt

st.set_page_config(page_title="CUET Marks Checker", page_icon="🎓", layout="wide")

# Custom CSS for better aesthetics
st.markdown("""
<style>
    /* Gradient text for main title */
    .main-title {
        font-size: 3.5rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #4f46e5, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0px;
        padding-bottom: 0px;
    }
    .sub-title {
        text-align: center;
        color: #6b7280;
        font-size: 1.2rem;
        margin-top: 0px;
        margin-bottom: 40px;
        font-weight: 500;
    }
    
    /* Style for metrics */
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem;
        font-weight: bold;
    }
    
    /* Hide default Streamlit elements for a cleaner look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🎓 CUET Marks Checker</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Upload your Response Sheet & Answer Key to calculate your score instantly</p>', unsafe_allow_html=True)

# Layout for file uploaders
col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("### 📄 Response Sheet")
    st.info("Upload the PDF containing your recorded responses.")
    response_sheet_file = st.file_uploader("Response Sheet", type=["pdf"], label_visibility="collapsed")

with col2:
    st.markdown("### 🔐 Answer Key")
    st.info("Upload the official NTA Provisional Answer Key PDF.")
    answer_key_file = st.file_uploader("Answer Key", type=["pdf"], label_visibility="collapsed")


# PDF text extraction
@st.cache_data
def extract_text(file_bytes):
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)

# Answer Key: Question ID → Correct Option ID
@st.cache_data
def parse_answer_key(text):
    return dict(re.findall(r"(\d{10})\s+(\d{10})", text))

# Response Sheet Parser
@st.cache_data
def parse_response_sheet(text):
    lines = text.splitlines()
    blocks = []
    block = []

    for line in lines:
        line = line.strip()
        if "Question ID" in line and block:
            blocks.append(block)
            block = []
        block.append(line)
    if block:
        blocks.append(block)

    response_map = {}

    for block in blocks:
        qid = opt_ids = chosen = None
        options = [None] * 4

        for line in block:
            if "Question ID" in line:
                qid_match = re.search(r"(\d{10})", line)
                qid = qid_match.group(1) if qid_match else None
            for idx in range(4):
                if f"Option {idx+1} ID" in line:
                    opt_match = re.search(r"(\d{10})", line)
                    options[idx] = opt_match.group(1) if opt_match else None
            if "Chosen Option" in line:
                chosen_match = re.search(r"(\d+|Not Attempted)", line)
                chosen = chosen_match.group(1) if chosen_match else "Not Attempted"

        if qid:
            if chosen.lower().startswith("not") or not chosen.isdigit():
                response_map[qid] = "Unattempted"
            else:
                index = int(chosen) - 1
                response_map[qid] = options[index] if 0 <= index < 4 else "Unattempted"

    return response_map

st.divider()

if not (response_sheet_file and answer_key_file):
    # Empty State Instructions
    st.markdown("""
        <div style="background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0;">
            <h4>📌 How to use this tool:</h4>
            <ol>
                <li>Download your <b>Response Sheet</b> from the CUET portal.</li>
                <li>Download the official <b>Answer Key</b> PDF.</li>
                <li>Upload both files above.</li>
                <li>Your final score, detailed analysis, and a visual breakdown will appear instantly!</li>
            </ol>
            <p style="color: #64748b; font-size: 0.9em; margin-bottom: 0;"><i>Note: All processing happens locally. Your files are not saved or sent anywhere.</i></p>
        </div>
    """, unsafe_allow_html=True)

else:
    with st.spinner("🔄 Processing your files... please wait."):
        try:
            response_bytes = response_sheet_file.read()
            answer_bytes = answer_key_file.read()

            response_text = extract_text(response_bytes)
            answer_text = extract_text(answer_bytes)

            answer_map = parse_answer_key(answer_text)
            response_map = parse_response_sheet(response_text)

            correct = incorrect = unattempted = 0
            results = []

            for qid, correct_code in answer_map.items():
                user_code = response_map.get(qid, "Unattempted")

                if user_code == "Unattempted":
                    status = "Unattempted"
                    unattempted += 1
                elif user_code == correct_code:
                    status = "Correct"
                    correct += 1
                else:
                    status = "Incorrect"
                    incorrect += 1

                results.append({
                    "Question ID": qid,
                    "Your Option ID": user_code,
                    "Correct Option ID": correct_code,
                    "Status": status
                })

            score = correct * 4 - incorrect
            total_questions = len(answer_map)
            max_score = total_questions * 4
            
            # Score Cards
            st.markdown("### 🏆 Your Result Summary")
            
            mcol1, mcol2, mcol3, mcol4 = st.columns(4)
            mcol1.metric("🎯 Final Score", f"{score} / {max_score}")
            mcol2.metric("✅ Correct", f"{correct}", "+4 marks each")
            mcol3.metric("❌ Incorrect", f"{incorrect}", "-1 mark each")
            mcol4.metric("⚪ Unattempted", f"{unattempted}", "0 marks")
            
            st.markdown("---")
            
            # Layout for Charts and Detailed Table
            c1, c2 = st.columns([1, 2], gap="large")
            
            with c1:
                st.markdown("#### 📊 Accuracy Distribution")
                
                # Prepare data for Altair chart
                chart_data = pd.DataFrame({
                    "Status": ["Correct", "Incorrect", "Unattempted"],
                    "Count": [correct, incorrect, unattempted]
                })
                
                # Remove zero values to avoid empty slices in pie chart
                chart_data = chart_data[chart_data["Count"] > 0]
                
                if not chart_data.empty:
                    base = alt.Chart(chart_data).encode(
                        theta=alt.Theta("Count:Q", stack=True),
                        color=alt.Color("Status:N", scale=alt.Scale(
                            domain=["Correct", "Incorrect", "Unattempted"],
                            range=["#10b981", "#ef4444", "#9ca3af"]
                        ), legend=None),
                        tooltip=["Status", "Count"]
                    )
                    
                    pie = base.mark_arc(innerRadius=50, stroke="#fff")
                    
                    text = base.mark_text(radius=80, size=15, fontWeight="bold", fill="white").encode(
                        text="Count:Q"
                    )
                    
                    chart = (pie + text).properties(height=350)
                    st.altair_chart(chart, use_container_width=True)
                    
                    # Custom legend below chart
                    st.markdown("""
                        <div style="display:flex; justify-content:center; gap:15px; margin-top:-20px;">
                            <span style="color:#10b981; font-weight:bold;">● Correct</span>
                            <span style="color:#ef4444; font-weight:bold;">● Incorrect</span>
                            <span style="color:#9ca3af; font-weight:bold;">● Unattempted</span>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("No data available to display chart.")

            with c2:
                st.markdown("#### 📋 Detailed Question Analysis")
                df = pd.DataFrame(results)
                
                # Prettify the status column for the dataframe
                display_df = df.copy()
                display_df["Status"] = display_df["Status"].map({
                    "Correct": "✅ Correct",
                    "Incorrect": "❌ Incorrect",
                    "Unattempted": "⚪ Unattempted"
                })
                
                # Configure column styling using pandas styler if supported,
                # else Streamlit dataframe auto-handles emojis gracefully.
                st.dataframe(
                    display_df, 
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )

        except Exception as e:
            st.error("❌ An error occurred while processing your files. Please check the PDF format and try again.")
            st.exception(e)  # Useful for debugging