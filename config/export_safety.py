"""Keep user-provided spreadsheet text literal and worksheet names valid."""
import re


def worksheet_title(value):
    return re.sub(r'[\\/*?:\[\]\x00-\x1f]', '_', str(value))[:31] or '문서'


def literal_workbook(workbook):
    for sheet in workbook:
        for row in sheet:
            for cell in row:
                if isinstance(cell.value, str) and cell.value.lstrip().startswith(('=', '+', '-', '@')):
                    cell.data_type = 's'
    return workbook
