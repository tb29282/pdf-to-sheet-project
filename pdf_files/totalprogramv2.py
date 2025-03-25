from flask import Flask, request, send_file, jsonify
import os
import re
import pandas as pd
import zipfile
from werkzeug.utils import secure_filename
from google.cloud import documentai
from google.api_core.client_options import ClientOptions

app = Flask(__name__)

# Configure directories
UPLOAD_FOLDER = "uploads"
PROCESSED_FOLDER = "processed"
COMBINED_CSV = os.path.join(PROCESSED_FOLDER, "final_combined.csv")
ALLOWED_EXTENSIONS = {"pdf", "zip"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["PROCESSED_FOLDER"] = PROCESSED_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Track processing progress in a global variable
processing_complete = False


def allowed_file(filename):
    """Check if the file has an allowed extension (PDF or ZIP)."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def process_document_sample(file_path):
    """
    Processes a single PDF file with Document AI and extracts text.
    Using gcloud auth application-default login for credentials.
    """
    global processing_complete
    processing_complete = False  # Reset processing flag at the start

    # Replace these with your own GCP info
    project_id = "dataformatter-437611"
    location = "us"
    processor_id = "3fde13115fa0076f"
    mime_type = "application/pdf"

    output_txt = os.path.join(PROCESSED_FOLDER, f"{os.path.basename(file_path)}.txt")

    try:
        # Use Application Default Credentials (requires `gcloud auth application-default login`)
        opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
        name = client.processor_path(project_id, location, processor_id)

        with open(file_path, "rb") as f:
            document_content = f.read()

        raw_document = documentai.RawDocument(content=document_content, mime_type=mime_type)
        request = documentai.ProcessRequest(name=name, raw_document=raw_document, field_mask="entities")

        result = client.process_document(request=request)
        document = result.document

        with open(output_txt, "w", encoding="utf-8") as output:
            if document.text:
                output.write("Extracted Text:\n")
                output.write(document.text + "\n\n")

            if document.entities:
                output.write("Extracted Entities:\n")
                for entity in document.entities:
                    output.write(f"{entity.type_}: {entity.mention_text}\n")
            else:
                output.write("No entities found in the document.\n")

        processing_complete = True
        return output_txt
    except Exception as e:
        print(f"Error processing document: {e}")
        processing_complete = False
        return None


def parse_output(file_path):
    """Parses extracted text from Document AI output to structure the data."""
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    data = []
    current_date = None

    # Attempt to find a date in reverse
    for line in reversed(lines):
        if line.startswith("dateoftest:"):
            current_date = line.split(":", 1)[1].strip()
            break

    # Find test types & results
    for i, line in enumerate(lines):
        if line.startswith("TestTypeandResult:"):
            test_type = line.split(":", 1)[1].strip()
            result = ""

            # Check subsequent lines for a result
            for j in range(i + 1, len(lines)):
                next_line = lines[j].strip()
                if next_line.startswith("TestTypeandResult:") or next_line.startswith("dateoftest:"):
                    break

                if re.match(r"High|Low", next_line):
                    if re.search(r"\d+", next_line):
                        result = next_line
                    break
                elif re.match(r"^[<>]?\d+(\.\d+)?|Normal", next_line):
                    result = next_line
                    break

            data.append((test_type, result, current_date))

    return data


def convert_to_csv(output_text_file, output_csv_file):
    """Converts structured parsed output into a CSV."""
    data = parse_output(output_text_file)

    # If no data, skip CSV creation
    if not data:
        print(f"Warning: No data found in {output_text_file}.")
        return None

    structured_data = [{"TestType": test_type, "Result": result} for (test_type, result, date) in data]
    df = pd.DataFrame(structured_data)

    # Attempt to name columns based on discovered date
    if data and len(data[0]) > 2 and data[0][2] is not None:
        df.columns = ["TestType", data[0][2]]

    df.to_csv(output_csv_file, index=False)
    return output_csv_file


def merge_csv_files(csv_files, output_file):
    """Merges multiple CSV files into a single CSV with blank rows in between."""
    valid_csvs = [csv for csv in csv_files if csv is not None]
    if not valid_csvs:
        print("No valid CSVs found to merge.")
        return None

    # Read each CSV and add blank rows in between
    combined_df = pd.DataFrame()
    for csv_file in valid_csvs:
        df = pd.read_csv(csv_file)
        # Add a blank row first for separation
        if not combined_df.empty:
            blank_row = pd.DataFrame([["", ""]])
            combined_df = pd.concat([combined_df, blank_row], ignore_index=True)

        combined_df = pd.concat([combined_df, df], ignore_index=True)

    combined_df.to_csv(output_file, index=False)
    return output_file


@app.route("/", methods=["GET"])
def index():
    """
    Serve the main HTML page for Drag & Drop + Browse upload.
    """
    # Return the HTML code
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Upload</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            margin: 50px;
        }
        .upload-container {
            border: 2px dashed #ccc;
            padding: 20px;
            width: 400px;
            margin: 0 auto;
            position: relative;
            cursor: pointer;
            transition: border-color 0.3s;
        }
        .upload-container.dragover {
            border-color: #218838;
            background-color: #f8f9fa;
        }
        input[type="file"] {
            display: none;
        }
        .file-list {
            border: 1px solid #ddd;
            margin-top: 10px;
            padding: 10px;
            width: 400px;
            max-height: 200px;
            overflow-y: auto;
            text-align: left;
            margin-left: auto;
            margin-right: auto;
        }
        .file-list p {
            margin: 5px 0;
            font-size: 14px;
        }
        .progress-container {
            display: none;
            width: 100%;
            margin-top: 10px;
        }
        .progress-bar {
            width: 0%;
            height: 10px;
            background-color: #28a745;
            transition: width 0.3s;
        }
        #upload-btn, #browse-btn {
            background-color: #28a745;
            color: white;
            border: none;
            padding: 10px 20px;
            cursor: pointer;
            margin-top: 10px;
            display: inline-block;
        }
        #upload-btn:hover, #browse-btn:hover {
            background-color: #218838;
        }
        #download-btn {
            display: none;
            margin-top: 20px;
            padding: 10px 20px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
        }
        #download-btn:hover {
            background-color: #0056b3;
        }
    </style>
</head>
<body>
    <h1>Upload Your Files</h1>

    <div class="upload-container" id="drop-zone">
        <p class="file-label">Drag & Drop your files here or <span id="browse-btn" style="text-decoration: underline; cursor: pointer;">Browse</span></p>
        <input type="file" id="file-input" name="file" multiple>
    </div>

    <!-- Box to show the list of uploaded files -->
    <div class="file-list" id="file-list">
        <p>No files uploaded.</p>
    </div>

    <!-- Upload Button -->
    <button id="upload-btn">Upload</button>

    <!-- Progress Bar -->
    <div class="progress-container">
        <div class="progress-bar" id="progress-bar"></div>
    </div>

    <!-- Download Button -->
    <a id="download-btn" href="#" download="final_combined.csv">Download Processed CSV</a>

    <script>
    const dropZone = document.getElementById("drop-zone");
    const browseBtn = document.getElementById("browse-btn");
    const fileInput = document.getElementById("file-input");
    const uploadBtn = document.getElementById("upload-btn");
    const fileList = document.getElementById("file-list");
    const progressContainer = document.querySelector(".progress-container");
    const progressBar = document.getElementById("progress-bar");
    const downloadBtn = document.getElementById("download-btn");

    let uploadedFiles = [];

    // Clicking "Browse" triggers file dialog
    browseBtn.addEventListener("click", () => fileInput.click());

    // When files are chosen
    fileInput.addEventListener("change", (e) => {
        let files = e.target.files;
        if (files.length > 0) {
            for (let i = 0; i < files.length; i++) {
                uploadedFiles.push(files[i]);
            }
            updateFileList();
        }
    });

    // Drag & drop events
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");

        let files = e.dataTransfer.files;
        if (files.length > 0) {
            for (let i = 0; i < files.length; i++) {
                uploadedFiles.push(files[i]);
            }
            updateFileList();
        }
    });

    function updateFileList() {
        fileList.innerHTML = "";
        if (uploadedFiles.length === 0) {
            fileList.innerHTML = "<p>No files uploaded.</p>";
        } else {
            uploadedFiles.forEach(file => {
                let fileItem = document.createElement("p");
                fileItem.textContent = `✔ ${file.name}`;
                fileList.appendChild(fileItem);
            });
        }
    }

    // Click "Upload"
    uploadBtn.addEventListener("click", () => {
        if (uploadedFiles.length === 0) {
            alert("Please add files to upload.");
            return;
        }

        const formData = new FormData();
        uploadedFiles.forEach(file => {
            formData.append("file", file);
        });

        progressContainer.style.display = "block";
        progressBar.style.width = "0%";

        // Track upload progress via XMLHttpRequest
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/upload", true);

        xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
                let percentComplete = (event.loaded / event.total) * 50; // Up to 50% for upload
                progressBar.style.width = percentComplete + "%";
            }
        };

        xhr.onload = function () {
            if (xhr.status === 200) {
                startProcessingProgress(); // Switch to processing progress
            } else {
                alert("Upload failed. Try again.");
            }
        };

        xhr.send(formData);
    });

    // Poll /progress to see if the backend is done
    function startProcessingProgress() {
        let progress = 50;
        progressBar.style.width = "50%";

        let processingInterval = setInterval(() => {
            progress += 5;
            if (progress >= 100) progress = 95; // Stop at 95% until CSV is ready
            progressBar.style.width = progress + "%";
        }, 1000);

        fetch("/progress")
        .then(response => response.json())
        .then(data => {
            if (data.complete) {
                clearInterval(processingInterval);
                progressBar.style.width = "100%";
                progressContainer.style.display = "none";

                // Show download button
                downloadBtn.href = "/download";
                downloadBtn.style.display = "block";
            } else {
                setTimeout(startProcessingProgress, 2000);
            }
        });
    }
    </script>

</body>
</html>
    """


@app.route("/upload", methods=["POST"])
def upload_file():
    """
    POST route that actually handles the file(s) upload and processing.
    """
    global processing_complete
    processing_complete = False

    files = request.files.getlist("file")
    if not files or all(f.filename == "" for f in files):
        return "No files selected", 400

    csv_files = []
    # Create the folders if not present
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["PROCESSED_FOLDER"], exist_ok=True)

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)

            # If it's a ZIP, extract PDFs
            if filename.endswith(".zip"):
                with zipfile.ZipFile(file_path, "r") as zip_ref:
                    zip_ref.extractall(app.config["UPLOAD_FOLDER"])
                os.remove(file_path)

                for extracted_file in os.listdir(app.config["UPLOAD_FOLDER"]):
                    if extracted_file.endswith(".pdf"):
                        pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], extracted_file)
                        output_txt = process_document_sample(pdf_path)
                        if output_txt:
                            output_csv = convert_to_csv(output_txt, os.path.join(app.config["PROCESSED_FOLDER"], f"{extracted_file}.csv"))
                            if output_csv:
                                csv_files.append(output_csv)
            else:
                # Process PDF directly
                output_txt = process_document_sample(file_path)
                if output_txt:
                    output_csv = convert_to_csv(output_txt, os.path.join(app.config["PROCESSED_FOLDER"], f"{filename}.csv"))
                    if output_csv:
                        csv_files.append(output_csv)

    # Merge all CSVs
    final_csv = merge_csv_files(csv_files, COMBINED_CSV)
    if final_csv:
        return "Files uploaded successfully", 200
    else:
        return "Processing failed. No CSV generated.", 500


@app.route("/progress", methods=["GET"])
def get_progress():
    """
    Indicates whether Document AI processing is complete.
    The frontend polls this endpoint.
    """
    return jsonify({"complete": processing_complete})


@app.route("/download", methods=["GET"])
def download_file():
    """
    Allows users to download the final merged CSV.
    """
    if os.path.exists(COMBINED_CSV):
        return send_file(COMBINED_CSV, as_attachment=True)
    return "No CSV file available for download.", 404


if __name__ == "__main__":
    app.run(debug=True)
