from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import PurchaseOrder

User = get_user_model()

class PurchaseOrderStatusUpdateTest(TestCase):
    def setUp(self):
        # 테스트 유저 생성
        self.user = User.objects.create_user(username='test_supplier', password='password123')
        # PENDING 상태의 발주서 생성
        self.order = PurchaseOrder.objects.create(supplier=self.user, status=PurchaseOrder.Status.PENDING)

    def test_order_status_update_success(self):
        """정상적으로 발주 상태가 업데이트 되는지 확인하는 테스트"""
        url = reverse('procurement:order_status_update', kwargs={'pk': self.order.pk})
        
        # '대기'에서 '승인'으로 변경 요청
        response = self.client.post(url, data={'status': PurchaseOrder.Status.APPROVED})
        
        # 리다이렉트 응답 확인 (302)
        self.assertRedirects(response, reverse('procurement:order_detail', kwargs={'pk': self.order.pk}))
        
        # 새로운 상태가 DB에 잘 반영되었는지 확인
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, PurchaseOrder.Status.APPROVED)

    def test_order_status_update_invalid(self):
        """존재하지 않는 상태값으로의 변경은 무시되는지 테스트"""
        url = reverse('procurement:order_status_update', kwargs={'pk': self.order.pk})
        
        # 비정상적인 상태 문자열 전달
        response = self.client.post(url, data={'status': '잘못된상태'})
        
        self.assertRedirects(response, reverse('procurement:order_detail', kwargs={'pk': self.order.pk}))
        
        # 모델의 상태가 기존(대기) 그대로인지 확인
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, PurchaseOrder.Status.PENDING)
