from typing import Optional, List
from google.cloud import documentai
from google.api_core.client_options import ClientOptions
import os
import pandas as pd
import streamlit as st

# -----------------------------
#  Document AI Processing
# -----------------------------

def process_document_sample(
    project_id: str,
    location: str,
    processor_id: str,
    file_path: str,
    mime_type: str,
    field_mask: Optional[str] = "entities",
    processor_version_id: Optional[str] = None,
    target_entities: Optional[List[str]] = None,  # Specify a list of target entities
    output_file: str = "output.txt",  # Output file for saving results
) -> str:
    """
    Processes a document with Google Document AI and extracts specified entities.

    :return: Path to the output text file.
    """
    if not os.path.exists(file_path):
        print(f"❌ Error: The file '{file_path}' does not exist.")
        return None

    print(f"📂 Processing file: {file_path}")
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")

    try:
        # Initialize Document AI client
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
        name = client.processor_path(project_id, location, processor_id)

        # Read document content
        with open(file_path, "rb") as document_file:
            document_content = document_file.read()

        raw_document = documentai.RawDocument(content=document_content, mime_type=mime_type)
        request = documentai.ProcessRequest(name=name, raw_document=raw_document, field_mask=field_mask)

        print("⏳ Sending request to Document AI...")
        result = client.process_document(request=request)
        document = result.document

        # Save output text
        output_path = os.path.abspath(output_file)
        with open(output_path, "w") as output:
            if document.text:
                output.write("Extracted Text:\n")
                output.write(document.text + "\n\n")

            if document.entities:
                output.write("Extracted Entities:\n")
                for entity in document.entities:
                    if not target_entities or entity.type_ in target_entities:
                        output.write(f"{entity.type_}: {entity.mention_text}\n")

        print(f"✅ Document AI output saved to: {output_file}")
        return output_file

    except Exception as e:
        print(f"❌ Error in Document AI processing: {str(e)}")
        return None


# -----------------------------
#  CSV Processing & Editing
# -----------------------------

def parse_output(file_path: str):
    """
    Parse the text file output by Document AI to extract 'dateoftest' and 'TestTypeandResult' lines.
    """
    if not os.path.exists(file_path):
        print("❌ Error: Output file does not exist.")
        return []

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

            embedded_result = re.search(r"(\d+(?:\.\d+)?\s*(?:High|Low))", test_type)
            if embedded_result:
                result = embedded_result.group(0)
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
    """
    Convert extracted data to CSV format and allow editing.
    """
    data = parse_output(output_text_file)
    df = pd.DataFrame(data, columns=["TestType", "Result", "Date"])

    df.to_csv(output_csv_file, index=False)
    return df


# -----------------------------
#  Streamlit UI - Editable CSV
# -----------------------------

def editable_csv_ui():
    st.title("Compare PDF & Editable CSV")

    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
    
    if uploaded_file:
        pdf_file_path = "uploaded_file.pdf"
        with open(pdf_file_path, "wb") as f:
            f.write(uploaded_file.getvalue())

        if st.button("Process Document"):
            st.info("Processing document using Document AI...")

            output_text_file = "output.txt"
            processed_file = process_document_sample(
                project_id="80285593679",
                location="us",
                processor_id="dc982698f289d9e4",
                file_path=pdf_file_path,
                mime_type="application/pdf",
                output_file=output_text_file
            )

            if processed_file:
                st.success("Processing completed! Data extracted.")
                
                # Convert extracted data to CSV
                output_csv_file = "results.csv"
                df = convert_to_csv(processed_file, output_csv_file)

                # Store DataFrame in session state
                st.session_state["df"] = df

    if "df" in st.session_state:
        st.subheader("Editable Data")
        
        # Allow adding new rows
        if st.button("Add Row"):
            new_row = pd.DataFrame([["", "", ""]], columns=["TestType", "Result", "Date"])
            st.session_state["df"] = pd.concat([st.session_state["df"], new_row], ignore_index=True)

        # Show editable table
        edited_df = st.data_editor(st.session_state["df"], height=600, use_container_width=True)
        
        # Store updates in session state
        st.session_state["df"] = edited_df

        # Provide download button for updated CSV
        csv_data = edited_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Edited CSV",
            data=csv_data,
            file_name="edited_results.csv",
            mime="text/csv"
        )


# -----------------------------
#  Run App
# -----------------------------

def main():
    st.set_page_config(layout="wide")
    
    if "df" not in st.session_state:
        st.session_state["df"] = None

    editable_csv_ui()

if __name__ == "__main__":
    main()
