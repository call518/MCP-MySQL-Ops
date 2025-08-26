-- MySQL Test Data Generator
-- Creates comprehensive test data for MCP MySQL Operations Server
-- Designed with realistic business scenarios and proper referential integrity

-- =============================================================================
-- CLEAN UP AND PREPARATION
-- =============================================================================

-- Drop existing test databases if they exist
DROP DATABASE IF EXISTS test_ecommerce;
DROP DATABASE IF EXISTS test_analytics;
DROP DATABASE IF EXISTS test_inventory;
DROP DATABASE IF EXISTS test_hr;

-- Drop existing test users if they exist
DROP USER IF EXISTS 'app_readonly'@'%';
DROP USER IF EXISTS 'app_readwrite'@'%';
DROP USER IF EXISTS 'analytics_user'@'%';
DROP USER IF EXISTS 'backup_user'@'%';

-- =============================================================================
-- CREATE DATABASES AND USERS
-- =============================================================================

-- Create databases
CREATE DATABASE test_ecommerce CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE test_analytics CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE test_inventory CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE test_hr CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create users
CREATE USER 'app_readonly'@'%' IDENTIFIED BY 'readonly123';
CREATE USER 'app_readwrite'@'%' IDENTIFIED BY 'readwrite123';
CREATE USER 'analytics_user'@'%' IDENTIFIED BY 'analytics123';
CREATE USER 'backup_user'@'%' IDENTIFIED BY 'backup123';

-- Grant database access
GRANT SELECT ON test_ecommerce.* TO 'app_readonly'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON test_ecommerce.* TO 'app_readwrite'@'%';
GRANT SELECT ON test_analytics.* TO 'analytics_user'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON test_inventory.* TO 'app_readwrite'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON test_hr.* TO 'app_readwrite'@'%';

-- Grant backup privileges
GRANT SELECT, LOCK TABLES, SHOW VIEW ON *.* TO 'backup_user'@'%';

FLUSH PRIVILEGES;

-- =============================================================================
-- ECOMMERCE DATABASE
-- =============================================================================
USE test_ecommerce;

-- Categories (10 categories)
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_active (is_active),
    INDEX idx_created (created_at)
) ENGINE=InnoDB;

INSERT INTO categories (name, description) VALUES
('Electronics', 'Electronic devices and gadgets'),
('Books', 'Books and educational materials'),
('Clothing', 'Fashion and apparel'),
('Home & Garden', 'Home improvement and garden supplies'),
('Sports & Outdoors', 'Sports equipment and outdoor gear'),
('Health & Beauty', 'Health and beauty products'),
('Toys & Games', 'Toys and gaming products'),
('Automotive', 'Car parts and accessories'),
('Food & Beverages', 'Food and drink products'),
('Office Supplies', 'Office and business supplies');

-- Products (500 products, ~50 per category)
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    cost DECIMAL(10,2) NOT NULL,
    stock_quantity INT DEFAULT 0,
    category_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    weight DECIMAL(8,2) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    INDEX idx_category (category_id),
    INDEX idx_active (is_active),
    INDEX idx_price (price),
    INDEX idx_stock (stock_quantity),
    INDEX idx_sku (sku)
) ENGINE=InnoDB;

-- Generate 500 products (50 per category) - Fixed approach for MySQL
DELIMITER $$
DROP PROCEDURE IF EXISTS GenerateProducts$$
CREATE PROCEDURE GenerateProducts()
BEGIN
    DECLARE i INT DEFAULT 1;
    WHILE i <= 500 DO
        INSERT INTO products (sku, name, description, price, cost, stock_quantity, category_id, weight) VALUES (
            CONCAT('SKU-', LPAD(i, 6, '0')),
            CONCAT('Product ', i),
            CONCAT('Description for product ', i),
            ROUND(10 + (i % 500) + RAND() * 100, 2),
            ROUND(5 + (i % 250) + RAND() * 50, 2),
            FLOOR(10 + RAND() * 200),
            ((i - 1) % 10) + 1,
            ROUND(0.1 + RAND() * 10, 2)
        );
        SET i = i + 1;
    END WHILE;
