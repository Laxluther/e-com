
-- Categories table
CREATE TABLE categories (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(100) NOT NULL,
    parent_id INT,
    description TEXT,
    image_url VARCHAR(255),
    status ENUM('active', 'inactive') DEFAULT 'active',
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES categories(category_id) ON DELETE SET NULL,
    INDEX idx_parent_id (parent_id),
    INDEX idx_status (status)
);

-- Users table
CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    gender ENUM('male', 'female', 'other'),
    profile_image VARCHAR(255),
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_phone (phone),
    INDEX idx_status (status)
);

-- Addresses table
CREATE TABLE addresses (
    address_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(36) NOT NULL,
    address_type ENUM('home', 'work', 'other') DEFAULT 'home',
    full_name VARCHAR(200) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(100) DEFAULT 'India',
    landmark VARCHAR(255),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_is_default (is_default)
);

-- Products table
CREATE TABLE products (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(255) NOT NULL,
    description TEXT,
    category_id INT NOT NULL,
    brand VARCHAR(100),
    sku VARCHAR(100) UNIQUE,
    price DECIMAL(10, 2) NOT NULL,
    discount_price DECIMAL(10, 2),
    cost_price DECIMAL(10, 2),
    weight DECIMAL(8, 3),
    dimensions VARCHAR(100),
    is_featured BOOLEAN DEFAULT FALSE,
    meta_title VARCHAR(255),
    meta_description TEXT,
    status ENUM('active', 'inactive', 'draft') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(category_id),
    INDEX idx_category_id (category_id),
    INDEX idx_status (status),
    INDEX idx_featured (is_featured),
    INDEX idx_sku (sku),
    FULLTEXT idx_search (product_name, description)
);

-- Product images table
CREATE TABLE product_images (
    image_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    image_url VARCHAR(255) NOT NULL,
    alt_text VARCHAR(255),
    sort_order INT DEFAULT 0,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    INDEX idx_product_id (product_id),
    INDEX idx_is_primary (is_primary)
);

-- Product variants table
CREATE TABLE product_variants (
    variant_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    variant_name VARCHAR(100) NOT NULL,
    variant_value VARCHAR(100) NOT NULL,
    price_adjustment DECIMAL(10, 2) DEFAULT 0,
    weight_adjustment DECIMAL(8, 3) DEFAULT 0,
    sku VARCHAR(100),
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    INDEX idx_product_id (product_id),
    INDEX idx_status (status)
);

-- Inventory table
CREATE TABLE inventory (
    inventory_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    variant_id INT,
    quantity INT NOT NULL DEFAULT 0,
    reserved_quantity INT NOT NULL DEFAULT 0,
    min_stock_level INT DEFAULT 10,
    max_stock_level INT DEFAULT 1000,
    location VARCHAR(100) DEFAULT 'main_warehouse',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(variant_id) ON DELETE SET NULL,
    UNIQUE KEY unique_inventory (product_id, variant_id, location),
    INDEX idx_product_id (product_id),
    INDEX idx_quantity (quantity)
);

-- Shopping cart table
CREATE TABLE cart (
    cart_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(36) NOT NULL,
    product_id INT NOT NULL,
    variant_id INT,
    quantity INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(variant_id) ON DELETE SET NULL,
    UNIQUE KEY unique_cart_item (user_id, product_id, variant_id),
    INDEX idx_user_id (user_id)
);

-- Orders table
CREATE TABLE orders (
    order_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    status ENUM('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded') DEFAULT 'pending',
    subtotal DECIMAL(10, 2) NOT NULL,
    tax_amount DECIMAL(10, 2) DEFAULT 0,
    shipping_amount DECIMAL(10, 2) DEFAULT 0,
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    total_amount DECIMAL(10, 2) NOT NULL,
    payment_method ENUM('cod', 'online', 'wallet') NOT NULL,
    payment_status ENUM('pending', 'completed', 'failed', 'refunded') DEFAULT 'pending',
    shipping_address JSON NOT NULL,
    billing_address JSON,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_order_number (order_number),
    INDEX idx_created_at (created_at)
);

