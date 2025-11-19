import os
import yaml
from django.conf import settings
from django.db import transaction
from backend.models import Shop, Category, ProductInfo, Parameter, ProductParameter, Product


def import_data_from_yaml(file_path: str | None = None) -> dict:
    """'
    Импорт данных из файла 'data/shop1.yaml'
    Для каждой записи пытается выполнить update_or_create по одному из уникальных полей модели.
    Возвращает статистику импорта.
    """
    if file_path is None:
        file_path = os.path.join(settings.BASE_DIR, 'data', 'shop1.yaml')

    with open(file_path, 'r', encoding='utf-8') as stream:
        data = yaml.safe_load(stream)

    stats = {
        'shops_created': 0,
        'categories_created': 0,
        'products_created': 0,
        'product_infos_created': 0,
        'parameters_created': 0,
        'product_parameters_created': 0,
    }

    with transaction.atomic():
        # Импортируем магазин
        shop_data = data.get('shop')  # Получаем данные магазина из YAML
        if isinstance(shop_data, dict):
            shop, created = Shop.objects.update_or_create(
                id=shop_data.get('id'),
                defaults={
                    'name': shop_data['name'],
                    'url': shop_data.get('url')
                }
            )
            if created:
                stats['shops_created'] += 1
        elif isinstance(shop_data, str) and shop_data.strip():
            # В YAML магазин задан одной строкой (названием)
            shop, created = Shop.objects.get_or_create(name=shop_data.strip())
            if created:
                stats['shops_created'] += 1
        else:
            # Нет валидных данных магазина — дальнейшие операции потребуют shop
            raise ValueError("'shop' в YAML должен быть словарем с полями или строкой с названием магазина")

        # Импортируем категории
        for category_data in data.get('categories', []):
            category, created = Category.objects.update_or_create(
                id=category_data.get('id'),
                defaults={'name': category_data['name']}
            )
            if created:
                stats['categories_created'] += 1
            if shop:
                shop.categories.add(category)  # Добавляем связь магазина с категорией

        # Импортируем товары
        for goods_data in data.get('goods', []):
            product, created = Product.objects.update_or_create(
                id=goods_data.get('id'),
                defaults={
                    'name': goods_data['name'],
                    'category': Category.objects.get(id=goods_data['category'])
                }
            )

            if created:
                stats['products_created'] += 1

            # Добавление связи магазина с товаром (если такая M2M связь существует)
            if shop and hasattr(shop, 'products'):
                shop.products.add(product)

            # В ProductInfo уникальность по (product, shop, external_id)
            product_info, created = ProductInfo.objects.update_or_create(
                product=product,
                shop=shop,
                external_id=goods_data['id'],
                defaults={
                    'model': goods_data.get('model', ''),
                    'price': goods_data['price'],
                    'price_rrc': goods_data['price_rrc'],
                    'quantity': goods_data['quantity'],
                }
            )
            if created:
                stats['product_infos_created'] += 1


            # Импортируем параметры товара
            for param_name, param_value in goods_data.get('parameters', {}).items():
                parameter, created = Parameter.objects.update_or_create(
                    name=param_name
                )
                if created:
                    stats['parameters_created'] += 1
                product_parameter, created = ProductParameter.objects.update_or_create(
                    product_info=product_info,
                    parameter=parameter,
                    defaults={'value': param_value}
                )
                if created:
                    stats['product_parameters_created'] += 1


    return stats