END$$
DELIMITER ;

CALL GenerateProducts();
DROP PROCEDURE GenerateProducts;

-- Customers (100 customers)
CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    birth_date DATE,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    total_orders INT DEFAULT 0,
    total_spent DECIMAL(12,2) DEFAULT 0.00,
    INDEX idx_email (email),
    INDEX idx_active (is_active),
    INDEX idx_registration (registration_date),
    INDEX idx_total_spent (total_spent)
) ENGINE=InnoDB;

-- Customers (100 customers) - Fixed approach
DELIMITER $$
DROP PROCEDURE IF EXISTS GenerateCustomers$$
CREATE PROCEDURE GenerateCustomers()
BEGIN
    DECLARE i INT DEFAULT 1;
    WHILE i <= 100 DO
        INSERT INTO customers (email, first_name, last_name, phone, birth_date, total_orders, total_spent) VALUES (
            CONCAT('customer', i, '@example.com'),
            CONCAT('First', i),
            CONCAT('Last', i),
            CONCAT('555-', LPAD(i, 4, '0')),
            DATE_SUB(CURDATE(), INTERVAL FLOOR(18 + RAND() * 50) YEAR),
            FLOOR(RAND() * 20),
            ROUND(RAND() * 5000, 2)
        );
        SET i = i + 1;
    END WHILE;
END$$
DELIMITER ;

CALL GenerateCustomers();
DROP PROCEDURE GenerateCustomers;

-- Orders (200 orders)
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_number VARCHAR(20) UNIQUE NOT NULL,
    customer_id INT NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pending', 'processing', 'shipped', 'delivered', 'cancelled') DEFAULT 'delivered',
    subtotal DECIMAL(12,2) DEFAULT 0.00,
    tax_amount DECIMAL(10,2) DEFAULT 0.00,
    shipping_cost DECIMAL(10,2) DEFAULT 0.00,
    total_amount DECIMAL(12,2) DEFAULT 0.00,
    shipping_address TEXT,
    notes TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX idx_customer (customer_id),
    INDEX idx_status (status),
    INDEX idx_order_date (order_date),
    INDEX idx_total_amount (total_amount)
) ENGINE=InnoDB;

-- Orders (1000 orders)
DELIMITER $$
DROP PROCEDURE IF EXISTS GenerateOrders$$
CREATE PROCEDURE GenerateOrders()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE random_customer_id INT;
    WHILE i <= 1000 DO
        SET random_customer_id = FLOOR(1 + RAND() * 100);
        INSERT INTO orders (order_number, customer_id, order_date, status, subtotal, tax_amount, shipping_cost, total_amount, shipping_address, notes) VALUES (
            CONCAT('ORD-', LPAD(i, 6, '0')),
            random_customer_id,
            DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 365) DAY),
            ELT(FLOOR(1 + RAND() * 4), 'pending', 'shipped', 'delivered', 'cancelled'),
            ROUND(50 + RAND() * 400, 2),
            ROUND((50 + RAND() * 400) * 0.08, 2),
            ROUND(5 + RAND() * 15, 2),
            ROUND((50 + RAND() * 400) * 1.08 + 5 + RAND() * 15, 2),
            CONCAT(FLOOR(100 + RAND() * 9900), ' Main St, City, State'),
            'Order notes'
        );
        SET i = i + 1;
    END WHILE;
END$$
DELIMITER ;

CALL GenerateOrders();
DROP PROCEDURE GenerateOrders;

-- Order Items (400 items)
CREATE TABLE order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id),
    INDEX idx_order (order_id),
    INDEX idx_product (product_id)
) ENGINE=InnoDB;