-- Order items table
CREATE TABLE order_items (
    item_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id VARCHAR(36) NOT NULL,
    product_id INT NOT NULL,
    variant_id INT,
    product_name VARCHAR(255) NOT NULL,
    variant_name VARCHAR(100),
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (variant_id) REFERENCES product_variants(variant_id) ON DELETE SET NULL,
    INDEX idx_order_id (order_id),
    INDEX idx_product_id (product_id)
);

-- Order tracking table
CREATE TABLE order_tracking (
    tracking_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id VARCHAR(36) NOT NULL,
    status ENUM('order_placed', 'confirmed', 'processing', 'packed', 'shipped', 'out_for_delivery', 'delivered', 'cancelled') NOT NULL,
    message TEXT,
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    INDEX idx_order_id (order_id),
    INDEX idx_status (status)
);

-- Reviews table
CREATE TABLE reviews (
    review_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    order_id VARCHAR(36),
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(255),
    comment TEXT,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    helpful_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE SET NULL,
    UNIQUE KEY unique_user_product_review (user_id, product_id),
    INDEX idx_product_id (product_id),
    INDEX idx_user_id (user_id),
    INDEX idx_rating (rating)
);

-- Wishlist table
CREATE TABLE wishlist (
    wishlist_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(36) NOT NULL,
    product_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    UNIQUE KEY unique_wishlist_item (user_id, product_id),
    INDEX idx_user_id (user_id)
);

