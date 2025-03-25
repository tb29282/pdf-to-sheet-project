from typing import Optional
from google.cloud import documentai
from google.api_core.client_options import ClientOptions

def process_document_sample(
    project_id: str,
    location: str,
    processor_id: str,
    file_path: str,
    mime_type: str,
    field_mask: Optional[str] = "entities",
    processor_version_id: Optional[str] = None,
    target_entities: Optional[list] = None,  # Add this parameter
) -> None:
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")

    client = documentai.DocumentProcessorServiceClient(client_options=opts)

    # Set up the full processor path
    name = client.processor_path(project_id, location, processor_id)

    with open(file_path, "rb") as image:
        image_content = image.read()

    raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)
    request = documentai.ProcessRequest(
        name=name,
        raw_document=raw_document,
        field_mask=field_mask,
    )

    result = client.process_document(request=request)
    document = result.document

    # Check for entities and filter them based on target_entities
    if document.entities:
        print("Extracted entities:")
        for entity in document.entities:
            # Filter for specific entities (e.g., "name", "date")
            if target_entities and entity.type_ in target_entities:
                print(f"{entity.type_}: {entity.mention_text}")
    else:
        print("No entities found in the document.")

# Call the function with a list of target entities
process_document_sample(
   process_document_sample( project_id="dataformatter-437611", 
                           location="us", 
                           processor_id="3fde13115fa0076f", 
                           file_path=r"C:\Users\joyjp\Downloads\M107_2024.06.10 - Preliminary Bloodwork Report, Labcorp", 
                           mime_type="application/pdf", 
                           target_entities=["doctors-orders", "patient-history", "prescribed tests", "test_results"] )
)