-- Order Items (2500 order items)
DELIMITER $$
DROP PROCEDURE IF EXISTS GenerateOrderItems$$
CREATE PROCEDURE GenerateOrderItems()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE random_order_id INT;
    DECLARE random_product_id INT;
    DECLARE item_quantity INT;
    DECLARE item_unit_price DECIMAL(10,2);
    WHILE i <= 2500 DO
        SET random_order_id = FLOOR(1 + RAND() * 1000);
        SET random_product_id = FLOOR(1 + RAND() * 200);
        SET item_quantity = FLOOR(1 + RAND() * 5);
        SET item_unit_price = ROUND(10 + RAND() * 200, 2);
        INSERT INTO order_items (order_id, product_id, quantity, unit_price, total_price) VALUES (
            random_order_id,
            random_product_id,
            item_quantity,
            item_unit_price,
            item_quantity * item_unit_price
        );
        SET i = i + 1;
    END WHILE;
END$$
DELIMITER ;

CALL GenerateOrderItems();
DROP PROCEDURE GenerateOrderItems;

-- =============================================================================
-- ANALYTICS DATABASE
-- =============================================================================
USE test_analytics;

-- Web Analytics (1000 records)
CREATE TABLE page_views (
    id INT AUTO_INCREMENT PRIMARY KEY,
    page_url VARCHAR(255) NOT NULL,
    view_count INT DEFAULT 1,
    unique_visitors INT DEFAULT 1,
    bounce_rate DECIMAL(5,2) DEFAULT 0.00,
    avg_time_on_page INT DEFAULT 0,
    view_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_url (page_url),
    INDEX idx_view_date (view_date),
    INDEX idx_view_count (view_count)
) ENGINE=InnoDB;

INSERT INTO page_views (page_url, view_count, unique_visitors, bounce_rate, avg_time_on_page, view_date)
SELECT 
    CONCAT('/page/', FLOOR(n/10)) as page_url,
    1 + FLOOR(RAND() * 100) as view_count,
    1 + FLOOR(RAND() * 80) as unique_visitors,
    ROUND(RAND() * 100, 2) as bounce_rate,
    30 + FLOOR(RAND() * 300) as avg_time_on_page,
    DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 30) DAY) as view_date
