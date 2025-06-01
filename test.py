#!/usr/bin/env python3
"""
Script to fix product image URLs in the database
This will update the image URLs to use working placeholder images
"""

import mysql.connector
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Sanidhya@28',
    'database': 'ecommerce_db'
}

def fix_product_images():
    """Update product image URLs to use working placeholder images"""
    
    # Image URLs for different product categories
    image_urls = {
        'almonds': 'https://images.unsplash.com/photo-1508747703725-719777637510?w=400&h=300&fit=crop&crop=center',
        'cashews': 'https://images.unsplash.com/photo-1566027381013-cb5cfede1e6b?w=400&h=300&fit=crop&crop=center',
        'chia': 'https://images.unsplash.com/photo-1602500873309-7ad5bfbf94b6?w=400&h=300&fit=crop&crop=center',
        'coffee': 'https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=400&h=300&fit=crop&crop=center',
        'honey': 'https://images.unsplash.com/photo-1558642084-fd7f09ba3c56?w=400&h=300&fit=crop&crop=center'
    }
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("Fixing product image URLs...")
        
        # Update product images
        updates = [
            (image_urls['almonds'], 1),  # Premium Almonds
            (image_urls['cashews'], 2),  # Roasted Cashews
            (image_urls['chia'], 3),     # Chia Seeds
            (image_urls['coffee'], 4),   # Arabica Coffee
            (image_urls['honey'], 5),    # Manuka Honey
        ]
        
        for image_url, product_id in updates:
            cursor.execute("""
                UPDATE product_images 
                SET image_url = %s 
                WHERE product_id = %s
            """, (image_url, product_id))
            print(f"Updated image for product ID {product_id}")
        
        conn.commit()
        print("✅ Product images updated successfully!")
        
        # Verify the updates
        cursor.execute("""
            SELECT p.product_name, pi.image_url 
            FROM products p 
            JOIN product_images pi ON p.product_id = pi.product_id
        """)
        
        results = cursor.fetchall()
        print("\nUpdated product images:")
        for product_name, image_url in results:
            print(f"  - {product_name}: {image_url}")
            
    except mysql.connector.Error as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def add_sample_products():
    """Add more sample products if needed"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check if we need more products
        cursor.execute("SELECT COUNT(*) FROM products")
        product_count = cursor.fetchone()[0]
        
        if product_count < 10:
            print("Adding more sample products...")
            
            sample_products = [
                ('Organic Walnuts', 'Premium organic walnuts rich in omega-3 fatty acids', 1, 1299.00, 1199.00, 'WAL001', True),
                ('Pumpkin Seeds', 'Roasted pumpkin seeds perfect for healthy snacking', 2, 399.00, 349.00, 'PUM001', False),
                ('Sunflower Seeds', 'Natural sunflower seeds packed with nutrients', 2, 299.00, 249.00, 'SUN001', False),
                ('Ethiopian Coffee', 'Single origin Ethiopian coffee with floral notes', 3, 799.00, 699.00, 'COF002', True),
                ('Wild Honey', 'Pure wild honey collected from forest areas', 4, 899.00, 799.00, 'HON002', False),
            ]
            
            image_urls = [
                'https://images.unsplash.com/photo-1553975166-44e92c4e1aa8?w=400&h=300&fit=crop&crop=center',  # Walnuts
                'https://images.unsplash.com/photo-1602943148592-32b9e8f3e1a9?w=400&h=300&fit=crop&crop=center',  # Pumpkin seeds
                'https://images.unsplash.com/photo-1528803721862-b039f45b8dc5?w=400&h=300&fit=crop&crop=center',  # Sunflower seeds
                'https://images.unsplash.com/photo-1497515114629-f71d768fd07c?w=400&h=300&fit=crop&crop=center',  # Ethiopian coffee
                'https://images.unsplash.com/photo-1587049332474-4a1fe0c55c3b?w=400&h=300&fit=crop&crop=center',  # Wild honey
            ]
            
            for i, (name, desc, cat_id, price, disc_price, sku, featured) in enumerate(sample_products):
                # Insert product
                cursor.execute("""
                    INSERT INTO products (product_name, description, category_id, price, discount_price, sku, is_featured, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', %s)
                """, (name, desc, cat_id, price, disc_price, sku, featured, datetime.now()))
                
                product_id = cursor.lastrowid
                
                # Insert product image
                cursor.execute("""
                    INSERT INTO product_images (product_id, image_url, alt_text, is_primary, created_at)
                    VALUES (%s, %s, %s, TRUE, %s)
                """, (product_id, image_urls[i], name, datetime.now()))
                
                print(f"Added product: {name}")
            
            conn.commit()
            print("✅ Sample products added successfully!")
        else:
            print("Sufficient products already exist.")
            
    except mysql.connector.Error as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🔧 Fixing E-commerce Database Issues...")
    print("=" * 40)
    
    # Fix existing product images
    fix_product_images()
    
    print("\n" + "=" * 40)
    
    # Add more sample products
    add_sample_products()
    
    print("\n✅ All fixes completed!")
    print("\nYou can now run your Flask app without image 404 errors.")