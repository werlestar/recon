from flask import Flask, render_template, request, Response
import csv
import logging
import os

app = Flask(__name__)

# Set up logging
log_file_path = 'app.log'
logging.basicConfig(filename=log_file_path, level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Function to read CSV file
def read_file(file):
    read_list = []
    with file as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=';')
        for row in csv_reader:
            read_list.append(row)
    return read_list

# Function to clean up amounts in the CSV file
def clean_amounts(data, columns):
    for column in columns:
        for i in range(1, len(data)):
            if ',' in data[i][column]:
                if data[i][column][-2] == ',':
                    data[i][column] += '0'
                data[i][column] = data[i][column].replace(',', '')
                data[i][column] = data[i][column].replace(' ', '')
            else:
                data[i][column] += '00'

# Function to compare transactions in two CSV files
def compare_transactions(file1_data, file2_data, column1, column2):
    uniques_in_file1 = []
    uniques_in_file2 = []

    for row1 in range(1, len(file1_data)):
        unique = True
        for row2 in range(1, len(file2_data)):
            if file1_data[row1][column1] == file2_data[row2][column2]:
                unique = False
                break
        if unique:
            uniques_in_file1.append(file1_data[row1])

    for row2 in range(1, len(file2_data)):
        unique = True
        for row1 in range(1, len(file1_data)):
            if file2_data[row2][column2] == file1_data[row1][column1]:
                unique = False
                break
        if unique:
            uniques_in_file2.append(file2_data[row2])

    return uniques_in_file1, uniques_in_file2

# Function to find column index by column name
def find_column(header, column_name):
    for i, column in enumerate(header):
        if column == column_name:
            return i
    return None

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file1' not in request.files or 'file2' not in request.files:
            logger.error('No file part')
            return 'No file part'

        file1 = request.files['file1']
        file2 = request.files['file2']

        if file1.filename == '' or file2.filename == '':
            logger.error('No selected file')
            return 'No selected file'

        logger.info(f'Files uploaded: {file1.filename}, {file2.filename}')

        if file1 and file2:
            file1_data = read_file(file1)
            file2_data = read_file(file2)

            clean_amounts(file1_data, [4, 5, 6])
            clean_amounts(file2_data, [9, 10, 11, 12])

            vf_trans_column = find_column(file1_data[0], 'Filing code')
            bo_trans_column = find_column(file2_data[0], 'Extern transaktionsreferens')

            if vf_trans_column is None or bo_trans_column is None:
                logger.error('Column not found')
                return 'Column not found'

            logger.info('Comparison started')

            vf_uniques, bo_uniques = compare_transactions(file1_data, file2_data, vf_trans_column, bo_trans_column)

            logger.info('Comparison completed')

            # Generate CSV data
            csv_data = [['Verifone Unique Transactions:'] + [';'.join(row) for row in vf_uniques] + [''],
                        ['Backoffice Unique Transactions:'] + [';'.join(row) for row in bo_uniques]]

            # Define response headers
            headers = {
                "Content-Disposition": "attachment; filename=result.csv",
                "Content-Type": "text/csv"
            }

            # Create response object with CSV data
            csv_response = Response(csv_data, headers=headers)

            logger.info('CSV file generated')

            # Render result.html template with unique transactions
            return render_template('result.html', vf_unika=vf_uniques, bo_unika=bo_uniques), csv_response

    # Render index.html template for initial page load
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
