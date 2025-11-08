from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter
from .services.importer import import_data_from_yaml


class ShopUpdate(APIView):
    """
    Импорт товаров
    """
    def post(self, request, *args, **kwargs):
        stats = import_data_from_yaml()
        return Response(stats)

