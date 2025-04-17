Feature: Product
  We want to test that product functionality works correctly

  Scenario: Create product with negative availability
    Given I want to create a product
    When I set availability to "-5", name to "item" and price to "20"
    Then Product creation should fail

  Scenario: Create product with negative price
    Given I want to create a product
    When I set availability to "10", name to "item" and price to "-1"
    Then Product creation should fail

  Scenario: Create product with name shorter than 3 characters
    Given I want to create a product
    When I set availability to "5", name to "ok" and price to "30"
    Then Product creation should fail

  Scenario: Create product with price as text
    Given I want to create a product
    When I set availability to "7", name to "item" and price to "ten"
    Then Product creation should fail

  Scenario: Create product with missing price
    Given I want to create a product
    When I set availability to "7", name to "item" and omit the price
    Then Product creation should fail

  Scenario: Check product availability when requested amount is too high
    Given A product with availability "8"
    When I check if "10" units are available
    Then The product should be considered unavailable

  Scenario: Buy product and reduce availability
    Given A product with availability "10"
    When I buy "3" units of the product
    Then The remaining product availability should be "7"

  Scenario: Compare products by name
    Given A product named "Gadget"
    And Another product named "Gadget"
    When I compare both products
    Then They should be equal
