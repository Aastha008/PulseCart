"""PulseCart E-Commerce Backend End-to-End Workflow Demonstration

Demonstrates:
1. Customer registration and JWT authentication
2. Product catalog browsing & stock verification
3. Order checkout with atomic stock decrement and server-side pricing
4. Idempotency replay (identical order returned, stock untouched)
5. Idempotency tampering rejection (mismatched payload rejected)
6. Order cancellation with exact single inventory restoration
7. Double-cancellation rejection
"""

import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8080/api/v1"

def http_request(endpoint, method="GET", body=None, headers=None):
    url = f"{BASE_URL}{endpoint}"
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            resp_body = response.read().decode("utf-8")
            return status, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            parsed = json.loads(err_body)
        except Exception:
            parsed = {"raw": err_body}
        return e.code, parsed


import uuid

def run_demonstration():
    print("=" * 70)
    print("PULSECART END-TO-END ORDER WORKFLOW DEMONSTRATION")
    print("=" * 70)

    run_id = uuid.uuid4().hex[:8]
    test_email = f"demo_{run_id}@pulsecart.com"

    # Step 1: Customer Registration
    print(f"\n--- Step 1: Register New Customer ({test_email}) ---")
    reg_payload = {
        "email": test_email,
        "password": "Password123!",
        "firstName": "Alice",
        "lastName": "Wonderland"
    }
    status, reg_res = http_request("/auth/register", method="POST", body=reg_payload)
    print(f"Register status: {status}")

    # Step 2: Customer Login
    print("\n--- Step 2: Authenticate and Acquire JWT ---")
    login_payload = {
        "email": test_email,
        "password": "Password123!"
    }
    status, login_res = http_request("/auth/login", method="POST", body=login_payload)
    print(f"Login status: {status}")
    token = login_res.get("token")
    assert token, "JWT token must be present"
    auth_headers = {"Authorization": f"Bearer {token}"}
    print(f"Acquired JWT Bearer Token: {token[:25]}... (length: {len(token)})")

    # Step 3: Browse Product Catalog
    print("\n--- Step 3: Browse Product Catalog ---")
    status, catalog = http_request("/products?size=5")
    print(f"Catalog query status: {status}, Total products: {catalog.get('totalElements')}")
    products = catalog.get("content", [])
    assert len(products) > 0, "Catalog must contain seeded products"
    product = products[0]
    prod_id = product["id"]
    initial_stock = product["stock"]
    print(f"Selected Product: ID={prod_id}, SKU={product['sku']}, Name='{product['name']}', Price=${product['price']}, Initial Stock={initial_stock}")

    # Step 4: Place Order with Idempotency Key
    print("\n--- Step 4: Place Order with Idempotency-Key Header ---")
    idempotency_key = f"IDEMP-DEMO-{run_id}"
    order_payload = {
        "items": [{"productId": prod_id, "quantity": 2}],
        "paymentMethod": "CREDIT_CARD"
    }
    order_headers = {**auth_headers, "Idempotency-Key": idempotency_key}
    status, order_res = http_request("/orders", method="POST", body=order_payload, headers=order_headers)
    print(f"Checkout status: {status}")
    order_id = order_res.get("id")
    order_num = order_res.get("orderNumber")
    print(f"Order Created: ID={order_id}, Number={order_num}")
    print(f"Subtotal: ${order_res.get('subtotal')}, Tax: ${order_res.get('taxAmount')}, Total: ${order_res.get('totalAmount')}")

    # Verify Stock Decremented
    status, updated_prod = http_request(f"/products/{prod_id}")
    print(f"Stock after purchase: {updated_prod['stock']} (Expected: {initial_stock - 2})")
    assert updated_prod["stock"] == initial_stock - 2, "Stock must decrement by 2"

    # Step 5: Duplicate Request (Safe Idempotent Replay)
    print("\n--- Step 5: Safe Duplicate Order Submission (Same Key) ---")
    status, replay_res = http_request("/orders", method="POST", body=order_payload, headers=order_headers)
    print(f"Replay status: {status}")
    print(f"Replay Order Number: {replay_res.get('orderNumber')} (Matches original: {replay_res.get('orderNumber') == order_num})")
    assert replay_res.get("orderNumber") == order_num, "Replayed order number must match exactly"

    # Verify Stock Was NOT Deducted Again
    status, prod_check = http_request(f"/products/{prod_id}")
    print(f"Stock after replay: {prod_check['stock']} (Strictly unchanged, overselling prevented)")
    assert prod_check["stock"] == initial_stock - 2, "Stock must not decrement again"

    # Step 6: Idempotency Key Reuse with Modified Payload (Tampering Rejection)
    print("\n--- Step 6: Reject Reusing Key with Modified Payload ---")
    tampered_payload = {
        "items": [{"productId": prod_id, "quantity": 5}],
        "paymentMethod": "PAYPAL"
    }
    status, tampered_res = http_request("/orders", method="POST", body=tampered_payload, headers=order_headers)
    print(f"Tampered request status: {status} (Expected: 400 Bad Request)")
    print(f"Rejection response: {tampered_res.get('message')}")
    assert status == 400, "Tampered payload with existing key must return 400"

    # Step 7: Order Cancellation and Stock Restoration
    print("\n--- Step 7: Cancel Order and Restore Stock Exactly Once ---")
    status, cancel_res = http_request(f"/orders/{order_id}/cancel", method="POST", headers=auth_headers)
    print(f"Cancel status: {status}, New Order Status: {cancel_res.get('status')}")
    assert cancel_res.get("status") == "CANCELLED", "Order status must be CANCELLED"

    status, restored_prod = http_request(f"/products/{prod_id}")
    print(f"Stock after cancellation: {restored_prod['stock']} (Expected: {initial_stock}, perfectly restored)")
    assert restored_prod["stock"] == initial_stock, "Stock must be fully restored"

    # Step 8: Double-Cancellation Protection
    print("\n--- Step 8: Prevent Double Cancellation ---")
    status, second_cancel = http_request(f"/orders/{order_id}/cancel", method="POST", headers=auth_headers)
    print(f"Second cancel status: {status} (Expected: 400 Bad Request)")
    print(f"Rejection message: {second_cancel.get('message')}")
    assert status == 400, "Double cancellation must be rejected"

    status, final_prod = http_request(f"/products/{prod_id}")
    print(f"Stock after second cancel attempt: {final_prod['stock']} (Strictly unchanged)")
    assert final_prod["stock"] == initial_stock, "Stock must not be restored twice"

    print("\n" + "=" * 70)
    print("ALL ORDER WORKFLOW VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_demonstration()
