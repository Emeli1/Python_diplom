from django.urls import path
from django_rest_passwordreset.views import (reset_password_request_token,
                                             reset_password_confirm)
from rest_framework.urls import app_name

from backend.views import (ShopUpdate, RegisterAccountView, ConfirmAccountView,
                           AccountDetailsView, LoginAccountView, LogoutAccountView,
                           ShopListView, ShopDetailView, CategoryListView,
                           CategoryDetailView, ProductListView, ProductDetailView,
                           ProductInfoView, BasketView, PartnerUpdateView,
                           PartnerStateView, PartnerOrdersView, ContactView,
                           OrderView)


app_name = 'backend'


urlpatterns = [
    path('shops/update', ShopUpdate.as_view()),
    path('user/register', RegisterAccountView.as_view(), name='user-register'),
    path('user/register/confirm', ConfirmAccountView.as_view(), name='user-register-confirm'),
    path('user/details', AccountDetailsView.as_view(), name='user-details'),
    path('user/login', LoginAccountView.as_view(), name='user-login'),
    path('user/logout', LogoutAccountView.as_view(), name='user-logout'),
    path('user/password_reset', reset_password_request_token, name='password-reset'),
    path('user/password_reset/confirm', reset_password_confirm, name='password-reset-confirm'),
    path('user/contacts', ContactView.as_view(), name='user-contacts'),
    path('shops', ShopListView.as_view(), name='shop-list'),
    path('shops/<int:pk>', ShopDetailView.as_view(), name='shop-detail'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/<int:pk>', CategoryDetailView.as_view(), name='category-detail'),
    path('products', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>', ProductDetailView.as_view(), name='product-detail'),
    path('products/info', ProductInfoView.as_view(), name='product-info'),
    path('basket', BasketView.as_view(), name='basket'),
    path('partner/update', PartnerUpdateView.as_view(), name='partner-update'),
    path('partner/state', PartnerStateView.as_view(), name='partner-state'),
    path('partner/orders', PartnerOrdersView.as_view(), name='partner-orders'),
    path('orders', OrderView.as_view(), name='orders'),
]
