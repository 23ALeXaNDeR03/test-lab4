import unittest
from app.eshop import Product, ShoppingCart, Order
from unittest.mock import MagicMock

class TestProduct(unittest.TestCase):
    def setUp(self):
        self.product = Product(name='Test', price=123.45, available_amount=21)
        self.cart = ShoppingCart()
        self.product1 = Product(name='Product1', price=10.0, available_amount=100)
        self.product2 = Product(name='Product2', price=20.0, available_amount=50)

    def tearDown(self):
        self.cart.remove_product(self.product)

    # Original tests
    def test_mock_add_product(self):
        self.product.is_available = MagicMock()
        self.cart.add_product(self.product, 12345)
        self.product.is_available.assert_called_with(12345)
        self.product.is_available.reset_mock()

    def test_add_available_amount(self):
        self.cart.add_product(self.product, 11)
        self.assertEqual(self.cart.contains_product(self.product), True, 'Продукт успішно доданий до корзини')

    def test_add_non_available_amount(self):
        with self.assertRaises(ValueError):
            self.cart.add_product(self.product, 22)
        self.assertEqual(self.cart.contains_product(self.product), False, 'Продукт не доданий до корзини')

    # Additional tests
    def test_product_initialization(self):
        self.assertEqual(self.product.name, 'Test', 'Назва продукту ініціалізована неправильно')
        self.assertEqual(self.product.price, 123.45, 'Ціна продукту ініціалізована неправильно')
        self.assertEqual(self.product.available_amount, 21, 'Доступна кількість продукту ініціалізована неправильно')

    def test_product_is_available(self):
        self.assertTrue(self.product.is_available(20), 'Продукт має бути доступним для 20 одиниць')
        self.assertTrue(self.product.is_available(21), 'Продукт має бути доступним для 21 одиниці')
        self.assertFalse(self.product.is_available(22), 'Продукт не має бути доступним для 22 одиниць')

    def test_product_buy(self):
        initial_amount = self.product.available_amount
        self.product.buy(10)
        self.assertEqual(self.product.available_amount, initial_amount - 10, 'Кількість продукту після покупки зменшена неправильно')

    def test_product_eq(self):
        product2 = Product(name='Test', price=100, available_amount=10)
        self.assertEqual(self.product, product2, 'Продукти з однаковою назвою мають бути рівними')
        product3 = Product(name='Other', price=123.45, available_amount=21)
        self.assertNotEqual(self.product, product3, 'Продукти з різними назвами не мають бути рівними')

    def test_product_str(self):
        self.assertEqual(str(self.product), 'Test', 'Строкове представлення продукту повертає неправильне значення')

    def test_shopping_cart_initialization(self):
        self.assertEqual(self.cart.products, {}, 'Кошик має ініціалізуватися порожнім')

    def test_shopping_cart_calculate_total_empty(self):
        self.assertEqual(self.cart.calculate_total(), 0, 'Загальна сума порожнього кошика має бути 0')

    def test_shopping_cart_calculate_total_with_products(self):
        self.cart.add_product(self.product1, 2)
        self.cart.add_product(self.product2, 3)
        total = 2 * 10.0 + 3 * 20.0
        self.assertEqual(self.cart.calculate_total(), total, 'Загальна сума кошика розрахована неправильно')

    def test_shopping_cart_remove_product_existing(self):
        self.cart.add_product(self.product1, 1)
        self.assertTrue(self.cart.contains_product(self.product1), 'Продукт має бути в кошику після додавання')
        self.cart.remove_product(self.product1)
        self.assertFalse(self.cart.contains_product(self.product1), 'Продукт не видалений з кошика')

    def test_shopping_cart_remove_product_non_existing(self):
        self.cart.remove_product(self.product1)  # Should not raise an error
        self.assertFalse(self.cart.contains_product(self.product1), 'Продукт не має бути в кошику після видалення')

if __name__ == '__main__':
    unittest.main()