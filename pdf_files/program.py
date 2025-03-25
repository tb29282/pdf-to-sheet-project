import streamlit as st
import pandas as pd
import base64
import re
import os

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
    Renders a simple password prompt before showing the main content.
    """
    st.title("Login Required")
    password_input = st.text_input("Enter Password:", type="password")
    if st.button("Submit"):
        if password_input == "carteclinics":
            st.session_state["authenticated"] = True
            st.experimental_rerun()  # Refresh to show main content
        else:
            st.error("Incorrect password. Please try again.")


def main_app():
    """
    The main application where the user uploads a PDF, sees a PDF viewer, 
    and an editable CSV side-by-side.
    """
    st.title("Compare PDF & Editable CSV")

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
        else:
            st.info("Please upload a PDF to view it here.")

    with col2:
        st.subheader("Editable CSV")
        # Show "Process Document" button only if a PDF is uploaded
        if uploaded_file is not None:
            if st.button("Process Document with Document AI"):
                st.info("Running Document AI...")

                # Hardcoded Document AI parameters
                project_id = "80285593679"
                location = "us"
                processor_id = "dc982698f289d9e4"

                # 1) Document AI
                output_text_file = "output.txt"
                process_document_sample(
                    project_id=project_id,
                    location=location,
                    processor_id=processor_id,
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
