import streamlit as st
import pandas as pd
import base64
import os
import re
from typing import Optional, List
from google.cloud import documentai
from google.api_core.client_options import ClientOptions

# ✅ MUST be the first Streamlit command
st.set_page_config(
    layout="wide",
    page_title="PDF to Sheet Converter",
    page_icon="📄",
    initial_sidebar_state="expanded"
)

# -----------------------------
# Config and Constants
# -----------------------------
PASSWORD = "carteclinics"
PROJECT_ID = "80285593679"
LOCATION = "us"
PROCESSOR_ID = "dc982698f289d9e4"

# -----------------------------
# Google Cloud Credentials Setup
# -----------------------------
def setup_google_credentials():
    try:
        credentials_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if credentials_json:
            try:
                credentials_json = base64.b64decode(credentials_json).decode('utf-8')
            except:
                pass
            credentials_path = "google_credentials.json"
            with open(credentials_path, "w") as f:
                f.write(credentials_json)
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
            return True
        else:
            st.warning("Google Cloud credentials not found.")
            return False
    except Exception as e:
        st.error(f"Error setting up credentials: {str(e)}")
        return False

# -----------------------------
# Document AI Logic
# -----------------------------
def process_document_sample(
    project_id: str,
    location: str,
    processor_id: str,
    file_path: str,
    mime_type: str = "application/pdf",
    field_mask: str = "entities",
    target_entities=None,
    output_file: str = "output.txt",
) -> Optional[str]:
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The file '{file_path}' does not exist.")

        opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
        name = client.processor_path(project_id, location, processor_id)

        with open(file_path, "rb") as f:
            content = f.read()

        raw_document = documentai.RawDocument(content=content, mime_type=mime_type)
        request = documentai.ProcessRequest(name=name, raw_document=raw_document, field_mask=field_mask)
        result = client.process_document(request=request)
        document = result.document

        with open(output_file, "w") as output:
            if document.text:
                output.write("Extracted Text:\n")
                output.write(document.text + "\n\n")
            if document.entities:
                output.write("Extracted Entities:\n")
                for entity in document.entities:
                    if not target_entities or entity.type_ in target_entities:
                        output.write(f"{entity.type_}: {entity.mention_text}\n")
            else:
                output.write("No entities found.\n")
        return output_file
    except Exception as e:
        st.error(f"Document AI error: {str(e)}")
        return None

# -----------------------------
# Text to CSV Parsing
# -----------------------------
def parse_output(file_path: str):
    with open(file_path, "r") as f:
        lines = f.readlines()

    data = []
    current_date = None

    for line in reversed(lines):
        if line.startswith("dateoftest:"):
            current_date = line.split(":", 1)[1].strip()
            break

    for i, line in enumerate(lines):
        if line.startswith("TestTypeandResult:"):
            test_type = line.split(":", 1)[1].strip()
            result = ""

            embedded = re.search(r"(\d+(?:\.\d+)?\s*(?:High|Low))", test_type)
            if embedded:
                result = embedded.group(0)
                test_type = test_type.replace(result, "").strip()

            for j in range(i + 1, len(lines)):
                next_line = lines[j].strip()
                if next_line.startswith("TestTypeandResult:") or next_line.startswith("dateoftest:"):
                    break
                if re.match(r"High|Low", next_line):
                    if re.search(r"\d+", next_line):
                        result = next_line
                    elif j + 1 < len(lines) and re.match(r"^[<>]?\d+(\.\d+)?", lines[j + 1].strip()):
                        result = f"{next_line} {lines[j + 1].strip()}"
                    break
                elif re.match(r"^[<>]?\d+(\.\d+)?|Normal", next_line):
                    result = next_line
                    break

            data.append((test_type, result, current_date))
    return data

def convert_to_csv(output_text_file: str, output_csv_file: str):
    data = parse_output(output_text_file)
    df = pd.DataFrame([{"TestType": t, "Result": r} for t, r, d in data])
    if data:
        df.columns = ["TestType", data[0][2]]
    df.to_csv(output_csv_file, index=False)
    return df

# -----------------------------
# PDF Viewer Utility
# -----------------------------
def display_pdf_in_iframe(pdf_file_path: str, width: int = 450, height: int = 700):
    with open(pdf_file_path, "rb") as pdf_file:
        base64_pdf = base64.b64encode(pdf_file.read()).decode("utf-8")
    st.markdown(f"""
    <iframe 
        src="data:application/pdf;base64,{base64_pdf}#toolbar=1&navpanes=1&scrollbar=1&view=FitH&zoom=100"
        width="{width}" height="{height}" type="application/pdf"></iframe>
    """, unsafe_allow_html=True)

# -----------------------------
# Login Page
# -----------------------------
def login_page():
    st.title("Login Required")
    if "authenticated" in st.session_state and st.session_state["authenticated"]:
        return

    password_input = st.text_input("Enter Password:", type="password")
    if password_input == PASSWORD:
        st.session_state["authenticated"] = True
        st.success("Login successful! Redirecting...")
        st.rerun()
    elif st.button("Submit"):
        if password_input == PASSWORD:
            st.session_state["authenticated"] = True
            st.success("Login successful! Redirecting...")
            st.rerun()
        else:
            st.error("Incorrect password.")

# -----------------------------
# Main Application
# -----------------------------
def main_app():
    st.title("PDF to Sheet Converter")
    st.sidebar.title("Instructions")
    st.sidebar.markdown("""
    1. Upload a PDF file.
    2. Click 'Process Document'.
    3. Edit the results below.
    4. Download your updated CSV.
    """)

    if not setup_google_credentials():
        return

    if "df" not in st.session_state:
        st.session_state["df"] = None

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("PDF Viewer")
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
        pdf_file_path = None

        if uploaded_file:
            pdf_file_path = "uploaded.pdf"
            with open(pdf_file_path, "wb") as f:
                f.write(uploaded_file.read())
            display_pdf_in_iframe(pdf_file_path)

    with col2:
        st.subheader("Extracted & Editable Data")
        if uploaded_file and st.button("Process Document"):
            output_txt = "output.txt"
            output_csv = "output.csv"

            result_file = process_document_sample(
                project_id=PROJECT_ID,
                location=LOCATION,
                processor_id=PROCESSOR_ID,
                file_path=pdf_file_path,
                mime_type="application/pdf",
                output_file=output_txt,
                target_entities=["dateoftest", "TestTypeandResult"]
            )

            if result_file:
                df = convert_to_csv(output_txt, output_csv)
                st.session_state["df"] = df

        if st.session_state["df"] is not None:
            if st.button("Add Row"):
                new_row = pd.DataFrame([["", ""]], columns=st.session_state["df"].columns)
                st.session_state["df"] = pd.concat([st.session_state["df"], new_row], ignore_index=True)

            edited_df = st.data_editor(
                st.session_state["df"],
                num_rows="dynamic",
                height=500,
                use_container_width=True
            )
            st.session_state["df"] = edited_df

            csv_data = edited_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Edited CSV", csv_data, "edited_results.csv", "text/csv")

# -----------------------------
# Entry Point
# -----------------------------
def main():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
