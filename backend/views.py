from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Shop, Category, Product, ProductInfo, \
    Parameter, ProductParameter, User, ConfirmEmailToken
from .serializers import UserSerializer, ShopSerializer, \
    CategorySerializer, ProductSerializer, ProductInfoSerializer, \
    ParameterSerializer, ProductParameterSerializer
from .services.importer import import_data_from_yaml


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
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'})

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
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'})


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
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            request.user.auth_token.delete()
            return JsonResponse({'Status': True, 'Message': 'Вы успешно вышли из системы'})
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не аутентифицирован'})


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
        query = Q(shop_state=True)

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
                    select_related('shop', 'product_category').    # Для получения связанных объектов
                    prefetch_related('product_parameters__parameter').    # Для многих параметров
                    distinct())    # Убираем дубликаты

        # Сериализуем queryset
        serializer = ProductInfoSerializer(queryset, many=True)
        return JsonResponse({'Status': True, 'ProductInfos': serializer.data})

