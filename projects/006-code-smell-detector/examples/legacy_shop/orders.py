"""A deliberately smelly order module used to demo the detector."""

TAX_RATE = 0.08


def process_order(order, inventory, customer):
    """Validate, price and ship an order. Does far too much."""
    if order:
        if order.get("items"):
            for item in order["items"]:
                if item["sku"] in inventory:
                    if inventory[item["sku"]] >= item["qty"]:
                        if customer.get("active"):
                            inventory[item["sku"]] -= item["qty"]
                        else:
                            raise ValueError("inactive customer")
                    else:
                        raise ValueError("out of stock")
    subtotal = 0
    for item in order["items"]:
        subtotal += item["price"] * item["qty"]
    discount = 0
    if customer.get("tier") == "gold":
        discount = subtotal * 0.1
    elif customer.get("tier") == "silver":
        discount = subtotal * 0.05
    taxed = (subtotal - discount) * (1 + TAX_RATE)
    total = round(taxed, 2)
    lines = []
    for item in order["items"]:
        lines.append(f"{item['sku']} x{item['qty']}")
    receipt = "\n".join(lines)
    return {"total": total, "receipt": receipt}


def quote(cart, customer):
    """Price a cart without reserving stock (copy-pasted from process_order)."""
    subtotal = 0
    for line in cart:
        subtotal += line["price"] * line["qty"]
    discount = 0
    if customer.get("tier") == "gold":
        discount = subtotal * 0.1
    elif customer.get("tier") == "silver":
        discount = subtotal * 0.05
    taxed = (subtotal - discount) * (1 + TAX_RATE)
    amount = round(taxed, 2)
    return amount
