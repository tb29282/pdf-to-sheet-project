import pytesseract
from pdf2image import convert_from_path
import os

# Specify Tesseract path if not in system path
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\joyjp\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"  # Update this path on Windows

def process_pdf(pdf_path):
    # Convert PDF to list of images and extract text
    images = convert_from_path(pdf_path)
    text_content = [pytesseract.image_to_string(image) for image in images]
    return "\n\n".join(text_content)

def process_image(image_path):
    # Extract text from a single image file
    return pytesseract.image_to_string(image_path)

def process_patient_folder(patient_folder):
    # Create an output text file for each patient
    patient_id = os.path.basename(patient_folder)
    output_text_path = os.path.join(patient_folder, f"{patient_id}_compiled.txt")
    
    all_text_content = []

    # Process each file in the patient's folder
    for file_name in os.listdir(patient_folder):
        file_path = os.path.join(patient_folder, file_name)
        if file_name.lower().endswith('.pdf'):
            print(f"Processing PDF: {file_name}")
            text = process_pdf(file_path)
        elif file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
            print(f"Processing Image: {file_name}")
            text = process_image(file_path)
        else:
            print(f"Skipping unsupported file type: {file_name}")
            continue
        all_text_content.append(text)
    
    # Write all extracted text to the patient's output file
    with open(output_text_path, 'w') as text_file:
        text_file.write("\n\n".join(all_text_content))
    print(f"Finished processing {patient_id}. Output saved to {output_text_path}")

# Batch process all patients
def batch_process_all_patients(base_folder):
    for patient_folder in os.listdir(base_folder):
        patient_folder_path = os.path.join(base_folder, patient_folder)
        if os.path.isdir(patient_folder_path):
            print(f"\nProcessing documents for {patient_folder}")
            process_patient_folder(patient_folder_path)

# Specify the base folder containing all patient folders
base_folder = r"C:\Users\joyjp\Downloads\Member 124-20241030T115115Z-001\Member 124\Carte"
batch_process_all_patients(base_folder) 
