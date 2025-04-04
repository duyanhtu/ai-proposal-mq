import openpyxl

from app.utils.exporter_v2 import process_excel_file_no_upload


def run():
    # Get the FileResponse object
    response = process_excel_file_no_upload(637)

    # Extract the file path from the response
    file_path = response.path

    print(f"Excel file created at: {file_path}")

    # Open the workbook
    workbook = openpyxl.load_workbook(file_path)

    # Print sheet names
    print(f"Sheets in the workbook: {workbook.sheetnames}")

    # Access the first sheet
    sheet = workbook.active
    print("First few rows of active sheet:")
    for row in list(sheet.rows)[:5]:
        print([cell.value for cell in row])


if __name__ == "__main__":
    run()