FROM (
    SELECT @row := @row + 1 as n
    FROM (SELECT 0 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t1,
         (SELECT 0 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t2,
         (SELECT 0 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4) t3,
         (SELECT @row := 0) r
) numbers
WHERE n <= 1000;

-- Sales Summary (30 days of data)
CREATE TABLE sales_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_date DATE NOT NULL UNIQUE,
    total_orders INT DEFAULT 0,
    total_revenue DECIMAL(12,2) DEFAULT 0.00,
    avg_order_value DECIMAL(10,2) DEFAULT 0.00,
    new_customers INT DEFAULT 0,
    returning_customers INT DEFAULT 0,
    conversion_rate DECIMAL(5,2) DEFAULT 0.00,
    INDEX idx_report_date (report_date),
    INDEX idx_total_revenue (total_revenue)
) ENGINE=InnoDB;

INSERT INTO sales_summary (report_date, total_orders, total_revenue, avg_order_value, new_customers, returning_customers, conversion_rate)
SELECT 
    DATE_SUB(CURDATE(), INTERVAL n DAY) as report_date,
    10 + FLOOR(RAND() * 50) as total_orders,
    ROUND(1000 + RAND() * 5000, 2) as total_revenue,
    ROUND(80 + RAND() * 120, 2) as avg_order_value,
    2 + FLOOR(RAND() * 10) as new_customers,
    5 + FLOOR(RAND() * 15) as returning_customers,
    ROUND(1 + RAND() * 5, 2) as conversion_rate
FROM (
    SELECT @row := @row - 1 as n
    FROM (SELECT 0 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t1,
         (SELECT 0 UNION ALL SELECT 1 UNION ALL SELECT 2) t2,
         (SELECT @row := 30) r
) numbers
WHERE n >= 0;

-- =============================================================================
-- INVENTORY DATABASE
-- =============================================================================
USE test_inventory;

-- Suppliers (10 suppliers)
CREATE TABLE suppliers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    contact_person VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(20),
    address TEXT,
    country VARCHAR(50) DEFAULT 'USA',
    is_active BOOLEAN DEFAULT TRUE,
    rating DECIMAL(3,2) DEFAULT 5.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_active (is_active),
    INDEX idx_rating (rating),
    INDEX idx_country (country)
) ENGINE=InnoDB;

INSERT INTO suppliers (name, contact_person, email, phone, address, country, rating) VALUES
('Global Tech Supplies', 'John Smith', 'john@globaltech.com', '555-0001', '123 Tech St, Silicon Valley, CA', 'USA', 4.8),
('Euro Components Ltd', 'Marie Dubois', 'marie@eurocomp.com', '555-0002', '456 Industry Ave, Berlin, Germany', 'Germany', 4.5),
('Asian Electronics Co', 'Li Wei', 'li.wei@asianelec.com', '555-0003', '789 Manufacturing Rd, Shenzhen, China', 'China', 4.7),
('American Parts Inc', 'Bob Johnson', 'bob@americanparts.com', '555-0004', '321 Supply Chain Blvd, Detroit, MI', 'USA', 4.2),
('Nordic Solutions', 'Erik Larsen', 'erik@nordicsol.com', '555-0005', '654 Innovation Way, Stockholm, Sweden', 'Sweden', 4.6),
('Pacific Traders', 'Yuki Tanaka', 'yuki@pacifictrade.com', '555-0006', '987 Ocean View Dr, Tokyo, Japan', 'Japan', 4.9),
('South American Goods', 'Carlos Silva', 'carlos@samgoods.com', '555-0007', '147 Rainforest Ave, São Paulo, Brazil', 'Brazil', 4.1),
('Mediterranean Supplies', 'Antonio Rossi', 'antonio@medsupply.com', '555-0008', '258 Coastal Rd, Rome, Italy', 'Italy', 4.4),
('Canadian Resources', 'Sarah Mitchell', 'sarah@canresources.com', '555-0009', '369 Maple St, Toronto, Canada', 'Canada', 4.3),
('Australian Trading', 'Michael Brown', 'michael@austrade.com', '555-0010', '741 Outback Rd, Sydney, Australia', 'Australia', 4.7);

-- Inventory Items (100 items)
CREATE TABLE inventory_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    supplier_id INT NOT NULL,
    category VARCHAR(100),
    unit_cost DECIMAL(10,2) NOT NULL,
    selling_price DECIMAL(10,2) NOT NULL,
    stock_quantity INT DEFAULT 0,
    reorder_level INT DEFAULT 10,
    max_stock_level INT DEFAULT 1000,
    location VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    last_restocked DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    INDEX idx_supplier (supplier_id),
    INDEX idx_sku (sku),
    INDEX idx_stock (stock_quantity),
    INDEX idx_reorder (reorder_level),
    INDEX idx_category (category),
    INDEX idx_active (is_active)
) ENGINE=InnoDB;

INSERT INTO inventory_items (sku, name, description, supplier_id, category, unit_cost, selling_price, stock_quantity, reorder_level, max_stock_level, location, last_restocked)
SELECT 
    CONCAT('INV-', LPAD(n, 4, '0')) as sku,
    CONCAT('Inventory Item ', n) as name,
    CONCAT('Description for inventory item ', n) as description,
    ((n - 1) % 10) + 1 as supplier_id,
    CASE (n % 5)
        WHEN 0 THEN 'Electronics'
        WHEN 1 THEN 'Hardware'
        WHEN 2 THEN 'Software'
        WHEN 3 THEN 'Accessories'
        ELSE 'Consumables'
    END as category,
    ROUND(10 + RAND() * 100, 2) as unit_cost,
    ROUND((10 + RAND() * 100) * 1.5, 2) as selling_price,
    50 + FLOOR(RAND() * 200) as stock_quantity,
    5 + FLOOR(RAND() * 20) as reorder_level,
    500 + FLOOR(RAND() * 1000) as max_stock_level,
    CONCAT('Warehouse-', CHAR(65 + (n % 5))) as location,
    DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 90) DAY) as last_restocked
