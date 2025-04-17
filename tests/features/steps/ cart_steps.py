from behave import given, when, then
from eshop import Product, ShoppingCart

@given("The product has availability of {availability}")
def create_product_for_cart(context, availability):
    context.product = Product(name="any", price=123, available_amount=int(availability))

@given('An empty shopping cart')
def empty_cart(context):
    context.cart = ShoppingCart()

@when("I add product to the cart in amount {product_amount}")
def add_product(context, product_amount):
    try:
        context.cart.add_product(context.product, int(product_amount))
        context.add_successfully = True
    except ValueError:
        context.add_successfully = False

@then("Product is added to the cart successfully")
def add_successful(context):
    assert context.add_successfully == True

@then("Product is not added to cart successfully")
def add_failed(context):
    assert context.add_successfully == False

@then('The total cost of the cart should be {total_cost}')
def check_cart_total(context, total_cost):
    calculated_total = context.cart.calculate_total()
    assert calculated_total == float(total_cost)

@when('I remove product from cart')
def remove_product_from_cart(context):
    context.cart.remove_product(context.product)

@then('The product is no longer in the cart')
def product_not_in_cart(context):
    assert not context.cart.contains_product(context.product)

@when('I search for product in the cart')
def search_product_in_cart(context):
    context.product_found = context.cart.contains_product(context.product)

@then('The product is present in the cart')
def product_found_in_cart(context):
    assert context.product_found == True
