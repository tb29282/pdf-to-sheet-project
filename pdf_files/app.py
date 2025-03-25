import streamlit as st
import pandas as pd
import base64
import re
import os
from google.cloud import documentai
from google.api_core.client_options import ClientOptions

# Get environment variables for sensitive data
PASSWORD = os.environ.get('APP_PASSWORD', 'carteclinics')  # Default for development only
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT_ID')
PROCESSOR_ID = os.environ.get('DOCUMENT_AI_PROCESSOR_ID')
LOCATION = os.environ.get('DOCUMENT_AI_LOCATION', 'us')

# Add security headers
st.set_page_config(
    layout="wide",
    page_title="PDF to Sheet Converter",
    page_icon="📄",
    initial_sidebar_state="expanded"
)

# Google Cloud Document AI
from google.cloud import documentai
from google.api_core.client_options import ClientOptions

# -----------------------------
#  Document AI logic
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
    Processes a document with Google Document AI and extracts specified entities.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist.")

    # Configure API endpoint
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)

    # Construct the processor name
    name = client.processor_path(project_id, location, processor_id)

    # Read file content
    with open(file_path, "rb") as document_file:
        document_content = document_file.read()

    # Create the raw document request
    raw_document = documentai.RawDocument(content=document_content, mime_type=mime_type)
    request = documentai.ProcessRequest(
        name=name,
        raw_document=raw_document,
        field_mask=field_mask,
    )

    # Execute
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
            output.write("No entities found in the document.\n")

    print(f"Document AI output saved to: {output_file}")
    return output_file


def parse_output(file_path: str):
    """
    Parse the text file to extract 'dateoftest' and 'TestTypeandResult' data.
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

            # Look ahead for result
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
    Convert parsed text data to CSV.
    """
    data = parse_output(output_text_file)
    structured_data = [
        {"TestType": test_type, "Result": result}
        for test_type, result, date in data
    ]

    df = pd.DataFrame(structured_data)
    # Use the date as column header if present
    if data:
        df.columns = ["TestType", data[0][2]]
    df.to_csv(output_csv_file, index=False)


# -----------------------------
# Utility: Display PDF
# -----------------------------
def display_pdf_in_iframe(pdf_file_path: str, width: int = 450, height: int = 700):
    """
    Convert PDF to base64 and display it in an HTML iframe
    with basic toolbar/zoom (browser support may vary).
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
#  Pages: Login & Main
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
        st.rerun()  # ✅ Updated function (replaces `st.experimental_rerun()`)

    # Manual "Submit" button option
    elif st.button("Submit"):
        if password_input == PASSWORD:
            st.session_state["authenticated"] = True
            st.success("Login successful! Redirecting...")
            st.rerun()  # ✅ Updated function
        else:
            st.error("Incorrect password. Please try again.")


def main_app():
    """
    The main application where the user uploads a PDF, sees a PDF viewer, 
    and an editable CSV side-by-side.
    """
    st.title("PDF to Sheet Converter")
    
    # Add some information about the app
    st.sidebar.title("About")
    st.sidebar.info(
        "This application allows you to convert PDF documents to editable spreadsheets "
        "using Google Document AI. Upload your PDF and get structured data in return."
    )
    
    # Add usage instructions
    st.sidebar.title("Instructions")
    st.sidebar.markdown("""
    1. Upload your PDF using the uploader
    2. Click 'Process Document' to extract data
    3. Edit the resulting table as needed
    4. Download the edited CSV
    """)

    # Prepare session state for DataFrame
    if "df" not in st.session_state:
        st.session_state["df"] = None

    # Two columns side by side with a large gap
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("PDF View")
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
        if uploaded_file is not None:
            pdf_file_path = "temp_upload.pdf"
            with open(pdf_file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            display_pdf_in_iframe(pdf_file_path, width=450, height=700)
            
            # Clean up the temporary file
            if os.path.exists(pdf_file_path):
                try:
                    os.remove(pdf_file_path)
                except Exception as e:
                    st.error(f"Error cleaning up temporary file: {e}")
        else:
            st.info("Please upload a PDF to view it here.")

    with col2:
        st.subheader("Editable CSV")
        if uploaded_file is not None:
            if st.button("Process Document with Document AI"):
                if not all([PROJECT_ID, PROCESSOR_ID]):
                    st.error("Missing required environment variables for Document AI")
                    return
                    
                st.info("Running Document AI...")
                try:
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

                    # 2) Convert text -> CSV
                    output_csv_file = "results.csv"
                    convert_to_csv(output_text_file, output_csv_file)

                    # 3) Load into session state
                    df = pd.read_csv(output_csv_file)
                    st.session_state["df"] = df
                    
                    # Clean up temporary files
                    for temp_file in [output_text_file, output_csv_file]:
                        if os.path.exists(temp_file):
                            try:
                                os.remove(temp_file)
                            except Exception as e:
                                st.error(f"Error cleaning up temporary file: {e}")
                                
                except Exception as e:
                    st.error(f"Error processing document: {str(e)}")

        # If we have a DataFrame, let the user edit it
        if st.session_state["df"] is not None:
            st.write("Below is your editable DataFrame. Make changes as needed.")
            edited_df = st.data_editor(
                st.session_state["df"],
                height=600,
                use_container_width=True
            )
            # Update session with the user's edits
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
#  Main Entry
# -----------------------------
def main():
    # Use a wide layout for more horizontal space
    st.set_page_config(layout="wide")

    # Check if user is authenticated
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        login_page()
    else:
        main_app()


if __name__ == "__main__":
    main()