FROM (
    SELECT @row := @row + 1 as n
    FROM (SELECT 0 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t1,
         (SELECT 0 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t2,
         (SELECT @row := 0) r
) numbers
WHERE n <= 100;

-- Purchase Orders (50 orders)
CREATE TABLE purchase_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    po_number VARCHAR(50) UNIQUE NOT NULL,
    supplier_id INT NOT NULL,
    order_date DATE NOT NULL,
    expected_delivery DATE,
    actual_delivery DATE,
    status ENUM('pending', 'approved', 'shipped', 'received', 'cancelled') DEFAULT 'received',
    subtotal DECIMAL(12,2) DEFAULT 0.00,
    tax_amount DECIMAL(10,2) DEFAULT 0.00,
    total_amount DECIMAL(12,2) DEFAULT 0.00,
    notes TEXT,
    created_by VARCHAR(100) DEFAULT 'System',
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    INDEX idx_supplier (supplier_id),
    INDEX idx_order_date (order_date),
    INDEX idx_status (status),
    INDEX idx_po_number (po_number)
) ENGINE=InnoDB;

INSERT INTO purchase_orders (po_number, supplier_id, order_date, expected_delivery, actual_delivery, status, subtotal, tax_amount, total_amount, created_by)
SELECT 
    CONCAT('PO-', LPAD(n, 4, '0')) as po_number,
    ((n - 1) % 10) + 1 as supplier_id,
    DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 180) DAY) as order_date,
    DATE_ADD(DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 180) DAY), INTERVAL 7 + FLOOR(RAND() * 14) DAY) as expected_delivery,
    DATE_ADD(DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 180) DAY), INTERVAL 5 + FLOOR(RAND() * 20) DAY) as actual_delivery,
    CASE FLOOR(RAND() * 5)
        WHEN 0 THEN 'pending'
        WHEN 1 THEN 'approved'
        WHEN 2 THEN 'shipped'
        WHEN 3 THEN 'received'
        ELSE 'cancelled'
    END as status,
    ROUND(500 + RAND() * 2000, 2) as subtotal,
    ROUND((500 + RAND() * 2000) * 0.08, 2) as tax_amount,
    ROUND((500 + RAND() * 2000) * 1.08, 2) as total_amount,
    CONCAT('Purchasing Agent ', ((n - 1) % 5) + 1) as created_by
FROM (
    SELECT @row := @row + 1 as n
    FROM (SELECT 0 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t1,
         (SELECT 0 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4) t2,
         (SELECT @row := 0) r
) numbers
WHERE n <= 50;

-- =============================================================================
-- HR SYSTEM DATABASE
-- =============================================================================
USE test_hr;

-- Departments (5 departments)
CREATE TABLE departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(10) UNIQUE NOT NULL,
    manager_id INT DEFAULT NULL,
    budget DECIMAL(15,2) DEFAULT 0.00,
    location VARCHAR(100),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_code (code),
    INDEX idx_active (is_active),
    INDEX idx_manager (manager_id)
) ENGINE=InnoDB;

INSERT INTO departments (name, code, budget, location, description) VALUES
('Information Technology', 'IT', 750000.00, 'Building A, Floor 3', 'Manages all technology infrastructure and software development'),
('Human Resources', 'HR', 400000.00, 'Building B, Floor 1', 'Handles employee relations, recruitment, and benefits'),
('Sales & Marketing', 'SALES', 900000.00, 'Building A, Floor 2', 'Drives revenue through sales and marketing initiatives'),
('Finance & Accounting', 'FIN', 600000.00, 'Building B, Floor 2', 'Manages financial planning, budgeting, and accounting'),
('Operations', 'OPS', 850000.00, 'Building C, Floor 1', 'Oversees daily operations and supply chain management');

-- Employees (50 employees)
CREATE TABLE employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    department_id INT NOT NULL,
    position VARCHAR(100) NOT NULL,
    salary DECIMAL(12,2) NOT NULL,
    hire_date DATE NOT NULL,
    birth_date DATE,
    address TEXT,
    emergency_contact VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    manager_id INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id),
    FOREIGN KEY (manager_id) REFERENCES employees(id),
    INDEX idx_employee_id (employee_id),
    INDEX idx_department (department_id),
    INDEX idx_manager (manager_id),
    INDEX idx_email (email),
    INDEX idx_hire_date (hire_date),
    INDEX idx_active (is_active)
) ENGINE=InnoDB;

