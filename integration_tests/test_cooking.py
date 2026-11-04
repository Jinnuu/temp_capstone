from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from inventory.models import Ingredient, InventoryLog, SupplySpecification
from meals.cooking import cooking_sheet
from meals.models import CookingInstruction, DietMenu, DietPlan, Menu, Recipe


class CookingInstructionsTest(TestCase):
    def setUp(self):
        user = get_user_model()
        self.operator = user.objects.create_user(username='cook-operator', is_staff=True)
        self.vendor = user.objects.create_user(username='cook-vendor', name='공급사', role='SUPPLIER')
        self.client.force_login(self.operator)
        self.ingredient = Ingredient.objects.create(
            name='만두', unit='kg', safe_stock_level=0, supplier=self.vendor)
        self.spec = SupplySpecification.objects.create(ingredient=self.ingredient, supplier=self.vendor,
            label='5kg/통', base_quantity=5, base_unit='kg', order_unit='통', unit_price=100)
        self.menu = Menu.objects.create(name='찐만두', cooking_notes='충분히 가열')
        self.recipe = Recipe.objects.create(menu=self.menu, ingredient=self.ingredient, unit='g', required_amount=100)
        self.plan = DietPlan.objects.create(target_date=date(2026,10,16), meal_type='중식',
            headcount=999, final_headcount=350, is_confirmed=True)
        DietMenu.objects.create(diet_plan=self.plan, menu=self.menu)
        self.url = reverse('meals:cooking_detail', args=[self.plan.pk])

    def test_confirmed_count_units_and_explicit_package(self):
        sheet = cooking_sheet(self.plan)
        self.assertEqual(sheet['warnings'], [])
        self.assertEqual(sheet['rows'][0]['total'], Decimal('35'))
        self.assertEqual(sheet['rows'][0]['package'], Decimal('7'))

    def test_recalculates_after_headcount_change(self):
        self.plan.final_headcount = 351
        self.plan.save()
        row = cooking_sheet(self.plan)['rows'][0]
        self.assertEqual(row['total'], Decimal('35.1'))
        self.assertEqual(row['package'], Decimal('7.02'))  # use amount, no order rounding

    def test_zero_is_valid(self):
        self.plan.final_headcount = 0
        self.assertEqual(cooking_sheet(self.plan)['rows'][0]['total'], 0)

    def test_unconfirmed_never_uses_manual_999(self):
        self.plan.is_confirmed = False
        sheet = cooking_sheet(self.plan)
        self.assertIsNone(sheet['rows'][0]['total'])
        self.assertTrue(sheet['warnings'])

    def test_no_recipe_warning(self):
        self.recipe.delete()
        self.assertIn('레시피가 없습니다', ' '.join(cooking_sheet(self.plan)['warnings']))

    def test_missing_spec_keeps_total_and_does_not_guess_label(self):
        self.spec.delete()
        self.ingredient.spec = '5kg/통'
        self.ingredient.save()
        row = cooking_sheet(self.plan)['rows'][0]
        self.assertEqual(row['total'], 35)
        self.assertIsNone(row['package'])
        self.assertTrue(cooking_sheet(self.plan)['warnings'])

    def test_incompatible_units_warn(self):
        self.recipe.unit = '개'
        self.recipe.save()
        sheet = cooking_sheet(self.plan)
        self.assertIsNone(sheet['rows'][0]['total'])
        self.assertIn('단위 환산 불가', ' '.join(sheet['warnings']))

    def test_save_edit_conflict_and_no_stock_mutation(self):
        data = {'instructions':'가열 후 배식', 'inventory_instructions':'선입고 재고 우선 사용', 'revision':0}
        self.assertEqual(self.client.post(self.url, data).status_code, 302)
        instruction = CookingInstruction.objects.get(diet_plan=self.plan)
        self.assertEqual(instruction.revision, 1)
        data['instructions'] = '다른 수정'
        self.assertContains(self.client.post(self.url, data), '다른 사용자가 수정')
        instruction.refresh_from_db()
        self.assertEqual(instruction.instructions, '가열 후 배식')
        data['revision'] = 1
        self.assertEqual(self.client.post(self.url, data).status_code, 302)
        self.assertEqual(InventoryLog.objects.count(), 0)

    def test_html_navigation_and_date_validation(self):
        self.assertContains(self.client.get(self.url), '조리지시서')
        self.assertContains(self.client.get(reverse('meals:cooking_index'), {'date':'2026-10-16'}), self.url)
        self.assertEqual(self.client.get(reverse('meals:cooking_index'), {'date':'bad'}).status_code, 400)
        self.assertContains(self.client.get(reverse('procurement:workflow')), '조리지시서 조회')

    def test_excel_numeric_total_and_literal_formula_text(self):
        CookingInstruction.objects.create(diet_plan=self.plan, instructions='=1+1')
        response = self.client.get(self.url, {'format':'xlsx'})
        self.assertEqual(response.status_code, 200)
        ws = load_workbook(BytesIO(response.content)).active
        self.assertEqual(ws['E3'].value, '35 kg')
        calc = load_workbook(BytesIO(response.content))['계산근거']
        self.assertEqual(calc['G2'].value, 35)
        self.assertEqual(calc['I2'].value, 7)
        self.assertTrue(any('=1+1' in str(c.value) for row in ws for c in row))
        self.assertFalse(any(c.data_type == 'f' for row in ws for c in row))
        self.assertEqual(ws.page_setup.orientation, 'portrait')

    def test_invalid_revision_and_oversized_notes_rejected(self):
        self.client.post(self.url, {'revision':-1, 'instructions':'x'*10001})
        self.assertFalse(CookingInstruction.objects.exists())

    def test_supplier_and_anonymous_access_denied(self):
        index = reverse('meals:cooking_index')
        for actor, status in [(self.vendor, 403), (None, 302)]:
            if actor:
                self.client.force_login(actor)
            else:
                self.client.logout()
            for url, data in [(index, {}), (index, {'date':'2026-10-16','format':'xlsx'}), (self.url, {}), (self.url, {'format': 'xlsx'})]:
                with self.subTest(actor=actor, url=url, data=data):
                    self.assertEqual(self.client.get(url, data).status_code, status)
            response = self.client.post(self.url, {
                'revision': 0, 'instructions': '접근 불가', 'inventory_instructions': '출고 금지'})
            self.assertEqual(response.status_code, status)
        self.assertFalse(CookingInstruction.objects.exists())
        self.assertFalse(InventoryLog.objects.exists())


    @skipUnless(Path('docs/reference/(8.7~8.9)조리지시서.xlsx').is_file(), '실제 참고 Excel 미제공')
    def test_reference_all_sheets_and_export_structure(self):
        source = load_workbook('docs/reference/(8.7~8.9)조리지시서.xlsx')
        self.assertEqual(source.sheetnames, ['목','금','토','토 (1)','Sheet2','Sheet3'])
        generated = load_workbook(BytesIO(self.client.get(self.url, {'format':'xlsx'}).content))
        main = generated.worksheets[0]
        for original in source.worksheets[:4]:
            self.assertEqual([main.cell(2,c).value for c in range(1,7)], [original.cell(2,c).value for c in range(1,7)])
            self.assertIn('A1:H1', [str(m) for m in original.merged_cells.ranges])
            self.assertEqual(main.page_setup.orientation, original.page_setup.orientation)
            self.assertEqual(main.page_setup.paperSize, original.page_setup.paperSize)
            self.assertEqual(main.page_margins, original.page_margins)
            for col in ['G','H']:
                self.assertTrue(original.column_dimensions[col].hidden)
                self.assertTrue(main.column_dimensions[col].hidden)
            self.assertFalse(any(cell.data_type == 'f' for row in original for cell in row))
        for original in source.worksheets[4:]:
            self.assertFalse(any(c.value is not None for row in original for c in row))
        # Friday is the declared layout reference; no copying example data.
        for col in 'ABCDEFGH':
            self.assertEqual(main.column_dimensions[col].width, source['금'].column_dimensions[col].width)
        self.assertIn('A1:H1', [str(m) for m in main.merged_cells.ranges])
        self.assertEqual(main.row_dimensions[1].height, source['금'].row_dimensions[1].height)
        self.assertEqual(main['A2'].font.name, source['금']['A2'].font.name)
        self.assertEqual(main['A2'].border.bottom.style, 'thin')
        self.assertEqual(main.print_title_rows, '$1:$2')
        self.assertIn('A$1:$F$', str(main.print_area))
        self.assertEqual(main.page_setup.fitToWidth, 1)
        self.assertEqual(main.page_setup.fitToHeight, 0)
        self.assertIn('2026-10-16', main['A1'].value)
        self.assertNotIn('입고분', main['A1'].value)

    def test_line_notes_save_export_and_conflicting_revision(self):
        key = f'line_{self.recipe.pk}'
        self.assertEqual(self.client.post(self.url, {'revision':0, key:'=1+1'}).status_code,302)
        saved=CookingInstruction.objects.get(diet_plan=self.plan)
        self.assertEqual(saved.line_notes[str(self.recipe.pk)], '=1+1')
        response=self.client.get(self.url)
        self.assertContains(response,'=1+1')
        wb=load_workbook(BytesIO(self.client.get(self.url, {'format':'xlsx'}).content))
        self.assertEqual(wb['계산근거']['M2'].value, '=1+1')
        self.assertEqual(wb['계산근거']['M2'].data_type, 's')
        self.assertContains(self.client.post(self.url, {'revision':0,key:'덮어쓰기'}),'다른 사용자가 수정')
        saved.refresh_from_db();self.assertEqual(saved.line_notes[str(self.recipe.pk)],'=1+1')
        self.assertFalse(InventoryLog.objects.exists())

    def test_daily_workbook_separate_meals_and_confirmed_counts(self):
        for meal,count in [('조식',0),('석식',7)]:
            plan=DietPlan.objects.create(target_date=self.plan.target_date,meal_type=meal,
                headcount=999,final_headcount=count,is_confirmed=True)
            DietMenu.objects.create(diet_plan=plan,menu=self.menu)
        response=self.client.get(reverse('meals:cooking_index'),{'date':'2026-10-16','format':'xlsx'})
        wb=load_workbook(BytesIO(response.content))
        self.assertEqual(wb.sheetnames,['1016-조식','1016-중식','1016-석식','계산근거'])
        self.assertEqual([wb[name]['B3'].value for name in wb.sheetnames[:3]],[0,350,7])
        self.assertEqual([wb['계산근거'].cell(i,7).value for i in [2,3,4]],[0,35,.7])
        self.assertEqual(self.client.get(reverse('meals:cooking_index'),{'date':'2026-10-17','format':'xlsx'}).status_code,404)

    def test_long_notes_continue_and_print_pages_repeat_headers(self):
        note='재고부터 사용하고 충분히 가열하세요. '*100
        CookingInstruction.objects.create(diet_plan=self.plan,
            line_notes={str(self.recipe.pk):note},instructions='현장 지시 '*500)
        wb=load_workbook(BytesIO(self.client.get(self.url,{'format':'xlsx'}).content))
        ws=wb.worksheets[0]
        self.assertTrue(ws.row_breaks.brk)
        self.assertEqual(ws.print_title_rows,'$1:$2')
        self.assertTrue(any('(계속)' in str(c.value) for row in ws for c in row))
        self.assertTrue(all(d.height <= 255 for d in ws.row_dimensions.values() if d.height))
        self.assertEqual(wb['계산근거']['M2'].value,note)
