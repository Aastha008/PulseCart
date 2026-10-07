# PulseCart E-Commerce Operational Backend

A production-grade Java 21 and Spring Boot 3.3 RESTful backend powering PulseCart's transactional e-commerce engine, product catalog, inventory locking, and order workflows. Supplies verified operational transaction data downstream to PulseCart's analytics warehouse.

---

## 1. Modular Monolith Architecture

The backend avoids unnecessary microservice complexity by utilizing a cohesive **modular monolith** structured across strict responsibility layers:

```
backend/src/main/java/com/pulsecart/backend/
├── config/             # Spring Security, Flyway, OpenAPI & Data Initializer
├── controller/         # REST Controllers with HTTP status mappings and Swagger tags
├── dto/                # Immutable Java 21 Records for request/response contracts
├── entity/             # JPA Entities (User, Product, Inventory, Order, OrderItem, IdempotencyRecord)
├── exception/          # GlobalExceptionHandler with RFC-7807 compatible ApiError structures
├── repository/         # Spring Data JPA repositories with atomic conditional queries
├── security/           # Stateless JWT Service, UserDetailsService, and Auth Filter
└── service/            # Transactional business logic (@Transactional boundaries)
```

### Layer Responsibilities
- **Controller Layer**: Decoupled HTTP interface handling URL routing, query parameter deserialization, `@Valid` bean validation, and returning typed `ResponseEntity<T>` payloads with standard HTTP status codes (200, 201, 400, 401, 403, 404, 409).
- **Service Layer**: Owns transactional business boundaries (`@Transactional`), price calculation rules, stock deductions, idempotency verification, and domain event triggering.
- **Repository Layer**: Provides Spring Data JPA abstraction with custom atomic updates (`decrementStockIfSufficient`, `incrementStock`) and indexes.
- **DTO Layer**: Implemented using **Java 21 Records**, preventing internal entity state exposure, over-posting attacks, and lazy-loading serialization leaks.
- **Security Layer**: Enforces stateless authentication using signed HMAC-SHA256 JWT tokens, BCrypt password hashing, and role-based permissions (`ROLE_CUSTOMER`, `ROLE_ADMIN`).

---

## 2. Database Schema & Flyway Migrations

The database utilizes PostgreSQL with Flyway versioned migrations located in `src/main/resources/db/migration/`:

- `V1__init_schema.sql`:
  - `users`: Identity accounts with email uniqueness constraint and BCrypt password hashes.
  - `products`: Catalog entries with `DECIMAL(12,2)` price and cost precision.
  - `inventory`: Linked 1:1 with products, tracking `stock` with non-negative constraints (`stock >= 0`).
  - `orders`: Purchase orders storing subtotal, tax (8%), shipping, discounts, and total amounts.
  - `order_items`: Line items storing immutable purchase-time snapshots (`unit_price`, `total_price`).
  - `idempotency_records`: Client idempotency key storage tracking cached responses.
- `V2__seed_products.sql`:
  - Initial product catalog and inventory across Electronics, Apparel, and Home & Kitchen.

---

## 3. Concurrency Strategy & Preventing Overselling

To prevent overselling when simultaneous checkout requests hit the last available stock, the backend uses **Atomic Conditional Updates** directly at the database engine level:

```sql
UPDATE inventory 
SET stock = stock - :quantity 
WHERE product_id = :productId AND stock >= :quantity
```

### Why Atomic Conditional Updates?
1. **Zero Race Conditions**: The database row-level write lock ensures that only the first thread to execute the update receives an affected row count of `1`.
2. **Deterministic Stock Checks**: Subsequent simultaneous threads find `stock >= :quantity` evaluates to `false`, returning `0` updated rows.
3. **Immediate Rollback**: When `updated == 0`, `OrderService` immediately throws `InsufficientStockException`, rolling back the transaction.
4. **Verified Invariant**: In concurrent stress testing with 10 simultaneous threads competing for the last 1 item, **exactly 1 order succeeded, exactly 9 orders were rejected**, and the ending stock was **exactly 0 (no overselling)**.

---

## 4. Idempotency Key Workflow

Network timeouts or duplicate client clicks can cause clients to submit duplicate order requests. The backend supports the standard HTTP header:

```http
Idempotency-Key: 7b819e64-5d55-46f8-9a91-4475510fba32
```

1. On order creation, `OrderService` checks `idempotency_records` for `(idempotencyKey, userId)`.
2. If already processed, the cached response payload is returned immediately with HTTP 201/200.
3. No duplicate order is created, and **inventory stock is NOT decremented a second time**.

---

## 5. Security & Authorization Matrix

| Endpoint | Method | Role | Ownership Rule |
| :--- | :--- | :--- | :--- |
| `/api/v1/auth/register` | `POST` | Public | Unrestricted |
| `/api/v1/auth/login` | `POST` | Public | Unrestricted |
| `/api/v1/products` | `GET` | Public | Unrestricted |
| `/api/v1/products/{id}` | `GET` | Public | Unrestricted |
| `/api/v1/orders` | `POST` | `ROLE_CUSTOMER` | Requires valid JWT |
| `/api/v1/orders` | `GET` | `ROLE_CUSTOMER` | Scoped to authenticated user's orders |
| `/api/v1/orders/{id}` | `GET` | `ROLE_CUSTOMER` / `ADMIN` | Customer can only view their own order |
| `/api/v1/orders/{id}/cancel` | `POST` | `ROLE_CUSTOMER` / `ADMIN` | Customer can only cancel their own order |
| `/api/v1/admin/products` | `POST` | `ROLE_ADMIN` | Forbidden to regular customers (403) |
| `/api/v1/admin/inventory/{id}`| `PUT` | `ROLE_ADMIN` | Forbidden to regular customers (403) |
| `/api/v1/admin/analytics/export-orders` | `GET` | `ROLE_ADMIN` | Data pipeline ingestion endpoint |

---

## 6. Running and Testing Locally

### Prerequisites
- Java 21 (Eclipse Temurin recommended)
- Maven 3.9+ (or `./mvnw.cmd` / `./mvnw`)
- Docker & Docker Compose (optional for containerized deployment)

### Execute Tests
```bash
cd backend
mvn test
```

### Run with Local PostgreSQL
```bash
mvn spring-boot:run
```

### Run with Docker Compose
```bash
docker-compose up --build
```
- API Base: `http://localhost:8080`
- Swagger UI Documentation: `http://localhost:8080/swagger-ui.html`
- OpenAPI Specification: `http://localhost:8080/v3/api-docs`
- Actuator Health Check: `http://localhost:8080/actuator/health`

---

## 7. Example API Requests

### 1. Register Customer
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "customer@example.com",
  "password": "Password123!",
  "firstName": "Jane",
  "lastName": "Doe"
}
```

### 2. Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "customer@example.com",
  "password": "Password123!"
}
```
*Response returns JWT Bearer token.*

### 3. Place Order (with Idempotency Key)
```http
POST /api/v1/orders
Authorization: Bearer <JWT_TOKEN>
Idempotency-Key: 927d6d1b-7a3b-489e-9907-fcf8ca1e30a5
Content-Type: application/json

{
  "items": [
    {
      "productId": 1,
      "quantity": 2
    }
  ],
  "paymentMethod": "CREDIT_CARD"
}
```

### 4. Cancel Order
```http
POST /api/v1/orders/1/cancel
Authorization: Bearer <JWT_TOKEN>
```
