import os
import yaml
from django.conf import settings
from django.db import transaction

from backend.models import Shop, Category, ProductInfo, Parameter, ProductParameter


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
        for shop_data in data.get('shops', []):
            shop, created = Shop.objects.update_or_create(
                id=shop_data['id'],
                defaults={
                    'name': shop_data['name'],
                    'url': shop_data['url']
                }
            )
            if created:
                stats['shops_created'] += 1

            for category_data in shop_data.get('categories', []):
                category, created = Category.objects.update_or_create(
                    id=category_data['id'],
                    defaults={'name': category_data['name']}
                )
                if created:
                    stats['categories_created'] += 1
                shop.categories.add(category)

            for product_data in shop_data.get('products', []):
                product, created = ProductInfo.objects.update_or_create(
                    id=product_data['id'],
                    defaults={
                        'name': product_data['name'],
                        'category_id': product_data['category_id']
                    }
                )
                if created:
                    stats['products_created'] += 1

                for info_data in product_data.get('product_infos', []):
                    product_info, created = ProductInfo.objects.update_or_create(
                        id=info_data['id'],
                        defaults={
                            'product': product,
                            'shop': shop,
                            'model': info_data['model'],
                            'quantity': info_data['quantity'],
                            'price': info_data['price'],
                            'price_rrc': info_data['price_rrc']
                        }
                    )
                    if created:
                        stats['product_infos_created'] += 1

                    for param_data in info_data.get('parameters', []):
                        parameter, created = Parameter.objects.update_or_create(
                            name=param_data['name']
                        )
                        if created:
                            stats['parameters_created'] += 1

                        product_parameter, created = ProductParameter.objects.update_or_create(
                            product_info=product_info,
                            parameter=parameter,
                            defaults={'value': param_data['value']}
                        )
                        if created:
                            stats['product_parameters_created'] += 1
    return stats