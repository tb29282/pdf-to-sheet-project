import pandas as pd
import re

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

# Define input and output file paths
input_file = 'output2.txt'  # Change this to your input file path
output_file = 'output_converted2.csv'  # Change this to your desired output file path

# Call the function
convert_text_to_csv(input_file, output_file)
