import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from inventory.services import process_ingredient_file_upload

class Command(BaseCommand):
    help = "프로젝트 루트의 '식재료_통합_완성본.xlsx' 엑셀 파일을 읽어 식재료 DB에 초기 데이터를 적재/업데이트합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='적재할 엑셀/CSV 파일 경로 (기본값: 프로젝트 루트/식재료_통합_완성본.xlsx)',
            default=None
        )

    def handle(self, *args, **options):
        file_option = options.get('file')
        if file_option:
            file_path = file_option
        else:
            file_path = os.path.join(settings.BASE_DIR, '식재료_통합_완성본.xlsx')

        if not os.path.exists(file_path):
            raise CommandError(f"초기 적재 파일이 존재하지 않습니다: {file_path}")

        self.stdout.write(self.style.NOTICE(f"초기 식재료 데이터 적재를 시작합니다: {file_path}"))

        try:
            created_cnt, updated_cnt = process_ingredient_file_upload(file_path)
            self.stdout.write(
                self.style.SUCCESS(
                    f"성공적으로 완료되었습니다! (신규 등록: {created_cnt}건, 업데이트: {updated_cnt}건)"
                )
            )
        except Exception as e:
            raise CommandError(f"초기 데이터 적재 중 오류 발생 (전체 롤백됨): {e}")
