import uuid
import pytest
import boto3
from app.eshop import Product, ShoppingCart, Order
import random
from services.service import ShippingService
from services.repository import ShippingRepository
from services.publisher import ShippingPublisher
from datetime import datetime, timedelta, timezone
from services.config import AWS_ENDPOINT_URL, AWS_REGION, SHIPPING_QUEUE, SHIPPING_TABLE_NAME

@pytest.mark.parametrize("order_id, shipping_id", [
    ("order_1", "shipping_1"),
    ("order_i2hur2937r9", "shipping_1!!!!"),
    (8662354, 123456),
    (str(uuid.uuid4()), str(uuid.uuid4()))
])

def test_place_order_with_mocked_repo(mocker, order_id, shipping_id):
    mock_repo = mocker.Mock()
    mock_publisher = mocker.Mock()
    shipping_service = ShippingService(mock_repo, mock_publisher)
    mock_repo.create_shipping.return_value = shipping_id
    cart = ShoppingCart()
    cart.add_product(Product(
        available_amount=10,
        name='Product',
        price=random.random() * 10000),
        amount=9
    )
    order = Order(cart, shipping_service, order_id)
    due_date = datetime.now(timezone.utc) + timedelta(seconds=3)
    actual_shipping_id = order.place_order(
        ShippingService.list_available_shipping_type()[0],
        due_date=due_date
    )
    assert actual_shipping_id == shipping_id, "Actual shipping id must be equal to mock return value"

    mock_repo.create_shipping.assert_called_with(ShippingService.list_available_shipping_type()[0], ["Product"],
                                                 order_id, shipping_service.SHIPPING_CREATED, due_date)

    mock_publisher.send_new_shipping.assert_called_with(shipping_id)

def test_place_order_with_unavailable_shipping_type_fails(dynamo_resource):
    shipping_service = ShippingService(ShippingRepository(), ShippingPublisher())
    cart = ShoppingCart()
    cart.add_product(Product(
        available_amount=10,
        name='Product',
        price=random.random() * 10000),
        amount=9
    )
    order = Order(cart, shipping_service)
    shipping_id = None
    with pytest.raises(ValueError) as excinfo:
        shipping_id = order.place_order(
            "Новий тип доставки",
            due_date=datetime.now(timezone.utc) + timedelta(seconds=3)
        )
    assert shipping_id is None, "Shipping id must not be assigned"
    assert "Shipping type is not available" in str(excinfo.value)

def test_when_place_order_then_shipping_in_queue(dynamo_resource):
    clear_sqs_queue()
    shipping_service = ShippingService(ShippingRepository(), ShippingPublisher())
    cart = ShoppingCart()
    cart.add_product(Product(
        available_amount=10,
        name='Product',
        price=random.random() * 10000),
        amount=9
    )
    order = Order(cart, shipping_service)
    shipping_id = order.place_order(
        ShippingService.list_available_shipping_type()[0],
        due_date=datetime.now(timezone.utc) + timedelta(minutes=1)
    )
    sqs_client = boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )
    queue_url = sqs_client.get_queue_url(QueueName=SHIPPING_QUEUE)["QueueUrl"]
    # Шукаємо повідомлення в черзі з кількома спробами, щоб врахувати можливі затримки
    found = False
    for _ in range(5):
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10
        )
        messages = response.get("Messages", [])
        if messages and messages[0]["Body"] == shipping_id:
            found = True
            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=messages[0]["ReceiptHandle"]
            )
            break
        elif messages:
            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=messages[0]["ReceiptHandle"]
            )
    assert found, f"Expected SQS message with shipping_id {shipping_id} not found"


# Допоміжна функція для очищення черги SQS перед тестами
def clear_sqs_queue():
    sqs_client = boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )
    queue_url = sqs_client.get_queue_url(QueueName=SHIPPING_QUEUE)["QueueUrl"]

    # Цикл для видалення всіх повідомлень із черги
    while True:
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=1
        )
        messages = response.get("Messages", [])
        if not messages:
            break
        for message in messages:
            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=message["ReceiptHandle"]
            )


