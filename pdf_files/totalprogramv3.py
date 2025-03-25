from flask import Flask, render_template, request, send_file
from typing import Optional, List
from google.cloud import documentai
from google.api_core.client_options import ClientOptions
import pandas as pd
import re
import os
import tempfile

app = Flask(__name__)

# Configuration - replace these with your actual values or use environment variables
app.config['PROJECT_ID'] = os.environ.get('PROJECT_ID', '80285593679')
app.config['LOCATION'] = os.environ.get('LOCATION', 'us')
app.config['PROCESSOR_ID'] = os.environ.get('PROCESSOR_ID', 'dc982698f289d9e4')
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def process_document_sample(file_path, output_file="output.txt"):
    """Wrapper function for Document AI processing"""
    opts = ClientOptions(api_endpoint=f"{app.config['LOCATION']}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    name = client.processor_path(app.config['PROJECT_ID'], app.config['LOCATION'], app.config['PROCESSOR_ID'])

    with open(file_path, "rb") as document_file:
        document_content = document_file.read()

    raw_document = documentai.RawDocument(content=document_content, mime_type="application/pdf")
    request = documentai.ProcessRequest(
        name=name,
        raw_document=raw_document,
        field_mask="entities",
    )

    result = client.process_document(request=request)
    document = result.document

    with open(output_file, "w") as output:
        if document.text:
            output.write("Extracted Text:\n")
            output.write(document.text + "\n\n")

        if document.entities:
            output.write("Extracted Entities:\n")
            for entity in document.entities:
                if entity.type_ in ["dateoftest", "TestTypeandResult"]:
                    output.write(f"{entity.type_}: {entity.mention_text}\n")
        else:
            output.write("No entities found in the document.\n")

    return output_file

def parse_output(file_path):
    """Parse the output text file (same as original)"""
    # ... (keep the original parse_output function implementation here) ...

def convert_to_csv(output_text_file, output_csv_file):
    """Convert parsed data to CSV (same as original)"""
    # ... (keep the original convert_to_csv function implementation here) ...

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file uploaded', 400
    
    file = request.files['file']
    
    if file.filename == '':
        return 'No selected file', 400
    
    if not allowed_file(file.filename):
        return 'Invalid file type. Only PDF files are allowed.', 400

    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded file
            pdf_path = os.path.join(temp_dir, 'uploaded_file.pdf')
            file.save(pdf_path)
            
            # Process document
            text_output = os.path.join(temp_dir, 'output.txt')
            process_document_sample(pdf_path, text_output)
            
            # Convert to CSV
            csv_output = os.path.join(temp_dir, 'result.csv')
            convert_to_csv(text_output, csv_output)
            
            # Send CSV file to client
            return send_file(
                csv_output,
                mimetype='text/csv',
                as_attachment=True,
                download_name='test_results.csv'
            )
    
    except Exception as e:
        return f'Error processing file: {str(e)}', 500

if __name__ == '__main__':
    app.run(debug=True)