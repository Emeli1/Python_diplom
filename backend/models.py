from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

STATE_CHOICES = (
    ('basket', 'Статус корзины'),
    ('new', 'Новый'),
    ('confirmed', 'Подтвержден'),
    ('assembled', 'Собран'),
    ('shipped', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен'),
)

USER_TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),
)

class UserManager(BaseUserManager):
    """
    Класс менеджера для пользователей
    """
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Создание пользователя

        :param email:
        :param password:
        :param extra_fields:
        :return:
        """
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """
        Создание пользователя

        :param email:
        :param password:
        :param extra_fields:
        :return:
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """
        Создание суперпользователя

        :param email:
        :param password:
        :param extra_fields:
        :return:
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')

        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
    """
    Класс пользователя
    """
    REQUIRED_FIELDS = []
    objects = UserManager()
    USERNAME_FIELD = 'email'
    email = models.EmailField(_('email_adress'), unique=True)
    company = models.CharField(verbose_name='Компания', max_length=100, blank=True)
    position = models.CharField(verbose_name='Должность', max_length=100, blank=True)
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_(
            'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
        ),
        validators=[username_validator],
        error_messages={
            'unique': _('A user with that username already exists.'),
        },
    )
    is_active = models.BooleanField(
        _('active'),
        default=False,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    type = models.CharField(verbose_name='Тип пользователя', choices=USER_TYPE_CHOICES, default='buyer')

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Список пользователей'
        ordering = ('email',)


class Shop(models.Model):
    objects = models.manager.Manager()
    name = models.CharField(max_length=40, verbose_name='Название')
    url = models.URLField(verbose_name='Ссылка', null=True, blank=True)
    user = models.OneToOneField(User,
                                verbose_name='Пользователь',
                                blank=True,
                                null=True,
                                on_delete=models.CASCADE)
    state = models.BooleanField(verbose_name='Статус получения заказов', default=True)

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Список магазинов'
        ordering = ('-name',)


    def __str__(self):
        return self.name


class Category(models.Model):
    objects = models.manager.Manager()
    name = models.CharField(max_length=40, verbose_name='Название')
    shops = models.ManyToManyField(Shop, verbose_name='Магазины', related_name='categories', blank=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Список категорий'
        ordering = ('-name',)

    def __str__(self):
        return self.name


class Product(models.Model):
    objects = models.manager.Manager()
    name = models.CharField(max_length=80, verbose_name='Название')
    category = models.ForeignKey(Category,
                                 verbose_name='Категория',
                                 related_name='products',
                                 on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Список товаров'
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    objects = models.manager.Manager()
    model = models.CharField(max_length=80, verbose_name='Модель', blank=True)
    external_id = models.PositiveIntegerField(verbose_name='Внешний ИД')
    product = models.ForeignKey(Product,
                                verbose_name='Товар',
                                related_name='product_infos',
                                on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop,
                             verbose_name='Магазин',
                             related_name='product_infos',
                             blank=True,
                             on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    price_rrc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Рекомендуемая розничная цена')

    class Meta:
        verbose_name = 'Информация о товаре'
        verbose_name_plural = 'Список информации о товарах'
        constraints = [
            models.UniqueConstraint(fields=['product', 'shop', 'external_id'], name='unique_product_info')
        ]

    def __str__(self):
        return f'{self.product.name} - {self.shop.name}'

class Parameter(models.Model):
    objects = models.manager.Manager()
    name = models.CharField(max_length=40, verbose_name='Название')

    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = 'Список параметров'
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    objects = models.manager.Manager()
    product_info = models.ForeignKey(ProductInfo,
                                     verbose_name='Информация о товаре',
                                     related_name='product_parameters',
                                     blank=True,
                                     on_delete=models.CASCADE)
    parameter = models.ForeignKey('Parameter',
                                  verbose_name='Параметр',
                                  related_name='product_parameters',
                                  on_delete=models.CASCADE)
    value = models.CharField(max_length=100, verbose_name='Значение')

    class Meta:
        verbose_name = 'Параметр товара'
        verbose_name_plural = 'Список параметров товаров'
        constraints = [
            models.UniqueConstraint(fields=['product_info', 'parameter'], name='unique_product_parameter')
        ]

    def __str__(self):
        return f'{self.product_info.product.name} - {self.parameter.name}: {self.value}'


class Contact(models.Model):
    objects = models.manager.Manager()
    user = models.ForeignKey(User,
                             verbose_name='Пользователь',
                             related_name='contacts',
                             on_delete=models.CASCADE)
    city = models.CharField(max_length=50, verbose_name='Город')
    street = models.CharField(max_length=100, verbose_name='Улица')
    house = models.CharField(max_length=10, verbose_name='Дом')
    structure = models.CharField(max_length=10, verbose_name='Корпус', blank=True)
    building = models.CharField(max_length=10, verbose_name='Строение', blank=True)
    apartment = models.CharField(max_length=10, verbose_name='Квартира', blank=True)
    phone = models.CharField(max_length=20, verbose_name='Телефон')

    class Meta:
        verbose_name = 'Контакт'
        verbose_name_plural = 'Список контактов'

    def __str__(self):
        return f'{self.user.email} - {self.phone}'


class Order(models.Model):
    objects = models.manager.Manager()
    user = models.ForeignKey(User,
                             verbose_name='Пользователь',
                             related_name='orders',
                             blank=True,
                             on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    state = models.CharField(max_length=20,
                             choices=STATE_CHOICES,
                             verbose_name='Статус заказа')
    contact = models.ForeignKey(Contact,
                                verbose_name='Контакт',
                                related_name='orders',
                                blank=True,
                                null=True,
                                on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Список заказов'
        ordering = ('-created_at',)

    def __str__(self):
        return str(self.created_at)


class OrderItem(models.Model):
    objects = models.manager.Manager()
    order = models.ForeignKey(Order,
                              verbose_name='Заказ',
                              related_name='ordered_items',
                              blank=True,
                              on_delete=models.CASCADE)
    product_info = models.ForeignKey(ProductInfo,
                                     verbose_name='Информация о товаре',
                                     related_name='order_items',
                                     blank=True,
                                     on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name='Количество')

    class Meta:
        verbose_name = 'Товар заказа'
        verbose_name_plural = 'Список товаров заказа'
        constraints = [
            models.UniqueConstraint(fields=['order_id', 'product_info'], name='unique_order_item')
        ]

    def __str__(self):
        return f'Заказ {self.order.id} - {self.product_info.product.name}'


class ConfirmEmailToken(models.Model):
    """
    Класс токена для подтверждения email
    """
    objects = models.manager.Manager()

    @staticmethod
    def generate_key():
        import hashlib
        import random
        import time

        salt = hashlib.sha1(str(random.random()).encode('utf8')).hexdigest()[:5]
        return hashlib.sha1((salt + str(time.time())).encode('utf8')).hexdigest()

    user = models.ForeignKey(User,
                             verbose_name='Пользователь',
                             related_name='email_confirm_tokens',
                             blank=True,
                             on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name='Дата создания')
    key = models.CharField(max_length=64,
                           verbose_name='Ключ',
                           db_index=True,
                           unique=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Токен подтверждения email'
        verbose_name_plural = 'Список токенов подтверждения email'
        ordering = ('-created_at',)

    def __str__(self):
        return f'Token for {self.user.email} - {self.key}'
