import pandas as pd
import re

def parse_output(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    data = []
    current_date = None

    # Extract the date from the last two lines
    if lines[-2].startswith("dateoftest:"):
        current_date = lines[-2].split(":")[1].strip()
    elif lines[-1].startswith("dateoftest:"):
        current_date = lines[-1].split(":")[1].strip()

    for i, line in enumerate(lines[:-2]):  # Exclude the last two lines
        if line.startswith("TestTypeandResult:"):
            test_type = line.split(":")[1].strip()
            if i + 1 < len(lines) and not lines[i + 1].startswith("TestTypeandResult:") and not lines[i + 1].startswith("dateoftest:"):
                result = lines[i + 1].strip()
            else:
                result = ""
            data.append((test_type, result, current_date))

    return data

def write_to_sheet(data, sheet):
    # Set the header for the results column as the date
    if data:
        sheet['B1'] = data[0][2]  # Use the date from the first entry

    for row, (test_type, result, date) in enumerate(data, start=2):
        sheet[f'A{row}'] = test_type
        sheet[f'B{row}'] = result

def convert_text_to_csv(input_file, output_file):
    data = parse_output(input_file)
    structured_data = [{"TestType": test_type, "Result": result} for test_type, result, date in data]

    # Convert to DataFrame
    df = pd.DataFrame(structured_data)

    # Set the header for the results column as the date
    if data:
        df.columns = ['TestType', data[0][2]]

    # Save the DataFrame to a CSV file
    df.to_csv(output_file, index=False)
    print(f"CSV file saved at: {output_file}")

#Define input and output file paths
input_file = 'output.txt'  # Change this to your input file path
output_file = 'output_converted.csv'  # Change this to your desired output file path

#Call the function
convert_text_to_csv(input_file, output_file)