# Тест 1: Перевірка створення замовлення з кількома продуктами та інтеграція з SQS і DynamoDB
def test_order_with_multiple_products(dynamo_resource):
    clear_sqs_queue()
    # Ініціалізація сервісу доставки з реальними залежностями
    real_repository = ShippingRepository()
    real_publisher = ShippingPublisher()
    shipping_service = ShippingService(real_repository, real_publisher)
    # Створюємо кошик і додаємо два продукти з різними характеристиками
    cart = ShoppingCart()
    product1 = Product(name="Product X", price=25.50, available_amount=10)
    product2 = Product(name="Product Y", price=15.75, available_amount=8)
    cart.add_product(product1, 4)
    cart.add_product(product2, 3)
    # Створюємо замовлення
    order = Order(cart=cart, shipping_service=shipping_service)
    # Викликаємо place_order для створення замовлення
    due_date = datetime.now(timezone.utc) + timedelta(minutes=5)
    shipping_id = order.place_order(
        shipping_type="Нова Пошта",
        due_date=due_date
    )
    # Робимо перевірку
    assert shipping_id is not None
    assert product1.available_amount == 6
    assert product2.available_amount == 5
    assert len(cart.products) == 0
    # Перевіряємо збереження даних у DynamoDB
    shipping_data = real_repository.get_shipping(shipping_id)
    assert shipping_data is not None
    assert shipping_data["shipping_type"] == "Нова Пошта"
    assert set(shipping_data["product_ids"].split(",")) == {"Product X", "Product Y"}
    assert shipping_data["shipping_status"] == shipping_service.SHIPPING_IN_PROGRESS
    # Ініціалізуємо клієнт SQS для перевірки повідомлення
    sqs_client = boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )
    queue_url = sqs_client.get_queue_url(QueueName=SHIPPING_QUEUE)["QueueUrl"]
    # Шукаємо повідомлення в черзі з кількома спробами
    found = False
    for _ in range(5):
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20
        )
        messages = response.get("Messages", [])
        if messages and messages[0]["Body"] == shipping_id:
            found = True
            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=messages[0]["ReceiptHandle"]
            )
            break
        elif messages:
            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=messages[0]["ReceiptHandle"]
            )
    assert found, f"Expected SQS message with shipping_id {shipping_id} not found"

# Тест 2: Перевірка замовлення з продуктом вартістю 0
def test_order_with_zero_price_product(dynamo_resource):
    # Ініціалізація сервісу доставки
    real_repository = ShippingRepository()
    real_publisher = ShippingPublisher()
    shipping_service = ShippingService(real_repository, real_publisher)
    # Створюємо кошик і додаємо продукт із нульовою ціною
    cart = ShoppingCart()
    product = Product(name="Free Product", price=0.0, available_amount=5)
    cart.add_product(product, 2)
    # Створюємо замовлення
    order = Order(cart=cart, shipping_service=shipping_service)
    # Викликаємо place_order
    due_date = datetime.now(timezone.utc) + timedelta(minutes=2)
    shipping_id = order.place_order(
        shipping_type="Укр Пошта",
        due_date=due_date
    )
    # Робимо перевірку
    assert shipping_id is not None
    assert product.available_amount == 3
    assert len(cart.products) == 0
    assert cart.calculate_total() == 0.0
    # Перевіряємо збереження даних у DynamoDB
    shipping_data = real_repository.get_shipping(shipping_id)
    assert shipping_data["product_ids"] == "Free Product"
    assert shipping_data["shipping_status"] == shipping_service.SHIPPING_IN_PROGRESS


# Тест 3: Перевірка замовлення з максимальною кількістю товару
def test_order_with_maximum_product_amount(dynamo_resource):
    clear_sqs_queue()
    real_repository = ShippingRepository()
    real_publisher = ShippingPublisher()
    shipping_service = ShippingService(real_repository, real_publisher)
    cart = ShoppingCart()
    product = Product(name="Max Product", price=100.0, available_amount=10)
    cart.add_product(product, 10)
    order = Order(cart=cart, shipping_service=shipping_service)
    due_date = datetime.now(timezone.utc) + timedelta(minutes=3)
    shipping_id = order.place_order(
        shipping_type="Meest Express",
        due_date=due_date
    )
    # Робимо перевірку
    assert shipping_id is not None
    assert product.available_amount == 0
    assert len(cart.products) == 0
    # Перевіряємо збереження даних у DynamoDB
    shipping_data = real_repository.get_shipping(shipping_id)
    assert shipping_data["product_ids"] == "Max Product"
    assert shipping_data["shipping_status"] == shipping_service.SHIPPING_IN_PROGRESS
    sqs_client = boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )
    queue_url = sqs_client.get_queue_url(QueueName=SHIPPING_QUEUE)["QueueUrl"]
    found = False
    for _ in range(5):
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20
        )
        messages = response.get("Messages", [])
        if messages and messages[0]["Body"] == shipping_id:
            found = True
            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=messages[0]["ReceiptHandle"]
            )
            break
        elif messages:
            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=messages[0]["ReceiptHandle"]
            )
    assert found, f"Expected SQS message with shipping_id {shipping_id} not found"

