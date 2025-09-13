import csv
import sys

if len(sys.argv) != 4:
    print("Usage: python extract_column.py <input.csv> <coloana> <output.csv>")
    sys.exit(1)

input_file = sys.argv[1]
column_name = sys.argv[2]
output_file = sys.argv[3]

with open(input_file, newline='') as infile:
    reader = csv.DictReader(infile)
    if column_name not in reader.fieldnames:
        print(f"Column '{column_name}'was not found.")
        sys.exit(1)

    with open(output_file, "w", newline='') as outfile:
        for row in reader:
            value = row[column_name].replace(".", ",")
            outfile.write(value + "\n")