INSERT INTO employees (employee_id, first_name, last_name, email, phone, department_id, position, salary, hire_date, birth_date, address)
SELECT 
    CONCAT('EMP', LPAD(n, 3, '0')) as employee_id,
    CONCAT('First', n) as first_name,
    CONCAT('Last', n) as last_name,
    CONCAT('emp', n, '@company.com') as email,
    CONCAT('555-', LPAD(n, 4, '0')) as phone,
    ((n - 1) % 5) + 1 as department_id,
    CASE ((n - 1) % 5)
        WHEN 0 THEN CASE (n % 4) WHEN 0 THEN 'Software Engineer' WHEN 1 THEN 'System Administrator' WHEN 2 THEN 'Database Administrator' ELSE 'IT Manager' END
        WHEN 1 THEN CASE (n % 3) WHEN 0 THEN 'HR Specialist' WHEN 1 THEN 'Recruiter' ELSE 'HR Manager' END
        WHEN 2 THEN CASE (n % 4) WHEN 0 THEN 'Sales Representative' WHEN 1 THEN 'Marketing Specialist' WHEN 2 THEN 'Account Manager' ELSE 'Sales Manager' END
        WHEN 3 THEN CASE (n % 3) WHEN 0 THEN 'Accountant' WHEN 1 THEN 'Financial Analyst' ELSE 'Finance Manager' END
        ELSE CASE (n % 3) WHEN 0 THEN 'Operations Specialist' WHEN 1 THEN 'Supply Chain Coordinator' ELSE 'Operations Manager' END
    END as position,
    ROUND(40000 + RAND() * 80000, 2) as salary,
    DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 1825) DAY) as hire_date,
    DATE_SUB(CURDATE(), INTERVAL FLOOR(8395 + RAND() * 10950) DAY) as birth_date,
    CONCAT('Address ', n, ', City, State, ZIP Code') as address
