import streamlit as st
import fitz
import re
import pandas as pd

st.set_page_config(page_title="CUET PG Checker", layout="wide")
st.title("📘 CUET PG Answer Key Checker")

response_sheet_file = st.file_uploader("📄 Upload Response Sheet PDF", type=["pdf"])
answer_key_file = st.file_uploader("🔐 Upload Answer Key PDF", type=["pdf"])

# PDF text extraction
def extract_text(file):
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)

# Answer Key: Question ID → Correct Option ID
def parse_answer_key(text):
    return dict(re.findall(r"(\d{10})\s+(\d{10})", text))

# Response Sheet Parser
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

# Main Logic
if response_sheet_file and answer_key_file:
    with st.spinner("Processing..."):
        try:
            response_text = extract_text(response_sheet_file)
            answer_text = extract_text(answer_key_file)

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
            df = pd.DataFrame(results)
            df["Status"] = df["Status"].map({
                "Correct": "🟢 Correct",
                "Incorrect": "🔴 Incorrect",
                "Unattempted": "⚪ Unattempted"
            })

            st.success(f"🎯 Your Final Score: {score}")
            st.write(f"✅ Correct: {correct}")
            st.write(f"❌ Incorrect: {incorrect}")
            st.write(f"⚪ Unattempted: {unattempted}")

            st.markdown("### 📊 Detailed Analysis")
            st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error("❌ An error occurred while processing your files. Please check the format and try again.")
