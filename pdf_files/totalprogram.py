from flask import Flask, request, render_template, send_file
import os
import pandas as pd
import re
from google.cloud import documentai
from google.api_core.client_options import ClientOptions
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Set upload folder and allowed extensions
UPLOAD_FOLDER = "uploads"
PROCESSED_FOLDER = "processed"
ALLOWED_EXTENSIONS = {"pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["PROCESSED_FOLDER"] = PROCESSED_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Document AI processing function
def process_document_sample(file_path):
    project_id = "80285593679"
    location = "us"
    processor_id = "dc982698f289d9e4"
    mime_type = "application/pdf"
    output_file = os.path.join(app.config["PROCESSED_FOLDER"], "output.txt")

    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    name = client.processor_path(project_id, location, processor_id)

    with open(file_path, "rb") as document_file:
        document_content = document_file.read()

    raw_document = documentai.RawDocument(content=document_content, mime_type=mime_type)

    request = documentai.ProcessRequest(name=name, raw_document=raw_document, field_mask="entities")
    result = client.process_document(request=request)
    document = result.document

    with open(output_file, "w") as output:
        if document.text:
            output.write("Extracted Text:\n")
            output.write(document.text + "\n\n")

        if document.entities:
            output.write("Extracted Entities:\n")
            for entity in document.entities:
                output.write(f"{entity.type_}: {entity.mention_text}\n")
        else:
            output.write("No entities found in the document.\n")

    return output_file


def parse_output(file_path):
    with open(file_path, "r") as file:
        lines = file.readlines()

    data = []
    current_date = None

    for line in reversed(lines):
        if line.startswith("dateoftest:"):
            current_date = line.split(":")[1].strip()
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


def convert_to_csv(output_text_file, output_csv_file):
    data = parse_output(output_text_file)
    structured_data = [{"TestType": test_type, "Result": result} for test_type, result, date in data]

    df = pd.DataFrame(structured_data)

    if data:
        df.columns = ["TestType", data[0][2]]

    df.to_csv(output_csv_file, index=False)


@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return "No file part"

        file = request.files["file"]

        if file.filename == "":
            return "No selected file"

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)

            # Process document
            output_text_file = process_document_sample(file_path)

            # Convert to CSV
            output_csv_file = os.path.join(app.config["PROCESSED_FOLDER"], "output.csv")
            convert_to_csv(output_text_file, output_csv_file)

            return send_file(output_csv_file, as_attachment=True)

    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>File Upload</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; margin: 50px; }
            .upload-container { border: 2px dashed #ccc; padding: 20px; width: 300px; margin: 0 auto; }
            .upload-container:hover { border-color: #666; }
            input[type="file"] { display: block; margin: 10px auto; }
            button { background-color: #28a745; color: white; border: none; padding: 10px 20px; cursor: pointer; }
            button:hover { background-color: #218838; }
        </style>
    </head>
    <body>
        <h1>Upload Your File</h1>
        <div class="upload-container">
            <form action="/" method="POST" enctype="multipart/form-data">
                <input type="file" name="file" required>
                <button type="submit">Upload</button>
            </form>
        </div>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(debug=True)
