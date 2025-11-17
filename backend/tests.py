import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orders.settings')
django.setup()

from unittest.mock import patch
from django.test import TestCase
from django.test.utils import override_settings
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from backend.models import (User, Shop, Category, Product,
                            ProductInfo, Parameter, ProductParameter,
                            Order, OrderItem, Contact)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AuthTestCase(TestCase):
    def setUp(self):
        """
        Подготовка тестовых данных
        """
        self.api_client = APIClient()
        self.username = 'testuser'
        self.password = 'testpass'
        self.email = 'test@example.com'

        # Получаем или создаем пользователя
        self.user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': self.email
            }
        )
        self.user.set_password(self.password) # Устанавливаем пароль
        self.user.is_active = True
        self.user.save()

        # Проверяем наличие токена, иначе создаем
        self.token, created = Token.objects.get_or_create(user=self.user)

    def test_login_success_returns_token(self):
        """
        Проверка успешного входа пользователя и получения токена
        """
        resp = self.api_client.post(
            '/api/v1/user/login',
            {'email': self.user.email,
             'password': self.password},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get('Status'))
        self.assertIn('Token', resp.json())

    def test_login_fails_with_bad_credentials(self):
        """
        Проверка неуспешного входа пользователя с неправильными данными
        """
        resp = self.api_client.post(
            '/api/v1/user/login',
            {'email': self.user.email,
             'password': 'bad'},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get('Status'))
        self.assertIn('Errors', resp.json())

    def test_logout_requires_authentication(self):
        """
        Проверка неуспешного выхода пользователя без аутентификации
        """
        resp = self.api_client.post(
            '/api/v1/user/logout',
            {},
            format='json'
        )
        self.assertEqual(resp.status_code, 401)

    def test_logout_succeeds_when_authenticated(self):
        """
        Проверка успешного выхода пользователя с аутентификацией
        """
        # Используем токен созданный в setUp
        token = self.token
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        resp = self.api_client.post(
            '/api/v1/user/logout',
            {},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get('Status'))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PartnerStateTests(TestCase):
    """
    Тесты для проверки изменения состояния магазина партнера
    """
    def setUp(self):
        """
        Подготовка тестовых данных
        """
        self.api_client = APIClient()
        self.password = 'Str0ngP@ssw0rd!'
        self.partner = User.objects.create_user(
            email='shop@example.com',
            username='shopuser',
            password=self.password,
            first_name='Shop',
            last_name='Keeper'
        )
        self.partner.type = 'shop'
        self.partner.is_active = True
        self.partner.save()
        self.shop = Shop.objects.create(
            user=self.partner,
            name='Test Shop',
            state=False
        )
        self.token = Token.objects.create(user=self.partner)
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_get_partner_state_requires_shop_type(self):
        """
        Проверка доступа к состоянию магазина только для пользователей типа "shop"
        """
        self.partner.type = 'buyer'
        self.partner.save()
        resp = self.api_client.get(
            '/api/v1/partner/state',
            format='json'
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(resp.json().get('Status'))

    def test_post_partner_state_accepts_various_truthy_values(self):
        """
        Проверка принятия различных истинных значений для состояния магазина
        """
        resp = self.api_client.post(
            '/api/v1/partner/state',
            {'state': 'YES'},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get('Status'))
        self.shop.refresh_from_db()
        self.assertTrue(self.shop.state)

    def test_post_partner_state_accepts_various_falsy_values(self):
        """
        Проверка принятия различных ложных значений для состояния магазина
        """
        resp = self.api_client.post(
            '/api/v1/partner/state',
            {'state': '0'},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get('Status'))
        self.shop.refresh_from_db()
        self.assertFalse(self.shop.state)

    def test_post_partner_state_missing_value(self):
        """
        Проверка обработки отсутствующего значения состояния магазина
        """
        resp = self.api_client.post(
            '/api/v1/partner/state',
            {},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get('Status'))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class BasketTests(TestCase):
    """
    Тесты для проверки работы корзины покупателя
    """
    def setUp(self):
        """
        Подготовка тестовых данных
        """
        self.api_client = APIClient()
        self.password = 'Str0ngP@ssw0rd!'
        self.user = User.objects.create_user(
            email='buyer@example.com',
            username='buyer',
            password=self.password,
            first_name='Buyer',
            last_name='One'
        )
        self.user.is_active = True
        self.user.save()
        self.token = Token.objects.create(user=self.user)
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        self.category = Category.objects.create(name='Phones')
        self.shop_user = User.objects.create_user(
            email='seller@example.com',
            username='seller',
            password=self.password
        )
        self.shop_user.type = 'shop'
        self.shop_user.save()
        self.shop = Shop.objects.create(
            user=self.shop_user,
            name='Seller Shop',
            state=True
        )
        self.category.shops.add(self.shop)
        self.product = Product.objects.create(
            name='iPhone',
            category=self.category
        )
        self.pinfo = ProductInfo.objects.create(
            product=self.product,
            external_id=1,
            model='14',
            price=1000,
            price_rrc=1200,
            quantity=10,
            shop=self.shop
        )
        self.param = Parameter.objects.create(name='color')
        ProductParameter.objects.create(
            product_info=self.pinfo,
            parameter=self.param,
            value='black'
        )

    def test_add_item_to_basket_with_json_items(self):
        """
        Тест добавления товара в корзину с использованием JSON для передачи списка товаров
        """
        payload = [{"product_info": self.pinfo.id, "quantity": 2}]
        resp = self.api_client.post(
            '/api/v1/basket',
            {'items': json_dumps(payload)},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('Status'))
        basket = Order.objects.get(user=self.user, status='basket')
        self.assertEqual(OrderItem.objects.filter(order=basket).count(), 1)

    def test_update_item_quantity_in_basket(self):
        """
        Тест обновления количества товара в корзине
        """
        basket = Order.objects.create(user=self.user, status='basket')
        item = OrderItem.objects.create(
            order=basket,
            product_info=self.pinfo,
            quantity=1
        )
        payload = [{"id": item.id, "quantity": 5}]
        resp = self.api_client.put(
            '/api/v1/basket',
            {'items': json_dumps(payload)},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 5)

    def test_delete_items_from_basket(self):
        """
        Тест удаления товаров из корзины
        """
        basket = Order.objects.create(user=self.user, status='basket')
        item1 = OrderItem.objects.create(
            order=basket,
            product_info=self.pinfo,
            quantity=1
        )
        # создаем вторую позицию с другим ProductInfo, так как (order, product_info) должно быть уникальным
        pinfo2 = ProductInfo.objects.create(
            product=self.product,
            external_id=2,
            model='14',
            price=1000,
            price_rrc=1200,
            quantity=10,
            shop=self.shop
        )
        item2 = OrderItem.objects.create(
            order=basket,
            product_info=pinfo2,
            quantity=2
        )
        resp = self.api_client.delete(
            '/api/v1/basket',
            {'items': f'{item1.id},{item2.id}'},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get('Status'))
        self.assertEqual(OrderItem.objects.filter(order=basket).count(), 0)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RegistrationTests(TestCase):
    """
    Тесты для проверки регистрации пользователей
    """
    @patch('backend.views.new_user_registered')
    def test_register_account_success_and_signal_emitted(self, mock_signal):
        """
        Тест успешной регистрации пользователя и проверки отправки сигнала
        """
        client = APIClient()
        payload = {
            'first_name': 'Alice',
            'last_name': 'Smith',
            'email': 'alice@example.com',
            'password': 'StrongP@ssw0rd!1',
            'company': 'ACME',
            'position': 'Engineer'
        }
        resp = client.post(
            '/api/v1/user/register',
            payload,
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get('Status'))
        self.assertTrue(User.objects.filter(email=payload['email']).exists())
        mock_signal.send.assert_called()

    def test_register_account_password_validation_errors(self):
        """
        Тест регистрации пользователя с некорректным паролем и проверка ошибок валидации
        """
        client = APIClient()
        payload = {
            'first_name': 'Bob',
            'last_name': 'Smith',
            'email': 'bob@example.com',
            'password': 'weak',
            'company': 'ACME',
            'position': 'Engineer'
        }
        resp = client.post(
            '/api/v1/user/register',
            payload,
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get('Status'))
        self.assertIn('password', resp.json().get('Errors', {}))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class OrdersFlowTests(TestCase):
    """
    Тесты для проверки процесса оформления заказа из корзины
    """
    @patch('backend.views.new_order')
    def test_make_order_from_basket(self, mock_signal):
        """
        Тест оформления заказа из корзины и проверки отправки сигнала
        """
        client = APIClient()
        password = 'Str0ngP@ssw0rd!'
        buyer = User.objects.create_user(email='ordbuyer@example.com', username='ordbuyer', password=password)
        buyer.is_active = True
        buyer.save()
        token = Token.objects.create(user=buyer)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # подготовка товаров и контакта
        category = Category.objects.create(name='TV')
        shop_user = User.objects.create_user(email='tvshop@example.com', username='tvshop', password=password)
        shop_user.type = 'shop'
        shop_user.save()
        shop = Shop.objects.create(user=shop_user, name='TV Shop', state=True)
        category.shops.add(shop)
        product = Product.objects.create(name='Big TV', category=category)
        pinfo = ProductInfo.objects.create(
            product=product,
            external_id=1,
            model='QLED',
            price=2000,
            price_rrc=2500,
            quantity=5,
            shop=shop
        )
        contact = Contact.objects.create(
            user=buyer,
            city='City',
            street='Street',
            house='1',
            phone='123'
        )

        # добавление товара в корзину
        resp_add = client.post(
            '/api/v1/basket',
            {'items': json_dumps([{ 'product_info': pinfo.id, 'quantity': 1 }])},
            format='json'
        )
        self.assertEqual(resp_add.status_code, 200)
        # делаем заказ из корзины
        resp = client.post(
            '/api/v1/orders',
            {'contact_id': str(contact.id)},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get('Status'))
        mock_signal.send.assert_called()


# вспомогательная функция для сериализации в JSON
import json

def json_dumps(obj):
    return json.dumps(obj)
