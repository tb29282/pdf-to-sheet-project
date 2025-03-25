import streamlit as st
import pandas as pd
import base64
import re
import os

# Google Cloud Document AI
from google.cloud import documentai
from google.api_core.client_options import ClientOptions

# -----------------------------
#  Configuration
# -----------------------------
# Hardcode your API key for Document AI here.
API_KEY = "AIzaSyAEo-YfIaB8cJjUTwLeQKFs-Weua1FiNyM"
PASSWORD = "carteclinics"
# Hardcode your Document AI processor details
PROJECT_ID = "80285593679"
LOCATION = "us"
PROCESSOR_ID = "dc982698f289d9e4"

# -----------------------------
#  Document AI Logic
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
):
    """
    Attempts to process a document with Document AI using the specified API key.
    WARNING: Using an API key for Document AI might not work if your project
    doesn't permit key-based access. If you get 'PERMISSION_DENIED' or
    'UNAUTHENTICATED', use service account or OAuth instead.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist.")

    # Configure the API endpoint and pass the API key
    client_options = ClientOptions(
        api_endpoint=f"{location}-documentai.googleapis.com",
        api_key=API_KEY
    )
    client = documentai.DocumentProcessorServiceClient(client_options=client_options)

    # Construct the resource name of the processor
    name = client.processor_path(project_id, location, processor_id)

    # Read file content
    with open(file_path, "rb") as f:
        doc_content = f.read()

    raw_document = documentai.RawDocument(
        content=doc_content,
        mime_type=mime_type
    )

    request = documentai.ProcessRequest(
        name=name,
        raw_document=raw_document,
        field_mask=field_mask,
    )

    # Attempt to process the document
    result = client.process_document(request=request)
    document = result.document

    # Write output to text file
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

    print(f"Document AI output saved to: {output_file}")
    return output_file

def parse_output(file_path: str):
    """
    Parse the text file output by process_document_sample to extract 'dateoftest'
    and 'TestTypeandResult' lines.
    """
    with open(file_path, "r") as f:
        lines = f.readlines()

    data = []
    current_date = None

    # Find date from reversed lines
    for line in reversed(lines):
        if line.startswith("dateoftest:"):
            current_date = line.split(":", 1)[1].strip()
            break

    # Collect test info
    for i, line in enumerate(lines):
        if line.startswith("TestTypeandResult:"):
            test_type = line.split(":", 1)[1].strip()
            result = ""

            # Check if there's an embedded numeric + High/Low
            embedded_result = re.search(r"(\d+(?:\.\d+)?\s*(?:High|Low))", test_type)
            if embedded_result:
                result = embedded_result.group(0)
                test_type = test_type.replace(result, "").strip()

            # Look ahead for additional result lines
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
    """
    Convert the parsed data to CSV format.
    """
    data = parse_output(output_text_file)
    structured_data = [
        {"TestType": test_type, "Result": result}
        for test_type, result, date in data
    ]
    df = pd.DataFrame(structured_data)

    # If date is found, use it as the second column's header
    if data:
        df.columns = ["TestType", data[0][2]]

    df.to_csv(output_csv_file, index=False)

# -----------------------------
#  Utility: Display PDF
# -----------------------------
def display_pdf_in_iframe(pdf_file_path: str, width: int = 450, height: int = 700):
    """
    Convert PDF to base64 and display it in an HTML iframe
    with a minimal toolbar/zoom (browser support may vary).
    """
    with open(pdf_file_path, "rb") as pdf_file:
        base64_pdf = base64.b64encode(pdf_file.read()).decode("utf-8")

    pdf_display = f"""
    <iframe 
        src="data:application/pdf;base64,{base64_pdf}#toolbar=1&navpanes=1&scrollbar=1&view=FitH&zoom=100"
        width="{width}" 
        height="{height}" 
        type="application/pdf"
    ></iframe>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)

# -----------------------------
#  Password Login
# -----------------------------
  

def login_page():
    """
    A simple password-based login page for authentication.
    Users must enter the correct password to access the app.
    """
    st.title("Login Required")

    # Check if the user is already authenticated
    if "authenticated" in st.session_state and st.session_state["authenticated"]:
        st.success("You are logged in!")
        return  # Skip login if already authenticated

    # Capture password input (supports Enter key submission)
    password_input = st.text_input("Enter Password:", type="password", key="password")

    # If the user presses "Enter", Streamlit automatically reruns the script
    if password_input == PASSWORD:
        st.session_state["authenticated"] = True
        st.success("Login successful! Redirecting...")
        st.rerun()  # ✅ Force page reload to unlock access

    # Manual "Submit" button option
    elif st.button("Submit"):
        if password_input == PASSWORD:
            st.session_state["authenticated"] = True
            st.success("Login successful! Redirecting...")
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")

# -----------------------------
#  Main App Page
# -----------------------------
def main_app():
    st.title("Compare PDF & Editable CSV")

    # Ensure there's a place in session_state for the DataFrame
    if "df" not in st.session_state:
        st.session_state["df"] = None

    # Wide columns with a large gap to avoid overlap
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("PDF View")
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
        if uploaded_file is not None:
            pdf_file_path = "temp_upload.pdf"
            with open(pdf_file_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            display_pdf_in_iframe(pdf_file_path, width=450, height=700)
        else:
            st.info("Please upload a PDF to view it here.")

    with col2:
        st.subheader("Editable CSV")
        if uploaded_file is not None:
            if st.button("Process Document with Document AI"):
                st.info("Running Document AI using API Key...")

                # 1) Document AI
                output_text_file = "output.txt"
                process_document_sample(
                    project_id=PROJECT_ID,
                    location=LOCATION,
                    processor_id=PROCESSOR_ID,
                    file_path=pdf_file_path,
                    mime_type="application/pdf",
                    output_file=output_text_file,
                    target_entities=["dateoftest", "TestTypeandResult"]
                )

                # 2) Convert to CSV
                output_csv_file = "results.csv"
                convert_to_csv(output_text_file, output_csv_file)

                # 3) Load into session_state
                df = pd.read_csv(output_csv_file)
                st.session_state["df"] = df

        # Display/edit DataFrame if available
        if st.session_state["df"] is not None:
            st.write("Below is your editable DataFrame. Make changes as needed.")
            edited_df = st.data_editor(
                st.session_state["df"],
                height=600,
                use_container_width=True
            )
            # Update session with user edits
            st.session_state["df"] = edited_df

            # Provide a download button for the edited CSV
            csv_data = edited_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Edited CSV",
                data=csv_data,
                file_name="edited_results.csv",
                mime="text/csv"
            )

# -----------------------------
#  Entry Point
# -----------------------------
def main():
    # Use a wide layout to reduce overlap
    st.set_page_config(layout="wide")

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    # If not authenticated, show login page
    if not st.session_state["authenticated"]:
        login_page()
    else:
        # Once logged in, show main app
        main_app()

if __name__ == "__main__":
    main()