# Тест 4: Перевірка видалення продуктів перед оформленням замовлення
def test_order_with_multiple_product_removal(mocker, dynamo_resource):
    # Налаштування мок-сервісу доставки
    mock_shipping_service = mocker.Mock(spec=ShippingService)
    mock_shipping_service.create_shipping.return_value = "mock_shipping_id"
    # Створюємо кошик і додаємо три продукти
    cart = ShoppingCart()
    product1 = Product(name="Gadget A", price=99.99, available_amount=10)
    product2 = Product(name="Gadget B", price=49.99, available_amount=5)
    product3 = Product(name="Gadget C", price=29.99, available_amount=3)
    cart.add_product(product1, 3)
    cart.add_product(product2, 2)
    cart.add_product(product3, 1)
    # Видаляємо два продукти перед оформленням замовлення
    cart.remove_product(product2)
    cart.remove_product(product3)
    # Створюємо замовлення з мок-сервісом
    order = Order(cart=cart, shipping_service=mock_shipping_service)
    # Викликаємо place_order
    due_date = datetime.now(timezone.utc) + timedelta(minutes=5)
    shipping_id = order.place_order(
        shipping_type="Нова Пошта",
        due_date=due_date
    )
    #Робимо перевірки
    assert shipping_id == "mock_shipping_id"
    assert product1.available_amount == 7  # Только Gadget A был заказан
    assert product2.available_amount == 5  # Gadget B не затронут
    assert product3.available_amount == 3  # Gadget C не затронут
    assert len(cart.products) == 0
    # Перевіряємо, що мок-сервіс викликався з правильними аргументами
    mock_shipping_service.create_shipping.assert_called_once_with(
        "Нова Пошта",
        ["Gadget A"],
        order.order_id,
        due_date
    )

# Тест 5: Перевірка замовлення з порожнім кошиком
def test_order_with_empty_cart_real(dynamo_resource):
    clear_sqs_queue()
    real_repository = ShippingRepository()
    real_publisher = ShippingPublisher()
    shipping_service = ShippingService(real_repository, real_publisher)
    cart = ShoppingCart()
    order = Order(cart=cart, shipping_service=shipping_service)
    due_date = datetime.now(timezone.utc) + timedelta(minutes=2)
    shipping_id = order.place_order(
        shipping_type="Самовивіз",
        due_date=due_date
    )
    assert shipping_id is not None
    assert cart.products == {}
    shipping_data = real_repository.get_shipping(shipping_id)
    assert shipping_data is not None
    assert shipping_data["shipping_type"] == "Самовивіз"
    assert shipping_data["product_ids"] == ""
    assert shipping_data["shipping_status"] == shipping_service.SHIPPING_IN_PROGRESS
    sqs_client = boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )
    queue_url = sqs_client.get_queue_url(QueueName=SHIPPING_QUEUE)["QueueUrl"]
    found = False
    for _ in range(5):
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20
        )
        messages = response.get("Messages", [])
        if messages and messages[0]["Body"] == shipping_id:
            found = True
            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=messages[0]["ReceiptHandle"]
            )
            break
        elif messages:
            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=messages[0]["ReceiptHandle"]
            )
    assert found, f"Expected SQS message with shipping_id {shipping_id} not found"

# Тест 6: Перевірка замовлення з кількома однаковими продуктами
def test_order_with_duplicate_products(dynamo_resource):
    real_repository = ShippingRepository()
    real_publisher = ShippingPublisher()
    shipping_service = ShippingService(real_repository, real_publisher)

    cart = ShoppingCart()
    product = Product(name="Duplicate Product", price=30.0, available_amount=10)
    cart.add_product(product, 3)
    cart.add_product(product, 2)  # Повторне додавання перезаписує кількість
    order = Order(cart=cart, shipping_service=shipping_service)
    due_date = datetime.now(timezone.utc) + timedelta(minutes=2)
    shipping_id = order.place_order(
        shipping_type="Нова Пошта",
        due_date=due_date
    )
    assert shipping_id is not None
    assert product.available_amount == 8  # 10 - 2 (последнее добавление перезаписало 3 на 2)
    assert len(cart.products) == 0
    shipping_data = real_repository.get_shipping(shipping_id)
    assert shipping_data["product_ids"] == "Duplicate Product"
    assert shipping_data["shipping_status"] == shipping_service.SHIPPING_IN_PROGRESS