-- Wallet table
CREATE TABLE wallet (
    wallet_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(36) UNIQUE NOT NULL,
    balance DECIMAL(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Wallet transactions table
CREATE TABLE wallet_transactions (
    transaction_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    transaction_type ENUM('credit', 'debit') NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    balance_after DECIMAL(10, 2) NOT NULL,
    description VARCHAR(255),
    reference_type ENUM('order', 'refund', 'cashback', 'referral', 'admin_adjustment'),
    reference_id VARCHAR(36),
    status ENUM('pending', 'completed', 'failed') DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_transaction_type (transaction_type),
    INDEX idx_created_at (created_at)
);

-- Promo codes table
CREATE TABLE promocodes (
    code_id INT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    discount_type ENUM('percentage', 'fixed') NOT NULL,
    discount_value DECIMAL(10, 2) NOT NULL,
    min_order_amount DECIMAL(10, 2) DEFAULT 0,
    max_discount_amount DECIMAL(10, 2),
    usage_limit INT,
    used_count INT DEFAULT 0,
    user_limit INT DEFAULT 1,
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP NOT NULL,
    status ENUM('active', 'inactive', 'expired') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_code (code),
    INDEX idx_status (status),
    INDEX idx_valid_dates (valid_from, valid_until)
);

-- Admin users table
CREATE TABLE admin_users (
    admin_id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    role ENUM('super_admin', 'product_manager', 'order_manager', 'customer_support') NOT NULL,
    permissions JSON,
    last_login TIMESTAMP NULL,
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role)
);

-- Activity logs table
CREATE TABLE activity_logs (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    user_type ENUM('user', 'admin') NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    action VARCHAR(100) NOT NULL,
    table_name VARCHAR(100),
    record_id VARCHAR(36),
    old_values JSON,
    new_values JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_type_id (user_type, user_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
);

-- Contact messages table
CREATE TABLE contact_messages (
    message_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status ENUM('new', 'in_progress', 'resolved') DEFAULT 'new',
    admin_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_email (email),
    INDEX idx_created_at (created_at)
);

-- FAQ table
CREATE TABLE faq (
    faq_id INT PRIMARY KEY AUTO_INCREMENT,
    question VARCHAR(500) NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(100),
    sort_order INT DEFAULT 0,
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_status (status),
    FULLTEXT idx_question_answer (question, answer)
);

-- Insert default data

-- Insert default categories
INSERT INTO categories (category_name, description, status) VALUES
('Nuts', 'quality nuts ', 'active'),
('Seeds', 'utritious seeds for a balanced diet', 'active'),
('Coffee', ' coffee beans and blends', 'active'),
('Honey', 'natural honey ', 'active');

-- Insert sample products
INSERT INTO products (product_name, description, category_id, price, discount_price, sku, is_featured) VALUES
('Premium Almonds', 'rich in protein and healthy fats', 1, 899.00, 799.00, 'ALM001', TRUE),
('Roasted Cashews', 'cashews with a rich, buttery flavor', 1, 1299.00, 1199.00, 'CSH001', TRUE),
('Chia Seeds', ' with omega-3 fatty acids', 2, 299.00, 249.00, 'CHI001', FALSE),
('Arabica Coffee', 'coffee beans from Karnataka', 3, 599.00, 549.00, 'COF001', TRUE),
('Manuka Honey', 'Premium Manuka honey with ', 4, 1299.00, 1199.00, 'HON001', TRUE);

-- Insert product images
INSERT INTO product_images (product_id, image_url, alt_text, is_primary) VALUES
(1, '/static/uploads/products/almonds1.jpg', 'Premium Almonds', TRUE),
(2, '/static/uploads/products/cashews1.jpg', 'Roasted Cashews', TRUE),
(3, '/static/uploads/products/chia1.jpg', 'Chia Seeds', TRUE),
(4, '/static/uploads/products/coffee1.jpg', 'Arabica Coffee', TRUE),
(5, '/static/uploads/products/honey1.jpg', 'Manuka Honey', TRUE);

-- Insert default admin user (username: admin, password: admin123)
INSERT INTO admin_users (admin_id, username, email, password_hash, full_name, role, status) VALUES
(UUID(), 'admin', 'admin@ecommerce.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewJB1FfpOG3TejBa', 'System Administrator', 'super_admin', 'active');

-- Insert sample FAQ
INSERT INTO faq (question, answer, category) VALUES
('What are your delivery charges?', 'We offer free delivery on orders above ₹500. For orders below ₹500, delivery charges are ₹50.', 'Delivery'),
('How long does delivery take?', 'We typically deliver within 2-5 business days depending on your location.', 'Delivery'),
('Do you accept returns?', 'Yes, we accept returns within 7 days of delivery for unopened products.', 'Returns'),
('Are your products organic?', 'Most of our products are organic and naturally sourced. Check individual product descriptions for details.', 'Products');

-- Create triggers for wallet balance updates
DELIMITER //

CREATE TRIGGER update_wallet_balance 
AFTER INSERT ON wallet_transactions
FOR EACH ROW
BEGIN
    IF NEW.transaction_type = 'credit' THEN
        UPDATE wallet SET balance = balance + NEW.amount, updated_at = NOW() WHERE user_id = NEW.user_id;
    ELSE
        UPDATE wallet SET balance = balance - NEW.amount, updated_at = NOW() WHERE user_id = NEW.user_id;
    END IF;
END//

-- Create trigger to create wallet when user registers
CREATE TRIGGER create_user_wallet
AFTER INSERT ON users
FOR EACH ROW
BEGIN
    INSERT INTO wallet (user_id, balance) VALUES (NEW.user_id, 0.00);
END//

-- Create trigger to update inventory on order
CREATE TRIGGER update_inventory_on_order
AFTER INSERT ON order_items
FOR EACH ROW
BEGIN
    UPDATE inventory 
    SET reserved_quantity = reserved_quantity + NEW.quantity 
    WHERE product_id = NEW.product_id AND (variant_id = NEW.variant_id OR (variant_id IS NULL AND NEW.variant_id IS NULL));
END//

DELIMITER ;

-- Create indexes for better performance
CREATE INDEX idx_products_price ON products(price);
CREATE INDEX idx_products_discount_price ON products(discount_price);
CREATE INDEX idx_orders_total_amount ON orders(total_amount);
CREATE INDEX idx_reviews_created_at ON reviews(created_at);
CREATE INDEX idx_wallet_transactions_created_at ON wallet_transactions(created_at);

-- Add GST columns to products
ALTER TABLE products ADD COLUMN hsn_code VARCHAR(10);
ALTER TABLE products ADD COLUMN gst_rate DECIMAL(5,2) DEFAULT 5.00;
ALTER TABLE products ADD COLUMN tax_category VARCHAR(50) DEFAULT 'standard';

-- Add state code to addresses
ALTER TABLE addresses ADD COLUMN state_code VARCHAR(5);

-- Update orders table for tax breakdown
ALTER TABLE orders ADD COLUMN cgst_amount DECIMAL(10,2) DEFAULT 0;
ALTER TABLE orders ADD COLUMN sgst_amount DECIMAL(10,2) DEFAULT 0;
ALTER TABLE orders ADD COLUMN igst_amount DECIMAL(10,2) DEFAULT 0;
ALTER TABLE orders ADD COLUMN tax_rate DECIMAL(5,2) DEFAULT 0;

-- Tax configuration table
CREATE TABLE tax_rates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(100),
    hsn_code VARCHAR(10),
    gst_rate DECIMAL(5,2),
    description VARCHAR(255),
    effective_from DATE DEFAULT CURRENT_DATE,
    status ENUM('active', 'inactive') DEFAULT 'active'
);

-- Insert GST rates for your products
INSERT INTO tax_rates (category_name, hsn_code, gst_rate, description) VALUES
('nuts_raw', '0801', 5.00, 'Raw nuts and dry fruits'),
('nuts_processed', '0801', 12.00, 'Roasted, salted, flavored nuts'),
('seeds', '1207', 5.00, 'Oil seeds and oleaginous fruits'),
('coffee_beans', '0901', 5.00, 'Coffee beans unroasted'),
('coffee_instant', '0901', 12.00, 'Instant coffee and extracts'),
('honey', '0409', 0.00, 'Natural honey (exempted)');
INSERT INTO promocodes (code, description, discount_type, discount_value, min_order_amount, max_discount_amount, usage_limit, valid_from, valid_until, status) VALUES
('WELCOME10', 'Welcome discount - 10% off on first order', 'percentage', 10.00, 100.00, 200.00, 1000, NOW(), DATE_ADD(NOW(), INTERVAL 6 MONTH), 'active'),
('SAVE50', 'Flat ₹50 off on orders above ₹300', 'fixed', 50.00, 300.00, 50.00, 500, NOW(), DATE_ADD(NOW(), INTERVAL 3 MONTH), 'active'),
('NUTS20', '20% off on all nuts products', 'percentage', 20.00, 200.00, 500.00, 200, NOW(), DATE_ADD(NOW(), INTERVAL 1 MONTH), 'active'),
('FREESHIP', 'Free shipping on all orders', 'fixed', 50.00, 0.00, 50.00, NULL, NOW(), DATE_ADD(NOW(), INTERVAL 12 MONTH), 'active'),
('BULK15', '15% off on orders above ₹1000', 'percentage', 15.00, 1000.00, 1000.00, 100, NOW(), DATE_ADD(NOW(), INTERVAL 2 MONTH), 'active'),
('FIRST100', 'First time customer - ₹100 off', 'fixed', 100.00, 500.00, 100.00, 1, NOW(), DATE_ADD(NOW(), INTERVAL 3 MONTH), 'active');

-- Also update existing products with proper HSN codes and GST rates if not already done
UPDATE products SET hsn_code = '0801', gst_rate = 5.00 WHERE category_id = 1 AND hsn_code IS NULL;
UPDATE products SET hsn_code = '1207', gst_rate = 5.00 WHERE category_id = 2 AND hsn_code IS NULL;
UPDATE products SET hsn_code = '0901', gst_rate = 5.00 WHERE category_id = 3 AND hsn_code IS NULL;
UPDATE products SET hsn_code = '0409', gst_rate = 0.00 WHERE category_id = 4 AND hsn_code IS NULL;
-- Update existing products with HSN and GST
UPDATE products SET hsn_code = '0801', gst_rate = 5.00, tax_category = 'nuts_raw' WHERE category_id = 1;
UPDATE products SET hsn_code = '1207', gst_rate = 5.00, tax_category = 'seeds' WHERE category_id = 2;
UPDATE products SET hsn_code = '0901', gst_rate = 5.00, tax_category = 'coffee_beans' WHERE category_id = 3;
UPDATE products SET hsn_code = '0409', gst_rate = 0.00, tax_category = 'honey' WHERE category_id = 4;