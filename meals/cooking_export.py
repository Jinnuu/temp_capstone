"""Cooking workbook layout based on the dietitian's six visible columns.

The example is a read-only reference, never a runtime template or seed database.
"""
from decimal import Decimal
from io import BytesIO
import unicodedata

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.worksheet.page import PageMargins
from openpyxl.worksheet.pagebreak import Break

from .cooking import display_quantity

HEADERS = ['날짜', '예상식수', '메뉴', '재료', '총량', '비고']
WIDTHS = {'A': 5, 'B': 5.5, 'C': 20, 'D': 17.5, 'E': 8.375, 'F': 23.75,
          'G': 8.875, 'H': 9}
WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']


def wrap_lines(text, width):
    """Conservative Excel column-character widths, including Korean glyphs."""
    result=[]
    for line in text.splitlines() or ['']:
        part='';used=0
        for char in line:
            size=0 if unicodedata.combining(char) else (2 if unicodedata.east_asian_width(char) in 'WF' else 1)
            if part and used+size>width:
                result.append(part);part='';used=0
            part+=char;used+=size
        result.append(part)
    return result


def literal(cell, value):
    cell.value = value
    if isinstance(value, str):
        cell.data_type = 's'


def workbook(sheets):
    wb = Workbook()
    wb.remove(wb.active)
    evidence = []
    for sheet, instruction in sheets:
        plan = sheet['plan']
        name = f'{plan.target_date:%m%d}-{plan.meal_type}'
        ws = wb.create_sheet(name)
        ws.sheet_format.defaultRowHeight = 16.5
        for col, width in WIDTHS.items():
            ws.column_dimensions[col].width = width
        ws.column_dimensions['G'].hidden = ws.column_dimensions['H'].hidden = True
        ws.merge_cells('A1:H1')
        literal(ws['A1'], f'{plan.target_date:%Y-%m-%d} ({WEEKDAYS[plan.target_date.weekday()]}) {plan.meal_type} 조리지시서')
        ws['A1'].font = Font(name='맑은 고딕', size=11)
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[1].height = 26.25
        thin = Side(style='thin', color='000000')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        for c, label in enumerate(HEADERS, 1):
            literal(ws.cell(2, c), label)
            ws.cell(2,c).font = Font(name='맑은 고딕',size=11)
            ws.cell(2,c).alignment = Alignment(horizontal='center',vertical='center',wrap_text=True)
            ws.cell(2,c).border = border
        ws.row_dimensions[2].height = 23
        used_height = 0
        # Repeat the title and header on every vertical page. Budget leaves
        # room for margins, footer and printer differences; no fit-to-one-page height.
        row_number = 3
        previous_menu = None
        for row in sheet['rows']:
            remark = '\n'.join(filter(None, [row.get('notes',''),row.get('remark','')]))
            if row.get('package') is not None:
                remark += ('\n' if remark else '') + f"{display_quantity(row['package'])} {row['package_unit']} 사용분 / {row['specification']}"
            ingredient = row['ingredient']
            if row.get('per_person') is not None:
                ingredient += f"\n1인량 {display_quantity(row['per_person'])} {row['recipe_unit']}"
            total = '계산 불가' if row.get('total') is None else f"{display_quantity(row['total'])} {row['unit']}"
            # Never silently clip a long instruction into a fixed-height row:
            # split it into continuation lines, each with date/menu context.
            lines = wrap_lines(remark, 20)
            chunks = [lines[i:i+8] for i in range(0,len(lines),8)]
            for part, chunk in enumerate(chunks):
                height = max(52, 15 * max(len(chunk),len(wrap_lines(ingredient,14)),len(wrap_lines(row['menu'],18))))
                page_start = used_height + height > 620
                if page_start:
                    ws.row_breaks.append(Break(id=row_number-1))
                    used_height = 0
                menu_label = row['menu'] if previous_menu != row['menu'] or page_start or part else ''
                if part:
                    menu_label = row['menu'] + ' (계속)'
                values = [f'{plan.target_date:%m/%d}\n({WEEKDAYS[plan.target_date.weekday()]})\n{plan.meal_type}',
                          sheet['headcount'] if sheet['confirmed'] else '미확정',
                          menu_label, ingredient if not part else row['ingredient']+' (계속)',
                          total if not part else '위 행 참조', '\n'.join(chunk)]
                for c,value in enumerate(values,1):
                    cell=ws.cell(row_number,c)
                    literal(cell,value)
                    cell.font=Font(name='맑은 고딕',size=12)
                    cell.alignment=Alignment(horizontal='center' if c<4 else 'left',vertical='center',wrap_text=True)
                    cell.border=border
                ws.row_dimensions[row_number].height=height
                row_number+=1
                used_height+=height
                previous_menu=row['menu']
            evidence.append([str(plan.target_date),plan.meal_type,row['menu'],row['ingredient'],
                row.get('per_person'),row.get('recipe_unit'),row.get('total'),row.get('unit'),
                row.get('package'),row.get('package_unit'),row.get('specification'),row.get('supplier'),row.get('remark','')])
        notes = [('재고 사용 지시', instruction.inventory_instructions),
                 ('현장 조리 지시·비고', instruction.instructions),
                 ('계산 안내','현재 최종 확정 식수로 재계산. 포장 환산은 사용량이며 발주 올림량과 다름. 단위·계산근거는 계산근거 시트 참조. 재고 자동 차감 없음.')]
        notes += [('경고',warning) for warning in sheet['warnings']]
        # Long document-level notes also use bounded continuation rows.
        for label,text in notes:
            if not text:
                continue
            wrapped=wrap_lines(text,65)
            for i in range(0,len(wrapped),8):
                chunk=wrapped[i:i+8]
                height=max(24,len(chunk)*15)
                if used_height+height>620:
                    ws.row_breaks.append(Break(id=row_number-1));used_height=0
                ws.merge_cells(start_row=row_number,start_column=1,end_row=row_number,end_column=6)
                cell=ws.cell(row_number,1)
                literal(cell,label+': '+'\n'.join(chunk))
                cell.font=Font(name='맑은 고딕',size=11)
                cell.alignment=Alignment(wrap_text=True,vertical='top')
                ws.row_dimensions[row_number].height=height+15
                used_height+=height+15;row_number+=1
        ws.freeze_panes='D3'
        ws.print_title_rows='1:2'
        ws.print_area=f'A1:F{row_number-1}'
        ws.page_setup.orientation='portrait'
        ws.page_setup.paperSize=ws.PAPERSIZE_A4
        ws.sheet_properties.pageSetUpPr.fitToPage=True
        ws.page_setup.fitToWidth=1
        ws.page_setup.fitToHeight=0
        ws.page_margins=PageMargins(left=.7,right=.7,top=.75,bottom=.75,header=.3,footer=.3)
        ws.oddFooter.center.text='&P / &N'
    calc=wb.create_sheet('계산근거')
    calc.append(['날짜','식사','메뉴','재료','1인량','기준 단위','총량','재고 단위','포장 환산량','포장 단위','납품규격','업체','재료별 비고'])
    for values in evidence:
        calc.append(values)
    for row in calc:
        for cell in row:
            if isinstance(cell.value,str):cell.data_type='s'
            cell.alignment=Alignment(wrap_text=True,vertical='top')
            cell.font=Font(name='맑은 고딕',size=11)
            if isinstance(cell.value,Decimal):cell.number_format='0.######'
    for col in 'ABCDEFGHIJKLM':calc.column_dimensions[col].width=20
    calc.print_title_rows='1:1'
    calc.freeze_panes='E2'
    calc.page_setup.orientation='landscape'
    calc.page_setup.paperSize=calc.PAPERSIZE_A4
    calc.sheet_properties.pageSetUpPr.fitToPage=True
    calc.page_setup.fitToWidth=1;calc.page_setup.fitToHeight=0
    calc.print_area=calc.dimensions
    stream=BytesIO();wb.save(stream)
    return stream.getvalue()
