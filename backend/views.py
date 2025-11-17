from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from enum import Enum
from typing import Optional
from requests import get
from yaml import load as load_yaml, Loader
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from ujson import loads as load_json
from backend.signals import new_user_registered, new_order
from .models import User, Shop, Category, Product, ProductInfo, \
    Parameter, ProductParameter, Contact, Order, OrderItem, ConfirmEmailToken
from .serializers import UserSerializer, ShopSerializer, \
    CategorySerializer, ProductSerializer, ProductInfoSerializer, \
    OrderSerializer, OrderItemSerializer, ContactSerializer
from .services.importer import import_data_from_yaml


class BooleanState(Enum):
    TRUE = 'true'
    FALSE = 'false'

def parse_boolean_state(state_str: str) -> Optional[bool]:
    """
    Преобразует строковое представление булевого состояния в булево значение.
    Возвращает None, если строка не соответствует ни одному из ожидаемых значений.
    """
    if not state_str:
        return None

    mapping = {
        'true': True, 'yes': True, '1': True, 'y': True, 'on': True,
        'false': False, 'no': False, '0': False, 'n': False, 'off': False
    }

    return mapping.get(state_str.lower().strip())


class ShopUpdate(APIView):
    """
    Импорт товаров
    """
    def post(self, request, *args, **kwargs):
        stats = import_data_from_yaml()
        return Response(stats)


