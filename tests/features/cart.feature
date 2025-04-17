Feature: Shopping cart
  We want to test that shopping cart functionality works correctly

  Scenario: Successful add product to cart
    Given The product has availability of 123
    And An empty shopping cart
    When I add product to the cart in amount 123
    Then Product is added to the cart successfully

  Scenario: Failed add product to cart
    Given The product has availability of 123
    And An empty shopping cart
    When I add product to the cart in amount 124
    Then Product is not added to cart successfully

  Scenario: Total cost calculation
    Given The product has availability of 200
    And An empty shopping cart
    When I add product to the cart in amount 50
    Then The total cost of the cart should be 6150

  Scenario: Remove product from cart
    Given The product has availability of 50
    And An empty shopping cart
    When I add product to the cart in amount 30
    And I remove product from cart
    Then The product is no longer in the cart

  Scenario: Check product presence in cart
    Given The product has availability of 70
    And An empty shopping cart
    When I add product to the cart in amount 30
    And I search for product in the cart
    Then The product is present in the cart
