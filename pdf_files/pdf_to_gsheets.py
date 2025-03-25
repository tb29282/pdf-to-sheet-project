import fitz  # PyMuPDF
import tabula
import pandas as pd
import re


def extract_dates(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""

    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text += page.get_text()

    # Define the pattern to match dates
    date_pattern = re.compile(r'^[A-Za-z]{3} \d{1,2}, \d{4}')
    dates = []
    date_ranges = []

    # Split the text into lines and extract dates
    lines = text.splitlines()

    for line in lines:
        if date_pattern.match(line) and '-' not in line:
            date = line.strip()
            dates.append(date)

    # Remove duplicates and sort dates
    unique_dates = sorted(set(dates), key=lambda date: pd.to_datetime(date, format='%b %d, %Y'))
    
    return unique_dates

def extract_test_results(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text += page.get_text()

    # Initialize storage for test results
    results = []
    lines = text.splitlines()

    for line in lines:
        line = line.strip()

        # Extract result values (assume ng/mL indicates a result)
        if re.match(r'^\d+ ng/mL', line):
            results.append(line.strip())

    return results

def extract_test_types_and_normal_range(text):
    lines = text.splitlines()
    test_types = []
    normal_ranges = []
    capture = False
    current_test = ""
    current_normal_range = ""

    for line in lines:
        line = line.strip()

        # Start capturing after a line that contains 'Component'
        if "Component" in line:
            capture = True
            continue
        
        # Stop capturing if we encounter 'Normal Range'
        if "Normal Range:" in line:
            capture = False
            current_normal_range = line.split("Normal Range:")[1].strip()
        
        # Skip lines that look like dates
        if re.match(r'^[A-Za-z]{3} \d{1,2}, \d{4}', line):
            continue
        
        # Capture lines as test types
        if capture and re.match(r'^[A-Za-z0-9, \-]+$', line):
            if current_test:
                current_test += " " + line
            else:
                current_test = line

        # Save the captured test type and normal range
        if not capture and current_test:
            test_types.append(current_test.strip())
            normal_ranges.append(current_normal_range.strip())
            current_test = ""
            current_normal_range = ""

    # Ensure the last captured test type and normal range are added
    if current_test:
        test_types.append(current_test.strip())
        normal_ranges.append(current_normal_range.strip())

    return test_types, normal_ranges

def extract_test_types_and_ranges(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text += page.get_text()

    return extract_test_types_and_normal_range(text)

# Extract dates, test results, and test types with normal ranges
pdf_path = r'pdfs\2024 08 test res 4.pdf'
dates = extract_dates(pdf_path)
results = extract_test_results(pdf_path)
test_types, normal_ranges = extract_test_types_and_ranges(pdf_path)

# Prepare data for CSV
max_len = max(len(dates), len(results), len(test_types))
data_reordered = {
    'Test Type': test_types + [''] * (max_len - len(test_types)),
    'Normal Range': normal_ranges + [''] * (max_len - len(normal_ranges)),
    'Date': dates + [''] * (max_len - len(dates)),
    'Result': results + [''] * (max_len - len(results))
}

# Convert to DataFrame
df_reordered = pd.DataFrame(data_reordered)

# Save to CSV with the correct column order
csv_reordered_path = r'C:\Users\joyjp\Desktop\Carte Clinics Project\pdf_to_sheet_project\pdf_files\test_results2.csv'
df_reordered.to_csv(csv_reordered_path, index=False)
