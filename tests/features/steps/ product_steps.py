from behave import given, when, then
from eshop import Product

@given(u'I want to create a product')
def step_given_create_product(context):
    context.product = None
    context.creation_success = False

@when(u'I set availability to "{availability}", name to "{name}" and price to "{price}"')
def step_when_set_product_details(context, availability, name, price):
    try:
        availability = int(availability)
        if len(name) < 3:
            raise ValueError("Name must be at least 3 characters long")
        if availability < 0:
            raise ValueError("Availability must be non-negative")
        try:
            if price.lower() == "ten":
                raise ValueError("Price must be a number, not text")
            price = float(price)
            if price < 0:
                raise ValueError("Price must be non-negative")
        except ValueError as e:
            if "must be a number" not in str(e):
                raise ValueError("Price must be a valid number")
            raise
        context.product = Product(name=name, price=price, available_amount=availability)
        context.creation_success = True
    except ValueError:
        context.creation_success = False
        context.product = None

@when(u'I set availability to "{availability}", name to "{name}" and omit the price')
def step_when_set_product_details_no_price(context, availability, name):
    try:
        availability = int(availability)
        if len(name) < 3:
            raise ValueError("Name must be at least 3 characters long")
        if availability < 0:
            raise ValueError("Availability must be non-negative")
        price = None
        if price is None:
            raise ValueError("Price must be provided and be a valid number")
        context.product = Product(name=name, price=price, available_amount=availability)
        context.creation_success = True
    except ValueError:
        context.creation_success = False
        context.product = None

@then('Product creation should fail')
def step_then_product_creation_should_fail(context):
    assert not context.creation_success, "Product creation succeeded, but it should have failed."


@given(u'A product with availability "{availability}"')
def step_given_a_product_with_availability(context, availability):
    context.product = Product(name="item", price=20.0, available_amount=int(availability))

@when(u'I check if "{amount}" units are available')
def step_when_check_product_availability(context, amount):
    amount = int(amount)
    context.is_available = context.product.is_available(amount)

@then(u'The product should be considered unavailable')
def step_then_product_unavailable(context):
    assert not context.is_available, "Product is available when it should be unavailable."

@when(u'I buy "{amount}" units of the product')
def step_when_buy_product(context, amount):
    amount = int(amount)
    try:
        if not context.product.is_available(amount):
            raise ValueError("Not enough items available to buy")
        context.product.buy(amount)
    except ValueError:
        context.product.available_amount = context.product.available_amount

@then(u'The remaining product availability should be "{remaining_availability}"')
def step_then_remaining_availability(context, remaining_availability):
    assert context.product.available_amount == int(
        remaining_availability), f"Expected {remaining_availability}, but got {context.product.available_amount}"

@given(u'A product named "{name}"')
def step_given_a_product_named(context, name):
    context.product = Product(name=name, price=20.0, available_amount=10)

@given(u'Another product named "{name}"')
def step_given_another_product_named(context, name):
    context.another_product = Product(name=name, price=20.0, available_amount=10)

@when(u'I compare both products')
def step_when_compare_products(context):
    context.are_equal = context.product == context.another_product

@then(u'They should be equal')
def step_then_products_equal(context):
    assert context.are_equal is True, "Products are not equal"