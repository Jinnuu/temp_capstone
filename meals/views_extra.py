from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse


def monthly_mealplan_create(request):
    if request.method == "POST":
        messages.info(
            request,
            "월간 식단 등록 저장 로직은 추후 연결 예정입니다. 현재는 화면 미리보기 단계입니다.",
        )
        return redirect("meals:mealplan_list")

    return render(request, "meals/monthly_mealplan_create.html")


def mealplan_bulk_upload(request):
    if request.method == "POST":
        uploaded_file = request.FILES.get("mealplan_file")

        if not uploaded_file:
            messages.error(request, "CSV 또는 XLSX 파일을 선택해 주세요.")
            return redirect("meals:mealplan_bulk_upload")

        messages.info(
            request,
            f"{uploaded_file.name} 파일 업로드 화면까지 연결되었습니다. 실제 파싱 로직은 추후 구현 예정입니다.",
        )
        return redirect("meals:mealplan_list")

    return render(request, "meals/mealplan_bulk_upload.html")
