from datetime import date

from django import forms
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .cooking_export import workbook

from .cooking import cooking_sheet
from .models import CookingInstruction, DietPlan, Recipe


class CookingForm(forms.ModelForm):
    revision = forms.IntegerField(min_value=0, widget=forms.HiddenInput)

    class Meta:
        model = CookingInstruction
        fields = ['instructions', 'inventory_instructions', 'revision']
        widgets = {'instructions': forms.Textarea(attrs={'rows': 5, 'maxlength': 10000}),
                   'inventory_instructions': forms.Textarea(attrs={'rows': 4, 'maxlength': 10000})}

    def __init__(self, *args, plan, **kwargs):
        super().__init__(*args, **kwargs)
        self.line_keys = []
        notes = self.instance.line_notes or {}
        for recipe in Recipe.objects.filter(menu__dietmenu__diet_plan=plan).select_related('menu','ingredient').order_by('menu__name','ingredient__name'):
            key = f'line_{recipe.pk}'
            self.line_keys.append((key,str(recipe.pk)))
            self.fields[key] = forms.CharField(
                label=f'{recipe.menu.name} / {recipe.ingredient.name} 비고',
                required=False, max_length=10000,
                initial=notes.get(str(recipe.pk),''),
                widget=forms.Textarea(attrs={'rows':2}))

    def clean(self):
        data = super().clean()
        for key in ['instructions', 'inventory_instructions']:
            if len(data.get(key, '')) > 10000:
                self.add_error(key, '10,000자 이하로 입력하세요.')
        return data


@require_http_methods(['GET'])
def cooking_index(request):
    raw = request.GET.get('date', timezone.localdate().isoformat())
    try:
        selected = date.fromisoformat(raw)
    except ValueError:
        return HttpResponse('날짜 형식은 YYYY-MM-DD입니다.', status=400)
    plans = DietPlan.objects.filter(target_date=selected, meal_type__in=['조식','중식','석식'])
    plans = sorted(plans, key=lambda p: ['조식','중식','석식'].index(p.meal_type))
    if request.GET.get('format') == 'xlsx':
        if not plans:
            return HttpResponse('해당 날짜의 식단이 없습니다.', status=404)
        sheets=[]
        for plan in plans:
            instruction=CookingInstruction.objects.filter(diet_plan=plan).first() or CookingInstruction(diet_plan=plan)
            sheets.append((cooking_sheet(plan,instruction.line_notes),instruction))
        response=HttpResponse(workbook(sheets),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition']=f'attachment; filename="cooking-{selected}.xlsx"'
        return response
    return render(request, 'workflow/cooking_index.html', {'plans': plans, 'selected': selected.isoformat()})


def spreadsheet(sheet, instruction):
    return workbook([(sheet, instruction)])


@require_http_methods(['GET', 'POST'])
def cooking_detail(request, pk):
    plan = get_object_or_404(DietPlan, pk=pk, meal_type__in=['조식','중식','석식'])
    instruction = CookingInstruction.objects.filter(diet_plan=plan).first() or CookingInstruction(diet_plan=plan)
    form = CookingForm(request.POST if request.method == 'POST' else None, instance=instruction, plan=plan)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            # Lock the existing parent as well as the optional child to serialize first creation.
            DietPlan.objects.select_for_update().get(pk=plan.pk)
            current = CookingInstruction.objects.select_for_update().filter(diet_plan=plan).first()
            if form.cleaned_data['revision'] != (current.revision if current else 0):
                form.add_error(None, '다른 사용자가 수정했습니다. 새로고침 후 다시 입력하세요.')
            else:
                saved = current or CookingInstruction(diet_plan=plan)
                saved.instructions = form.cleaned_data['instructions']
                saved.inventory_instructions = form.cleaned_data['inventory_instructions']
                saved.line_notes = dict(saved.line_notes or {})
                for field,key in form.line_keys:
                    saved.line_notes[key] = form.cleaned_data[field]
                saved.revision += 1
                saved.save()
                messages.success(request, '조리지시서를 저장했습니다. 실제 재고는 변경하지 않았습니다.')
                return redirect('meals:cooking_detail', pk=plan.pk)
    sheet = cooking_sheet(plan, instruction.line_notes)
    if request.GET.get('format') == 'xlsx' and request.method == 'GET':
        response = HttpResponse(spreadsheet(sheet, instruction), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="cooking-{plan.pk}.xlsx"'
        return response
    for row in sheet['rows']:
        if row.get('recipe_id'):
            row['note_field'] = form[f"line_{row['recipe_id']}"]
    return render(request, 'workflow/cooking_detail.html', {**sheet, 'form': form, 'instruction': instruction})
