import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import documentai_v1 as documentai
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# Authenticate and initialize Google APIs
def authenticate_service_account(service_account_file, scopes):
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=scopes)
    return credentials

# 1. Get files from Google Drive
def list_drive_files(drive_service, folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/pdf'"
    results = drive_service.files().list(q=query).execute()
    return results.get('files', [])

# 2. Download files from Google Drive
def download_file(drive_service, file_id, file_name):
    request = drive_service.files().get_media(fileId=file_id)
    with open(file_name, 'wb') as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

# 3. Process document using Document AI
def process_document_ai(project_id, file_path, location='us'):
    client = documentai.DocumentProcessorServiceClient()
    with open(file_path, 'rb') as image:
        image_content = image.read()
    
    # Configure the request
    document = {"content": image_content, "mime_type": "application/pdf"}
    name = f'projects/{project_id}/locations/{location}/processors/YOUR_PROCESSOR_ID'
    
    request = {"name": name, "raw_document": document}
    result = client.process_document(request=request)
    
    return result.document

# 4. Extract data from processed document
def extract_fields(document):
    fields = {}
    for entity in document.entities:
        fields[entity.type_] = entity.mention_text
    return fields

# 5. Save formatted data to Google Drive
def save_to_drive(drive_service, folder_id, content, file_name):
    media = MediaFileUpload(file_name, mimetype='text/plain')
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    drive_service.files().create(body=file_metadata, media_body=media).execute()

# Main Workflow
def main():
    service_account_file = 'path/to/your-service-account-key.json'
    project_id = 'your-project-id'
    folder_id = 'your-drive-folder-id'
    output_folder_id = 'your-output-drive-folder-id'
    
    scopes = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/cloud-platform']
    
    # Authenticate and build services
    credentials = authenticate_service_account(service_account_file, scopes)
    drive_service = build('drive', 'v3', credentials=credentials)
    
    # 1. Get PDF files from Google Drive folder
    files = list_drive_files(drive_service, folder_id)
    
    for file in files:
        file_id = file['id']
        file_name = file['name']
        
        # 2. Download the file
        local_file = f'tmp_{file_name}'
        download_file(drive_service, file_id, local_file)
        
        # 3. Process the file with Document AI
        processed_doc = process_document_ai(project_id, local_file)
        
        # 4. Extract the fields and format them
        extracted_data = extract_fields(processed_doc)
        formatted_output = "\n".join(f"{key}: {value}" for key, value in extracted_data.items())
        
        # 5. Save the formatted output to a new file in Google Drive
        output_file_name = f'processed_{file_name}.txt'
        with open(output_file_name, 'w') as output_file:
            output_file.write(formatted_output)
        
        save_to_drive(drive_service, output_folder_id, formatted_output, output_file_name)

if __name__ == '__main__':
    main()