# Тест 7: Перевірка замовлення з великою кількістю різних продуктів
def test_order_with_large_number_of_products(dynamo_resource):
    clear_sqs_queue()
    real_repository = ShippingRepository()
    real_publisher = ShippingPublisher()
    shipping_service = ShippingService(real_repository, real_publisher)
    cart = ShoppingCart()
    products = []
    for i in range(5):
        product = Product(name=f"Product_{i}", price=10.0 * (i + 1), available_amount=20)
        cart.add_product(product, 2)
        products.append(product)
    order = Order(cart=cart, shipping_service=shipping_service)
    due_date = datetime.now(timezone.utc) + timedelta(minutes=5)
    shipping_id = order.place_order(
        shipping_type="Укр Пошта",
        due_date=due_date
    )
    assert shipping_id is not None
    for product in products:
        assert product.available_amount == 18
    assert len(cart.products) == 0
    shipping_data = real_repository.get_shipping(shipping_id)
    assert set(shipping_data["product_ids"].split(",")) == {f"Product_{i}" for i in range(5)}
    sqs_client = boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )
    queue_url = sqs_client.get_queue_url(QueueName=SHIPPING_QUEUE)["QueueUrl"]
    found = False
    for _ in range(5):  # Увеличиваем количество попыток до 5
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20
        )
        messages = response.get("Messages", [])
        if messages and messages[0]["Body"] == shipping_id:
            found = True
            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=messages[0]["ReceiptHandle"]
            )
            break
        elif messages:
            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=messages[0]["ReceiptHandle"]
            )
    assert found, f"Expected SQS message with shipping_id {shipping_id} not found"

# Тест 8: Перевірка замовлення з дороговартісним продуктом
def test_order_with_high_price(dynamo_resource):
    real_repository = ShippingRepository()
    real_publisher = ShippingPublisher()
    shipping_service = ShippingService(real_repository, real_publisher)
    cart = ShoppingCart()
    product = Product(name="Expensive Product", price=10000.0, available_amount=5)
    cart.add_product(product, 2)
    order = Order(cart=cart, shipping_service=shipping_service)
    due_date = datetime.now(timezone.utc) + timedelta(minutes=2)
    shipping_id = order.place_order(
        shipping_type="Meest Express",
        due_date=due_date
    )
    assert shipping_id is not None
    assert product.available_amount == 3
    assert len(cart.products) == 0
    assert cart.calculate_total() == 0.0
    shipping_data = real_repository.get_shipping(shipping_id)
    assert shipping_data["product_ids"] == "Expensive Product"
    assert shipping_data["shipping_status"] == shipping_service.SHIPPING_IN_PROGRESS

# Тест 9: Перевірка замовлення з мінімальним терміном доставки
def test_order_with_minimum_due_date(dynamo_resource):
    real_repository = ShippingRepository()
    real_publisher = ShippingPublisher()
    shipping_service = ShippingService(real_repository, real_publisher)
    cart = ShoppingCart()
    product = Product(name="Urgent Product", price=50.0, available_amount=5)
    cart.add_product(product, 2)
    order = Order(cart=cart, shipping_service=shipping_service)
    due_date = datetime.now(timezone.utc) + timedelta(seconds=1)
    shipping_id = order.place_order(
        shipping_type="Самовивіз",
        due_date=due_date
    )
    assert shipping_id is not None
    assert product.available_amount == 3
    assert len(cart.products) == 0
    shipping_data = real_repository.get_shipping(shipping_id)
    assert shipping_data["shipping_type"] == "Самовивіз"
    assert shipping_data["shipping_status"] == shipping_service.SHIPPING_IN_PROGRESS

# Тест 10: Перевірка замовлення з продуктом без назви
def test_order_with_nameless_product(mocker, dynamo_resource):
    mock_shipping_service = mocker.Mock(spec=ShippingService)
    mock_shipping_service.create_shipping.return_value = "mock_shipping_id"
    cart = ShoppingCart()
    product = Product(name="", price=10.0, available_amount=5)
    cart.add_product(product, 2)
    order = Order(cart=cart, shipping_service=mock_shipping_service)
    due_date = datetime.now(timezone.utc) + timedelta(minutes=2)
    shipping_id = order.place_order(
        shipping_type="Нова Пошта",
        due_date=due_date
    )
    assert shipping_id == "mock_shipping_id"
    assert product.available_amount == 3
    assert len(cart.products) == 0
    mock_shipping_service.create_shipping.assert_called_once_with(
        "Нова Пошта",
        [""],
        order.order_id,
        due_date
    )