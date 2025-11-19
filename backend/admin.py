from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path, reverse
from backend.tasks import do_import
from .models import (
    User, Shop, Category, Product, ProductInfo,
    Parameter, ProductParameter, Contact, Order, OrderItem
)


"""
Inline для отображения связанных объектов в админке.
"""
class ProductParameterInline(admin.TabularInline):
    model = ProductParameter
    extra = 0


class ProductInfoInline(admin.TabularInline):
    model = ProductInfo
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


"""
Декоратор для регистрации каждой модели в панели администратора.
"""
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "username", "first_name", "last_name", "type", "is_active", "is_staff")
    search_fields = ("email", "username", "first_name", "last_name")
    list_filter = ("type", "is_active", "is_staff")


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "state", "user")
    search_fields = ("name",)
    list_filter = ("state",)
    actions = ["run_import_task"]

    def run_import_task(self, request, queryset):
        do_import.delay()
        self.message_user(request, "Импорт данных запущен в фоне (Celery).", level=messages.SUCCESS)

    run_import_task.short_description = "Запустить импорт данных (Celery)"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import/", self.admin_site.admin_view(self.import_view), name="backend_shop_import"),
        ]
        return custom_urls + urls

    def import_view(self, request):
        do_import.delay()
        self.message_user(request, "Импорт данных запущен в фоне (Celery).", level=messages.SUCCESS)
        return redirect(reverse("admin:backend_shop_changelist"))


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category")
    search_fields = ("name",)
    list_filter = ("category",)
    inlines = [ProductInfoInline]


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "shop", "model", "external_id", "quantity", "price", "price_rrc")
    search_fields = ("product__name", "shop__name", "model", "external_id")
    list_filter = ("shop", "product__category")
    inlines = [ProductParameterInline]


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    list_display = ("id", "product_info", "parameter", "value")
    search_fields = ("product_info__product__name", "parameter__name", "value")


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "city", "street", "house", "phone")
    search_fields = ("user__email", "city", "street", "phone")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "contact", "created_at", "updated_at")
    search_fields = ("user__email",)
    list_filter = ("status", "created_at")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product_info", "quantity")
    search_fields = ("order__id", "product_info__product__name")