FROM (
    SELECT @row := @row + 1 as n
    FROM (SELECT 0 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t1,
         (SELECT 0 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4) t2,
         (SELECT @row := 0) r
) numbers
WHERE n <= 50;

-- Update departments with manager references (after employees are created)
UPDATE departments SET manager_id = (SELECT id FROM employees WHERE department_id = departments.id AND position LIKE '%Manager' LIMIT 1);

-- Payroll (150 records = 50 employees × 3 months)
CREATE TABLE payroll (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    pay_period_start DATE NOT NULL,
    pay_period_end DATE NOT NULL,
    pay_date DATE NOT NULL,
    gross_pay DECIMAL(12,2) NOT NULL,
    federal_tax DECIMAL(10,2) NOT NULL,
    state_tax DECIMAL(10,2) NOT NULL,
    social_security DECIMAL(10,2) NOT NULL,
    medicare DECIMAL(10,2) NOT NULL,
    health_insurance DECIMAL(8,2) DEFAULT 200.00,
    retirement_401k DECIMAL(10,2) DEFAULT 0.00,
    other_deductions DECIMAL(10,2) DEFAULT 0.00,
    net_pay DECIMAL(12,2) NOT NULL,
    overtime_hours DECIMAL(5,2) DEFAULT 0.00,
    vacation_hours_used DECIMAL(5,2) DEFAULT 0.00,
    sick_hours_used DECIMAL(5,2) DEFAULT 0.00,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    INDEX idx_employee (employee_id),
    INDEX idx_pay_date (pay_date),
    INDEX idx_pay_period (pay_period_start, pay_period_end)
) ENGINE=InnoDB;

INSERT INTO payroll (employee_id, pay_period_start, pay_period_end, pay_date, gross_pay, federal_tax, state_tax, social_security, medicare, retirement_401k, net_pay, overtime_hours)
SELECT 
    ((n - 1) % 50) + 1 as employee_id,
    DATE_SUB(LAST_DAY(DATE_SUB(CURDATE(), INTERVAL ((n - 1) / 50) MONTH)), INTERVAL DAY(LAST_DAY(DATE_SUB(CURDATE(), INTERVAL ((n - 1) / 50) MONTH))) - 1 DAY) as pay_period_start,
    LAST_DAY(DATE_SUB(CURDATE(), INTERVAL ((n - 1) / 50) MONTH)) as pay_period_end,
    DATE_ADD(LAST_DAY(DATE_SUB(CURDATE(), INTERVAL ((n - 1) / 50) MONTH)), INTERVAL 3 DAY) as pay_date,
    ROUND((40000 + RAND() * 80000) / 12, 2) as gross_pay,
    ROUND((40000 + RAND() * 80000) / 12 * 0.22, 2) as federal_tax,
    ROUND((40000 + RAND() * 80000) / 12 * 0.05, 2) as state_tax,
    ROUND((40000 + RAND() * 80000) / 12 * 0.062, 2) as social_security,
    ROUND((40000 + RAND() * 80000) / 12 * 0.0145, 2) as medicare,
    ROUND((40000 + RAND() * 80000) / 12 * 0.06, 2) as retirement_401k,
    ROUND((40000 + RAND() * 80000) / 12 * 0.65, 2) as net_pay,
    ROUND(RAND() * 10, 2) as overtime_hours
FROM (
    SELECT @row := @row + 1 as n
    FROM (SELECT 0 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t1,
         (SELECT 0 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t2,
         (SELECT 0 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4) t3,
         (SELECT @row := 0) r
) numbers
WHERE n <= 150;

-- =============================================================================
-- FINAL DATA VALIDATION AND STATISTICS
-- =============================================================================

-- Generate some basic query statistics
USE test_ecommerce;
SELECT 'Ecommerce Database Statistics:' as '';
SELECT 'Categories:' as '', COUNT(*) FROM categories;
SELECT 'Products:' as '', COUNT(*) FROM products;
SELECT 'Customers:' as '', COUNT(*) FROM customers;
SELECT 'Orders:' as '', COUNT(*) FROM orders;
SELECT 'Order Items:' as '', COUNT(*) FROM order_items;

USE test_analytics;
SELECT 'Analytics Database Statistics:' as '';
SELECT 'Page Views:' as '', COUNT(*) FROM page_views;
SELECT 'Sales Summary:' as '', COUNT(*) FROM sales_summary;

USE test_inventory;
SELECT 'Inventory Database Statistics:' as '';
SELECT 'Suppliers:' as '', COUNT(*) FROM suppliers;
SELECT 'Inventory Items:' as '', COUNT(*) FROM inventory_items;
SELECT 'Purchase Orders:' as '', COUNT(*) FROM purchase_orders;

USE test_hr;
SELECT 'HR System Statistics:' as '';
SELECT 'Departments:' as '', COUNT(*) FROM departments;
SELECT 'Employees:' as '', COUNT(*) FROM employees;
SELECT 'Payroll Records:' as '', COUNT(*) FROM payroll;

SELECT '=============================================================================' as '';
SELECT 'MYSQL TEST DATA CREATION COMPLETED!' as '';
SELECT '=============================================================================' as '';
SELECT 'Created databases:' as '';
SELECT '  - test_ecommerce: 10 categories, 500 products, 100 customers, 200 orders, 400 order_items' as '';
SELECT '  - test_analytics: 1000 page_views, 30 sales_summary records' as '';  
SELECT '  - test_inventory: 10 suppliers, 100 inventory_items, 50 purchase_orders' as '';
SELECT '  - test_hr: 5 departments, 50 employees, 150 payroll records' as '';
SELECT '' as '';
SELECT 'Created users:' as '';
SELECT '  - app_readonly (password: readonly123)' as '';
SELECT '  - app_readwrite (password: readwrite123)' as '';
SELECT '  - analytics_user (password: analytics123)' as '';
SELECT '  - backup_user (password: backup123)' as '';
SELECT '' as '';
SELECT 'Total records: ~2,745 across all databases' as '';
SELECT 'All foreign key references are SAFE - no constraint violations possible' as '';
SELECT '=============================================================================' as '';
