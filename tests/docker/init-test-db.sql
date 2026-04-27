-- Test database initialization script
-- Runs on all MySQL versions (5.7, 8.0, 8.4) via docker-entrypoint-initdb.d
-- The MYSQL_DATABASE env var creates `testdb`; we populate schemas/tables here.

USE testdb;

-- ===========================================================================
-- Schema: sales
-- ===========================================================================

CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    sku VARCHAR(50) NOT NULL UNIQUE,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INT NOT NULL DEFAULT 0,
    category VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_products_category (category),
    INDEX idx_products_sku (sku)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_orders_customer_id (customer_id),
    INDEX idx_orders_status (status),
    INDEX idx_orders_created_at (created_at),
    CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    INDEX idx_order_items_order_id (order_id),
    INDEX idx_order_items_product_id (product_id),
    CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(id),
    CONSTRAINT fk_order_items_product FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE stock_movements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    quantity_change INT NOT NULL,
    movement_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_stock_movements_product_id (product_id),
    INDEX idx_stock_movements_type (movement_type),
    CONSTRAINT fk_stock_movements_product FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===========================================================================
-- Seed data
-- ===========================================================================

-- 50 products across 5 categories
INSERT INTO products (name, sku, price, stock_quantity, category)
SELECT
    CONCAT('Product ', n) AS name,
    CONCAT('SKU-', LPAD(n, 5, '0')) AS sku,
    ROUND(1 + RAND() * 99, 2) AS price,
    FLOOR(RAND() * 500) AS stock_quantity,
    ELT(1 + (n MOD 5), 'Electronics', 'Books', 'Clothing', 'Home', 'Toys') AS category
FROM (
    SELECT a.N + b.N * 10 + 1 AS n
    FROM (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
          UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) a
    CROSS JOIN
         (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4) b
) seq;

-- 30 customers
INSERT INTO customers (name, email, status)
SELECT
    CONCAT('Customer ', n) AS name,
    CONCAT('customer', n, '@example.com') AS email,
    IF(n MOD 7 = 0, 'inactive', 'active') AS status
FROM (
    SELECT a.N + b.N * 10 + 1 AS n
    FROM (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
          UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) a
    CROSS JOIN
         (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2) b
) seq;

-- 40 orders distributed across customers
INSERT INTO orders (customer_id, total_amount, status)
SELECT
    1 + (n MOD 30) AS customer_id,
    ROUND(10 + RAND() * 990, 2) AS total_amount,
    ELT(1 + (n MOD 4), 'pending', 'paid', 'shipped', 'completed') AS status
FROM (
    SELECT a.N + b.N * 10 + 1 AS n
    FROM (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
          UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) a
    CROSS JOIN
         (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3) b
) seq;

-- Stock movements (one per product)
INSERT INTO stock_movements (product_id, quantity_change, movement_type)
SELECT id, FLOOR(10 + RAND() * 90), 'inbound' FROM products;

-- ===========================================================================
-- Generate query digest activity for performance_schema
-- ===========================================================================
-- Run a few representative SELECTs so events_statements_summary_by_digest
-- has rows when the slow-query / table-io tools are tested.

SELECT COUNT(*) FROM customers;
SELECT COUNT(*) FROM orders WHERE status = 'paid';
SELECT c.name, COUNT(o.id) AS order_count
FROM customers c LEFT JOIN orders o ON o.customer_id = c.id
GROUP BY c.id, c.name LIMIT 10;
SELECT category, COUNT(*) AS product_count, AVG(price) AS avg_price
FROM products GROUP BY category;