class RegisterAccountView(APIView):
    """
    Регистрация нового пользователя
    """
    def post(self, request, *args, **kwargs):
        if {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(request.data):
            # Валидация пароля на сложность
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                for error in password_error:
                    error_array.append(error)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
            else:
                # Сериализация данных пользователя и проверка на валидность
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    user = user_serializer.save()
                    user.set_password(request.data['password'])    # Хешируем пароль
                    user.save()    # Сохраняем хешированный пароль
                    new_user_registered.send(sendler=self.__class__, user_id=user.id)
                    return JsonResponse({'Status': True, 'Message': 'Регистрация прошла успешно'})
                else:
                    return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


class ConfirmAccountView(APIView):
    """
    Подтверждение регистрации пользователя, подтверждает email.
    """
    def post(self, request, *args, **kwargs):
        if {'email', 'token'}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(email=request.data['email'],
                                                     key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({'Status': True, 'Message': 'Регистрация подтверждена'})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неправильный email или токен'})
        return JsonResponse({'Status': False, 'Errors': 'Не передан email или токен'})


class AccountDetailsView(APIView):
    """
    Получение и изменение данных пользователя
    """
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            user_serializer = UserSerializer(request.user)
            return JsonResponse({'Status': True, 'User': user_serializer.data})
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'}, status=403)

    def patch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if 'password' in request.data:
                try:
                    validate_password(request.data['password'])
                except Exception as password_error:
                    error_array = []
                    for error in password_error:
                        error_array.append(error)
                    return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
                else:
                    request.user.set_password(request.data['password'])
                    request.user.save()

            user_serializer = UserSerializer(request.user, data=request.data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()
                return JsonResponse({'Status': True, 'Message': 'Данные успешно обновлены'})
            else:
                return JsonResponse({'Status': False, 'Errors': user_serializer.errors})
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'}, status=403)


class LoginAccountView(APIView):
    """
    Авторизация пользователя
    """
    def post(self, request, *args, **kwargs):
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])
            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    return JsonResponse({'Status': True, 'Token': token.key})
            return JsonResponse({'Status': False, 'Errors': 'Неправильный email или пароль'})
        return JsonResponse({'Status': False, 'Errors': 'Не передан email или пароль'})


class LogoutAccountView(APIView):
    """
    Выход пользователя
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        # DRF ensures user is authenticated due to permission_classes
        request.user.auth_token.delete()
        return JsonResponse({'Status': True, 'Message': 'Вы успешно вышли из системы'})


class ShopListView(APIView):
    """
    Получение списка всех магазинов
    """
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer(queryset, many=True)


class ShopDetailView(APIView):
    """
    Получение данных конкретного магазина
    """
    def get(self, request, shop_id, *args, **kwargs):
        try:
            shop = Shop.objects.get(id=shop_id, state=True)
            shop_serializer = ShopSerializer(shop)
            return JsonResponse({'Status': True, 'Shop': shop_serializer.data})
        except Shop.DoesNotExist:
            return JsonResponse({'Status': False, 'Errors': 'Магазин не найден'})


class CategoryListView(APIView):
    """
    Получение списка всех категорий
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer(queryset, many=True)


class CategoryDetailView(APIView):
    """
    Получение данных конкретной категории
    """
    def get(self, request, category_id, *args, **kwargs):
        try:
            category = Category.objects.get(id=category_id)
            category_serializer = CategorySerializer(category)
            return JsonResponse({'Status': True, 'Category': category_serializer.data})
        except Category.DoesNotExist:
            return JsonResponse({'Status': False, 'Errors': 'Категория не найдена'})


class ProductListView(APIView):
    """
    Получение списка всех продуктов
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer(queryset, many=True)


class ProductDetailView(APIView):
    """
    Получение данных конкретного продукта
    """
    def get(self, request, product_id, *args, **kwargs):
        try:
            product = Product.objects.get(id=product_id)
            product_serializer = ProductSerializer(product)
            return JsonResponse({'Status': True, 'Product': product_serializer.data})
        except Product.DoesNotExist:
            return JsonResponse({'Status': False, 'Errors': 'Продукт не найден'})


class ProductInfoView(APIView):
    """
    Получение информации о продукте в конкретном магазине
    """
    def get(self, request, *args, **kwargs):
        # Начинаем с базового запроса, чтобы фильтровать только активные магазины
        query = Q(shop__state=True)

        # Получаем параметры запроса
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        # Если передан shop_id, добавляем его в запрос
        if shop_id:
            query = query & Q(shop_id=shop_id)

        # Если передан category_id, добавляем его в запрос
        if category_id:
            query = query & Q(product__category_id=category_id)

        # Получаем queryset с фильтрацией и оптимизацией запросов
        queryset = (ProductInfo.objects.filter(query).
                    select_related('shop', 'product__category').    # Для получения связанных объектов
                    prefetch_related('product_parameters__parameter').    # Для многих параметров
                    distinct())    # Убираем дубликаты

        # Сериализуем queryset
        serializer = ProductInfoSerializer(queryset, many=True)
        return JsonResponse({'Status': True, 'ProductInfos': serializer.data})


class BasketView(APIView):
    """
    Просмотр и управление корзиной пользователя
    """
    def get(self, request, *args, **kwargs):
        """ Получение текущей корзины пользователя """
        if request.user.is_authenticated:
            basket = (Order.objects.filter(user_id=request.user.id, status='basket').
                      prefetch_related('ordered_items__product_info__product__category',
                                       'ordered_items__product_info__product_parameters__parameter').
                      annotate(total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).
                      distinct())

            serializer = OrderSerializer(basket, many=True)
            return Response(serializer.data)
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'}, status=403)


    def post(self, request, *args, **kwargs):
        """ Добавление товара в корзину пользователя """
        if request.user.is_authenticated:
            items_string = request.data.get('items')
            if items_string:
                try:
                    items_dict = load_json(items_string)
                except ValueError:
                    return JsonResponse({'Status': False, 'Errors': 'Неверный формат данных'})
                else:
                    basket, _ = Order.objects.get_or_create(user_id=request.user.id, status='basket')
                    objects_created = 0
                    for order_item in items_dict:
                        order_item.update({'order': basket.id})
                        serializer = OrderItemSerializer(data=order_item)
                        if serializer.is_valid():
                            try:
                                serializer.save()
                            except IntegrityError as error:
                                return JsonResponse({'Status': False, 'Errors': str(error)})
                            else:
                                objects_created += 1
                        else:
                            return JsonResponse({'Status': False, 'Errors': serializer.errors})
                    return JsonResponse({'Status': True, 'Message': 'Товар добавлен в корзину'})
            return JsonResponse({'Status': False, 'Errors': 'Нет данных для добавления'})
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'}, status=403)


    def delete(self, request, *args, **kwargs):
        """ Удаление товара из корзины пользователя """
        if request.user.is_authenticated:
            items_string = request.data.get('items')
            if items_string:
                items_list = items_string.split(',')
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, status='basket')
                query = Q()
                objects_deleted = False
                for order_item_id in items_list:
                    if order_item_id.isdigit():
                        query = query | Q(id=int(order_item_id), order_id=basket.id)
                        objects_deleted = True

                if objects_deleted:
                    deleted_count = OrderItem.objects.filter(query).delete()[0]
                    return JsonResponse({'Status': True, 'Message': f'Удалено позиций: {deleted_count}'})
                else:
                    return JsonResponse({'Status': False, 'Errors': 'Нет корректных ID для удаления'})
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'}, status=403)


    def put(self, request, *args, **kwargs):
        """ Изменение количества товара в корзине пользователя """
        if request.user.is_authenticated:
            items_string = request.data.get('items')
            if items_string:
                try:
                    items_dict = load_json(items_string)
                except ValueError:
                    return JsonResponse({'Status': False, 'Errors': 'Неверный формат данных'})
                else:
                    basket, _ = Order.objects.get_or_create(user_id=request.user.id, status='basket')
                    objects_updated = 0
                    for order_item in items_dict:
                        if type(order_item['id']) == int and type(order_item['quantity']) == int:
                            objects_updated += (OrderItem.objects.filter(id=order_item['id'], order_id=basket.id).
                                                update(quantity=order_item['quantity']))
                    return JsonResponse({'Status': True, 'Message': 'Корзина успешно обновлена'})
            return JsonResponse({'Status': False, 'Errors': 'Нет данных для обновления'})
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'}, status=403)


class PartnerUpdateView(APIView):
    """
    Обновление информации партнёра
    """
    def post(self, request, *args, **kwargs):
        """ Обновление информации """
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Errors': 'Пользователь не является партнёром'}, status=403)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({'Status': False, 'Errors': f'Некорректный URL: {e}'})
            else:
                steam = get(url).content
                data = load_yaml(steam, Loader=Loader)
                shop, _ = Shop.objects.get_or_create(user_id=request.user.id, name=data['shop'])
                for category in data['categories']:
                    category_obj, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                    category_obj.shops.add(shop.id)
                    category_obj.save()
                ProductInfo.objects.filter(shop_id=shop.id).delete()
                for item in data['goods']:
                    product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])
                    product_info = ProductInfo.objects.create(product_id=product.id,
                                                              external_id=item['id'],
                                                              model=item['model'],
                                                              price=item['price'],
                                                              price_rrc=item['price_rrc'],
                                                              quantity=item['quantity'],
                                                              shop_id=shop.id,)
                    for parameter_name, parameter_value in item['parameters'].items():
                        parameter_obj, _ = Parameter.objects.get_or_create(name=parameter_name)
                        ProductParameter.objects.create(product_info_id=product_info.id,
                                                        parameter_id=parameter_obj.id,
                                                        value=parameter_value)
                return JsonResponse({'Status': True, 'Message': 'Информация успешно обновлена'})
        return JsonResponse({'Status': False, 'Errors': 'URL не передан'})


class PartnerStateView(APIView):
    """
    Изменение состояния партнёра (активен/неактивен)
    """
    def get(self, request, *args, **kwargs):
        """ Получение состояния партнёра """
        if request.user.is_authenticated:
            if request.user.type != 'shop':
                return JsonResponse({'Status': False, 'Errors': 'Пользователь не является партнёром'}, status=403)

            shop = request.user.shop
            serialiser = ShopSerializer(shop)
            return Response(serialiser.data)
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'}, status=403)


    def post(self, request, *args, **kwargs):
        """ Изменение состояния партнёра """
        if request.user.is_authenticated:
            if request.user.type != 'shop':
                return JsonResponse({'Status': False, 'Errors': 'Пользователь не является партнёром'}, status=403)
            state = request.data.get('state')
            if state is not None:
                parsed_state = parse_boolean_state(state)
                if parsed_state is not None:
                    Shop.objects.filter(user_id=request.user.id).update(state=parsed_state)
                    return JsonResponse({'Status': True, 'Message': 'Состояние успешно изменено'})
                return JsonResponse({'Status': False, 'Errors': 'Некорректное значение состояния'})
            return JsonResponse({'Status': False, 'Errors': 'Состояние не передано'})
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'}, status=403)


class PartnerOrdersView(APIView):
    """
    Просмотр заказов партнёра
    """
    def get(self, request, *args, **kwargs):
        """ Получение заказов партнёра """
        if request.user.is_authenticated:
            if request.user.type != 'shop':
                return JsonResponse({'Status': False, 'Errors': 'Пользователь не является партнёром'}, status=403)

            orders = (Order.objects.filter(ordered_items__product_info__shop__user_id=request.user.id).
                      exclude(status='basket').
                      prefetch_related('ordered_items__product_info__product__category',
                                       'ordered_items__product_info__product_parameters__parameter').
                      annotate(total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).
                      distinct())

            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data)
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'}, status=403)


class ContactView(APIView):
    """
    Просмотр и управление контактами пользователя
    """
    def get(self, request, *args, **kwargs):
        """ Получение контактов пользователя """
        if request.user.is_authenticated:
            contacts = Contact.objects.filter(user_id=request.user.id)
            serializer = ContactSerializer(contacts, many=True)
            return Response(serializer.data)
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'}, status=403)


    def post(self, request, *args, **kwargs):
        """ Добавление контакта пользователя """
        if request.user.is_authenticated:
            if {'city', 'street', 'house', 'phone'}.issubset(request.data):
                request.data._mutable = True
                request.data.update({'user': request.user.id})
                serializer = ContactSerializer(data=request.data)
                if serializer.is_valid():
                    serializer.save(user_id=request.user.id)
                    return JsonResponse({'Status': True, 'Message': 'Контакт успешно добавлен'})
                else:
                    return JsonResponse({'Status': False, 'Errors': serializer.errors})

            if not {'city', 'street', 'house', 'phone'}.issubset(request.data):
                return JsonResponse({'Status': False, 'Errors': 'Не все обязательные поля заполнены'})

        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'}, status=403)


    def delete(self, request, *args, **kwargs):
        """ Удаление контакта пользователя """
        if request.user.is_authenticated:
            items_string = request.data.get('items')
            if items_string:
                items_list = items_string.split(',')
                query = Q()
                objects_deleted = False
                for contact_id in items_list:
                    if contact_id.isdigit():
                        query = query | Q(id=int(contact_id), user_id=request.user.id)
                        objects_deleted = True

                if objects_deleted:
                    deleted_count = Contact.objects.filter(query).delete()[0]
                    return JsonResponse({'Status': True, 'Message': f'Удалено контактов: {deleted_count}'})
            return JsonResponse({'Status': False, 'Errors': 'Нет корректных ID для удаления'})
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'}, status=403)

    def put(self, request, *args, **kwargs):
        """ Изменение контакта пользователя """
        if request.user.is_authenticated:
            contact_id = request.data.get('id')
            if contact_id and contact_id.isdigit():
                contact = Contact.objects.filter(id=int(contact_id), user_id=request.user.id).first()
                if contact:
                    serializer = ContactSerializer(contact, data=request.data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        return JsonResponse({'Status': True, 'Message': 'Контакт успешно обновлен'})
                    else:
                        return JsonResponse({'Status': False, 'Errors': serializer.errors})
                else:
                    return JsonResponse({'Status': False, 'Errors': 'Контакт не найден'})
            return JsonResponse({'Status': False, 'Errors': 'Некорректный или отсутствующий ID контакта'})
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'}, status=403)


class OrderView(APIView):
    """
    Просмотр и управление заказами пользователя
    """
    def get(self, request, *args, **kwargs):
        """ Получение заказов пользователя """
        if request.user.is_authenticated:
            orders = (Order.objects.filter(user_id=request.user.id).
                      exclude(status='basket').
                      prefetch_related('ordered_items__product_info__product__category',
                                       'ordered_items__product_info__product_parameters__parameter').
                      select_related('contact').
                      annotate(total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).
                      distinct())

            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data)
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'}, status=403)


    def post(self, request, *args, **kwargs):
        """ Оформление заказа пользователя """
        if request.user.is_authenticated:
            contact_id = request.data.get('contact_id')
            if contact_id and contact_id.isdigit():
                try:
                    basket = Order.objects.filter(user_id=request.user.id, status='basket').first()
                    if basket:
                        contact = Contact.objects.filter(id=int(contact_id), user_id=request.user.id).first()
                        if contact:
                            basket.contact = contact
                            basket.status = 'new'
                            basket.save()
                            new_order.send(sendler=self.__class__, user_id=request.user.id, order_id=basket.id)
                            return JsonResponse({'Status': True, 'Message': 'Заказ успешно оформлен'})
                        else:
                            return JsonResponse({'Status': False, 'Errors': 'Контакт не найден'})
                    else:
                        return JsonResponse({'Status': False, 'Errors': 'Корзина пуста'})
                except IntegrityError as error:
                    print(error)
                    return JsonResponse({'Status': False, 'Errors': 'Ошибка при оформлении заказа'})
            return JsonResponse({'Status': False, 'Errors': 'Некорректный или отсутствующий ID контакта'})
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'}, status=403)


