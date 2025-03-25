from typing import Optional, List
from google.cloud import documentai
from google.api_core.client_options import ClientOptions
import pandas as pd
import re
import os

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

    :param project_id: Google Cloud project ID.
    :param location: Location of the Document AI processor (e.g., "us").
    :param processor_id: ID of the processor to use.
    :param file_path: Path to the document file to process.
    :param mime_type: MIME type of the document (e.g., "application/pdf").
    :param field_mask: Field mask for specific fields to extract.
    :param processor_version_id: Specific processor version to use (optional).
    :param target_entities: List of entities to extract (optional).
    :param output_file: Path to the output text file for saving results.
    :return: Path to the output text file.
    """
    # Verify if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist.")

    # Configure API endpoint based on location
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")

    # Initialize Document AI client
    client = documentai.DocumentProcessorServiceClient(client_options=opts)

    # Construct the processor path
    name = client.processor_path(project_id, location, processor_id)

    # Read the document content
    with open(file_path, "rb") as document_file:
        document_content = document_file.read()

    # Prepare raw document for processing
    raw_document = documentai.RawDocument(content=document_content, mime_type=mime_type)

    # Create the processing request
    request = documentai.ProcessRequest(
        name=name,
        raw_document=raw_document,
        field_mask=field_mask,
    )

    # Execute the request and get the response
    result = client.process_document(request=request)
    document = result.document

    # Open the output file for writing
    with open(output_file, "w") as output:
        # Write the document text if available
        if document.text:
            output.write("Extracted Text:\n")
            output.write(document.text + "\n\n")

        # Check for and filter entities
        if document.entities:
            output.write("Extracted Entities:\n")
            for entity in document.entities:
                # Filter entities if target_entities is provided
                if not target_entities or entity.type_ in target_entities:
                    output.write(f"{entity.type_}: {entity.mention_text}\n")
        else:
            output.write("No entities found in the document.\n")

    print(f"Document AI output saved to: {output_file}")
    return output_file

def parse_output(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    data = []
    current_date = None

    # Extract the date from the last lines
    for line in reversed(lines):
        if line.startswith("dateoftest:"):
            current_date = line.split(":")[1].strip()
            break

    for i, line in enumerate(lines):
        if line.startswith("TestTypeandResult:"):
            test_type = line.split(":", 1)[1].strip()  # Extract test type
            result = ""

            # Check if the test type itself contains the result
            embedded_result = re.search(r"(\d+(?:\.\d+)?\s*(?:High|Low))", test_type)
            if embedded_result:
                result = embedded_result.group(0)
                test_type = test_type.replace(result, "").strip()

            # Collect the subsequent lines until the next "TestTypeandResult:" or "dateoftest:"
            for j in range(i + 1, len(lines)):
                next_line = lines[j].strip()
                if next_line.startswith("TestTypeandResult:") or next_line.startswith("dateoftest:"):
                    break

                # Handle results on the next lines
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

def convert_to_csv(output_text_file, output_csv_file):
    data = parse_output(output_text_file)
    structured_data = [{"TestType": test_type, "Result": result} for test_type, result, date in data]

    # Convert to DataFrame
    df = pd.DataFrame(structured_data)

    # Set the header for the results column as the date
    if data:
        df.columns = ['TestType', data[0][2]]

    # Save the DataFrame to a CSV file
    df.to_csv(output_csv_file, index=False)
    print(f"CSV file saved to: {output_csv_file}")

# Main function to run the combined workflow
def main():
    # Parameters for Document AI
    project_id = "80285593679"
    location = "us"
    processor_id = "dc982698f289d9e4"
    input_pdf = r"C:\Users\joyjp\Downloads\M122_2024.07.18 - CBC, Inova"
    mime_type = "application/pdf"
    output_text_file = "output.txt"
    output_csv_file = "output_converted10.csv"

    # Step 1: Process the document and extract data
    processed_file = process_document_sample(
        project_id=project_id,
        location=location,
        processor_id=processor_id,
        file_path=input_pdf,
        mime_type=mime_type,
        output_file=output_text_file,
        target_entities=["dateoftest", "TestTypeandResult"],
    )

    # Step 2: Convert the extracted data to CSV
    convert_to_csv(processed_file, output_csv_file)

# Run the combined workflow
if __name__ == "__main__":
    main()
