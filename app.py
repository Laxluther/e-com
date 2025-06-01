from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import mysql.connector
from datetime import datetime, timedelta
import jwt
import os
import uuid
import json
from functools import wraps
from decimal import Decimal
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['JWT_SECRET_KEY'] = 'your-jwt-secret-key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Sanidhya@28',
    'database': 'ecommerce_db'
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        try:
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
        except:
            return jsonify({'message': 'Token is invalid'}), 401
            
        return f(current_user_id, *args, **kwargs)
    return decorated
def generate_gst_invoice_data(order_id):
    """Generate GST compliant invoice data"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get order with tax details
        cursor.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
        order = cursor.fetchone()
        
        # Get order items with HSN codes
        cursor.execute("""
            SELECT oi.*, p.hsn_code, p.gst_rate 
            FROM order_items oi 
            JOIN products p ON oi.product_id = p.product_id 
            WHERE oi.order_id = %s
        """, (order_id,))
        items = cursor.fetchall()
        
        # Parse addresses
        shipping_address = json.loads(order['shipping_address'])
        customer_state_code = get_state_code_from_state_name(shipping_address['state'])
        
        invoice_data = {
            'invoice_number': f"INV-{order['order_number']}",
            'invoice_date': order['created_at'].strftime('%Y-%m-%d'),
            'order_number': order['order_number'],
            'customer': {
                'name': shipping_address['full_name'],
                'address': shipping_address,
                'state_code': customer_state_code
            },
            'seller': {
                'name': 'Lorem ipsum',
                'gstin': app.config.get('BUSINESS_GSTIN'),
                'state_code': app.config.get('BUSINESS_STATE_CODE')
            },
            'items': items,
            'tax_summary': {
                'cgst': order['cgst_amount'],
                'sgst': order['sgst_amount'], 
                'igst': order['igst_amount']
            },
            'totals': {
                'subtotal': order['subtotal'],
                'total_tax': order['tax_amount'],
                'grand_total': order['total_amount']
            }
        }
        
        return invoice_data
    
    finally:
        cursor.close()
        conn.close()
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Admin access required', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def calculate_product_wise_gst(cart_items, customer_state_code):
    """Calculate GST for each product and total"""
    business_state = app.config.get('BUSINESS_STATE_CODE', 'MH')
    
    tax_breakdown = {
        'items': [],
        'total_cgst': 0,
        'total_sgst': 0, 
        'total_igst': 0,
        'total_tax': 0,
        'subtotal': 0
    }
    
    for item in cart_items:
        item_price = float(item.get('discount_price', item.get('price', 0)))
        quantity = item.get('quantity', 1)
        gst_rate = float(item.get('gst_rate', 5.0))
        item_total = item_price * quantity
        
        # Calculate tax based on delivery location
        if customer_state_code == business_state:
            # Intra-state: CGST + SGST
            cgst = (item_total * gst_rate / 2) / 100
            sgst = (item_total * gst_rate / 2) / 100
            igst = 0
        else:
            # Inter-state: IGST
            cgst = 0
            sgst = 0
            igst = (item_total * gst_rate) / 100
        
        item_tax = {
            'product_name': item.get('product_name'),
            'hsn_code': item.get('hsn_code'),
            'quantity': quantity,
            'unit_price': item_price,
            'item_total': item_total,
            'gst_rate': gst_rate,
            'cgst': round(cgst, 2),
            'sgst': round(sgst, 2),
            'igst': round(igst, 2),
            'total_tax': round(cgst + sgst + igst, 2)
        }
        
        tax_breakdown['items'].append(item_tax)
        tax_breakdown['total_cgst'] += cgst
        tax_breakdown['total_sgst'] += sgst
        tax_breakdown['total_igst'] += igst
        tax_breakdown['subtotal'] += item_total
    
    tax_breakdown['total_tax'] = tax_breakdown['total_cgst'] + tax_breakdown['total_sgst'] + tax_breakdown['total_igst']
    
    # Round totals
    for key in ['total_cgst', 'total_sgst', 'total_igst', 'total_tax']:
        tax_breakdown[key] = round(tax_breakdown[key], 2)
    
    return tax_breakdown

def calculate_order_totals(cart_items, customer_state):
    """Calculate order totals with GST - Fixed version"""
    customer_state_code = get_state_code_from_state_name(customer_state) if isinstance(customer_state, str) else customer_state
    business_state = app.config.get('BUSINESS_STATE_CODE', 'MH')
    
    subtotal = 0
    total_cgst = 0
    total_sgst = 0
    total_igst = 0
    total_tax_rate = 0
    
    for item in cart_items:
        item_price = float(item['discount_price']) if item['discount_price'] else float(item['price'])
        quantity = item['quantity']
        gst_rate = float(item.get('gst_rate', 5.0))
        item_total = item_price * quantity
        
        subtotal += item_total
        total_tax_rate += gst_rate * quantity
        
        # Calculate GST
        if customer_state_code == business_state:
            # Intra-state: CGST + SGST
            cgst = (item_total * gst_rate / 2) / 100
            sgst = (item_total * gst_rate / 2) / 100
            total_cgst += cgst
            total_sgst += sgst
        else:
            # Inter-state: IGST
            igst = (item_total * gst_rate) / 100
            total_igst += igst
    
    # Calculate shipping
    shipping_amount = 0 if subtotal >= 500 else 50
    
    # Calculate discount (if any promo code applied)
    discount_amount = 0
    if session.get('applied_promocode'):
        promo = session['applied_promocode']
        if subtotal >= promo['min_order_amount']:
            if promo['discount_type'] == 'percentage':
                discount_amount = subtotal * (promo['discount_value'] / 100)
                if promo['max_discount_amount'] > 0:
                    discount_amount = min(discount_amount, promo['max_discount_amount'])
            else:
                discount_amount = min(promo['discount_value'], subtotal)
    
    tax_amount = total_cgst + total_sgst + total_igst
    total_amount = subtotal + tax_amount + shipping_amount - discount_amount
    
    # Calculate average tax rate
    total_items = sum(item['quantity'] for item in cart_items)
    avg_tax_rate = (total_tax_rate / total_items) if total_items > 0 else 0
    
    return {
        'subtotal': round(subtotal, 2),
        'tax_amount': round(tax_amount, 2),
        'cgst_amount': round(total_cgst, 2),
        'sgst_amount': round(total_sgst, 2), 
        'igst_amount': round(total_igst, 2),
        'shipping_amount': round(shipping_amount, 2),
        'discount_amount': round(discount_amount, 2),
        'total_amount': round(total_amount, 2),
        'avg_tax_rate': round(avg_tax_rate, 2)
    }

def get_state_code_from_state_name(state_input):
    """Convert state name to state code or return as-is if already a code"""
    if not state_input:
        return 'MH'
    
    # If it's already a 2-letter code, return it
    if len(state_input) == 2 and state_input.isupper():
        return state_input
    
    # State mapping for conversion
    state_mapping = {
        'Andhra Pradesh': 'AP', 'Arunachal Pradesh': 'AR', 'Assam': 'AS', 'Bihar': 'BR',
        'Chhattisgarh': 'CG', 'Goa': 'GA', 'Gujarat': 'GJ', 'Haryana': 'HR', 
        'Himachal Pradesh': 'HP', 'Jharkhand': 'JH', 'Karnataka': 'KA', 'Kerala': 'KL',
        'Madhya Pradesh': 'MP', 'Maharashtra': 'MH', 'Manipur': 'MN', 'Meghalaya': 'ML',
        'Mizoram': 'MZ', 'Nagaland': 'NL', 'Odisha': 'OR', 'Punjab': 'PB', 
        'Rajasthan': 'RJ', 'Sikkim': 'SK', 'Tamil Nadu': 'TN', 'Telangana': 'TS',
        'Tripura': 'TR', 'Uttar Pradesh': 'UP', 'Uttarakhand': 'UK', 'West Bengal': 'WB',
        'Delhi': 'DL', 'Jammu and Kashmir': 'JK'
    }
    
    return state_mapping.get(state_input, 'MH')

def get_state_code_from_state_name(state_name):
    """Convert state name to state code"""
    state_mapping = {v: k for k, v in app.config.get('INDIAN_STATES', {}).items()}
    return state_mapping.get(state_name, 'MH')  # Default to Maharashtra

def calculate_product_wise_gst(cart_items, customer_state_code):
    """Calculate GST for each product and total"""
    business_state = app.config.get('BUSINESS_STATE_CODE', 'MH')
    
    tax_breakdown = {
        'items': [],
        'total_cgst': 0,
        'total_sgst': 0, 
        'total_igst': 0,
        'total_tax': 0,
        'subtotal': 0
    }
    
    for item in cart_items:
        item_price = float(item.get('discount_price', item.get('price', 0)))
        quantity = item.get('quantity', 1)
        gst_rate = float(item.get('gst_rate', 5.0))
        item_total = item_price * quantity
        
        # Calculate tax based on delivery location
        if customer_state_code == business_state:
            # Intra-state: CGST + SGST
            cgst = (item_total * gst_rate / 2) / 100
            sgst = (item_total * gst_rate / 2) / 100
            igst = 0
        else:
            # Inter-state: IGST
            cgst = 0
            sgst = 0
            igst = (item_total * gst_rate) / 100
        
        item_tax = {
            'product_name': item.get('product_name'),
            'hsn_code': item.get('hsn_code'),
            'quantity': quantity,
            'unit_price': item_price,
            'item_total': item_total,
            'gst_rate': gst_rate,
            'cgst': round(cgst, 2),
            'sgst': round(sgst, 2),
            'igst': round(igst, 2),
            'total_tax': round(cgst + sgst + igst, 2)
        }
        
        tax_breakdown['items'].append(item_tax)
        tax_breakdown['total_cgst'] += cgst
        tax_breakdown['total_sgst'] += sgst
        tax_breakdown['total_igst'] += igst
        tax_breakdown['subtotal'] += item_total
    
    tax_breakdown['total_tax'] = tax_breakdown['total_cgst'] + tax_breakdown['total_sgst'] + tax_breakdown['total_igst']
    
    # Round totals
    for key in ['total_cgst', 'total_sgst', 'total_igst', 'total_tax']:
        tax_breakdown[key] = round(tax_breakdown[key], 2)
    
    return tax_breakdown
def calculate_order_totals(cart_items, customer_state):
    """Calculate order totals with GST"""
    customer_state_code = get_state_code_from_state_name(customer_state)
    business_state = app.config.get('BUSINESS_STATE_CODE', 'MH')
    
    subtotal = 0
    total_cgst = 0
    total_sgst = 0
    total_igst = 0
    total_tax_rate = 0
    
    for item in cart_items:
        item_price = float(item['discount_price']) if item['discount_price'] else float(item['price'])
        quantity = item['quantity']
        gst_rate = float(item.get('gst_rate', 5.0))
        item_total = item_price * quantity
        
        subtotal += item_total
        total_tax_rate += gst_rate * quantity  # For average calculation
        
        # Calculate GST
        if customer_state_code == business_state:
            # Intra-state: CGST + SGST
            cgst = (item_total * gst_rate / 2) / 100
            sgst = (item_total * gst_rate / 2) / 100
            total_cgst += cgst
            total_sgst += sgst
        else:
            # Inter-state: IGST
            igst = (item_total * gst_rate) / 100
            total_igst += igst
    
    # Calculate shipping
    shipping_amount = 0 if subtotal >= 500 else 50
    
    # Calculate discount (if any promo code applied)
    discount_amount = 0
    if session.get('applied_promocode'):
        promo = session['applied_promocode']
        if subtotal >= promo['min_order_amount']:
            if promo['discount_type'] == 'percentage':
                discount_amount = subtotal * (promo['discount_value'] / 100)
                if promo['max_discount_amount'] > 0:
                    discount_amount = min(discount_amount, promo['max_discount_amount'])
            else:
                discount_amount = promo['discount_value']
    
    tax_amount = total_cgst + total_sgst + total_igst
    total_amount = subtotal + tax_amount + shipping_amount - discount_amount
    
    # Calculate average tax rate
    total_items = sum(item['quantity'] for item in cart_items)
    avg_tax_rate = (total_tax_rate / total_items) if total_items > 0 else 0
    
    return {
        'subtotal': round(subtotal, 2),
        'tax_amount': round(tax_amount, 2),
        'cgst_amount': round(total_cgst, 2),
        'sgst_amount': round(total_sgst, 2), 
        'igst_amount': round(total_igst, 2),
        'shipping_amount': round(shipping_amount, 2),
        'discount_amount': round(discount_amount, 2),
        'total_amount': round(total_amount, 2),
        'avg_tax_rate': round(avg_tax_rate, 2)
    }

def generate_order_number():
    """Generate unique order number"""
    from datetime import datetime
    import random
    
    date_part = datetime.now().strftime('%Y%m%d')
    random_part = random.randint(1000, 9999)
    return f"ORD{date_part}{random_part}"

def process_payment(order_id, payment_method, amount, cursor, conn):
    """Process payment based on method"""
    
    if payment_method == 'cod':
        # Cash on Delivery - No immediate payment processing
        cursor.execute("""
            UPDATE orders 
            SET payment_status = 'pending', status = 'confirmed'
            WHERE order_id = %s
        """, (order_id,))
        
        # Add tracking update
        cursor.execute("""
            INSERT INTO order_tracking (order_id, status, message, created_at)
            VALUES (%s, %s, %s, %s)
        """, (order_id, 'confirmed', 'Order confirmed. Will be processed soon.', datetime.now()))
        
        return {'success': True, 'message': 'COD order confirmed'}
    
    elif payment_method == 'wallet':
        # Wallet payment - Deduct from wallet
        try:
            # Get current balance
            cursor.execute("SELECT balance FROM wallet WHERE user_id = %s", (session['user_id'],))
            wallet_data = cursor.fetchone()
            current_balance = float(wallet_data['balance']) if wallet_data else 0.0
            
            if current_balance < amount:
                return {'success': False, 'message': 'Insufficient wallet balance'}
            
            # Create debit transaction
            transaction_id = str(uuid.uuid4())
            new_balance = current_balance - amount
            
            cursor.execute("""
                INSERT INTO wallet_transactions 
                (transaction_id, user_id, transaction_type, amount, balance_after, 
                 description, reference_type, reference_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (transaction_id, session['user_id'], 'debit', amount, new_balance,
                  f'Payment for order', 'order', order_id, datetime.now()))
            
            # Update wallet balance
            cursor.execute("""
                UPDATE wallet SET balance = %s, updated_at = %s 
                WHERE user_id = %s
            """, (new_balance, datetime.now(), session['user_id']))
            
            # Update order payment status
            cursor.execute("""
                UPDATE orders 
                SET payment_status = 'completed', status = 'confirmed'
                WHERE order_id = %s
            """, (order_id,))
            
            # Add tracking update
            cursor.execute("""
                INSERT INTO order_tracking (order_id, status, message, created_at)
                VALUES (%s, %s, %s, %s)
            """, (order_id, 'confirmed', 'Payment completed. Order confirmed.', datetime.now()))
            
            return {'success': True, 'message': 'Wallet payment successful'}
            
        except Exception as e:
            print(f"Wallet payment error: {e}")
            return {'success': False, 'message': 'Wallet payment failed'}
    
    elif payment_method == 'online':
        # Online payment - For now, mark as pending (implement gateway later)
        cursor.execute("""
            UPDATE orders 
            SET payment_status = 'pending', status = 'pending'
            WHERE order_id = %s
        """, (order_id,))
        
        return {'success': True, 'message': 'Online payment initiated'}
    
    else:
        return {'success': False, 'message': 'Invalid payment method'}

def send_order_confirmation_email(order_id, order_number, user_id):
   
    print(f"Order confirmation email sent for order {order_number} to user {user_id}")
    # TODO
    pass
def check_and_reserve_inventory(product_id, quantity):
    """Check if inventory is available and reserve it"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check current stock
        cursor.execute("""
            SELECT quantity, reserved_quantity 
            FROM inventory 
            WHERE product_id = %s
        """, (product_id,))
        
        stock_data = cursor.fetchone()
        if not stock_data:
            return False, "Product not found in inventory"
        
        available_stock = stock_data[0] - stock_data[1]  # total - reserved
        
        if available_stock < quantity:
            return False, f"Only {available_stock} units available"
        
        return True, "Stock available"
    
    finally:
        cursor.close()
        conn.close()

# ============ MAIN ROUTES ============

@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get featured products
        cursor.execute("""
            SELECT p.*, 
                   (SELECT pi.image_url FROM product_images pi WHERE pi.product_id = p.product_id LIMIT 1) as image_url
            FROM products p 
            WHERE p.is_featured = 1 AND p.status = 'active'
            ORDER BY p.created_at DESC
            LIMIT 8
        """)
        featured_products = cursor.fetchall()
        
        # Get categories
        cursor.execute("SELECT * FROM categories WHERE parent_id IS NULL AND status = 'active'")
        categories = cursor.fetchall()
        
        return render_template('home.html', products=featured_products, categories=categories)
    
    except Exception as e:
        print(f"Error in home route: {e}")
        return render_template('home.html', products=[], categories=[])
    
    finally:
        cursor.close()
        conn.close()

@app.route('/products')
def products():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        category_id = request.args.get('category')
        search_query = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        per_page = 12
        offset = (page - 1) * per_page
        
        # Build query
        query = """
            SELECT p.*, 
                   (SELECT pi.image_url FROM product_images pi WHERE pi.product_id = p.product_id LIMIT 1) as image_url,
                   c.category_name
            FROM products p 
            LEFT JOIN categories c ON p.category_id = c.category_id
            WHERE p.status = 'active'
        """
        
        params = []
        if category_id:
            query += " AND p.category_id = %s"
            params.append(category_id)
        
        if search_query:
            query += " AND (p.product_name LIKE %s OR p.description LIKE %s)"
            params.extend([f'%{search_query}%', f'%{search_query}%'])
        
        query += " ORDER BY p.created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        
        cursor.execute(query, params)
        products_list = cursor.fetchall()
        
        # Get categories for filter
        cursor.execute("SELECT * FROM categories WHERE status = 'active'")
        categories = cursor.fetchall()
        
        return render_template('products.html', products=products_list, categories=categories, 
                             current_category=category_id, search_query=search_query)
    
    except Exception as e:
        print(f"Error in products route: {e}")
        return render_template('products.html', products=[], categories=[], 
                             current_category=None, search_query='')
    
    finally:
        cursor.close()
        conn.close()

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get product details
        cursor.execute("""
            SELECT p.*, c.category_name 
            FROM products p 
            JOIN categories c ON p.category_id = c.category_id 
            WHERE p.product_id = %s AND p.status = 'active'
        """, (product_id,))
        product = cursor.fetchone()
        
        if not product:
            flash('Product not found', 'error')
            return redirect(url_for('products'))
        
        # Get product images
        cursor.execute("SELECT * FROM product_images WHERE product_id = %s", (product_id,))
        images = cursor.fetchall()
        
        # Get product variants
        cursor.execute("SELECT * FROM product_variants WHERE product_id = %s", (product_id,))
        variants = cursor.fetchall()
        
        # Get reviews
        cursor.execute("""
            SELECT r.*, u.first_name, u.last_name 
            FROM reviews r 
            JOIN users u ON r.user_id = u.user_id 
            WHERE r.product_id = %s AND r.status = 'approved'
            ORDER BY r.created_at DESC
        """, (product_id,))
        reviews = cursor.fetchall()
        
        return render_template('product_detail.html', product=product, images=images, 
                             variants=variants, reviews=reviews)
    
    except Exception as e:
        print(f"Error in product_detail route: {e}")
        flash('Error loading product', 'error')
        return redirect(url_for('products'))
    
    finally:
        cursor.close()
        conn.close()

# ============ AUTH ROUTES ============

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone = request.form['phone']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if user exists
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('Email already registered', 'error')
                return render_template('register.html')
            
            # Create user
            user_id = str(uuid.uuid4())
            hashed_password = generate_password_hash(password)
            
            cursor.execute("""
                INSERT INTO users (user_id, email, password_hash, first_name, last_name, phone, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, email, hashed_password, first_name, last_name, phone, datetime.now()))
            
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        
        except Exception as e:
            conn.rollback()
            print(f"Error in register: {e}")
            flash('Registration failed. Please try again.', 'error')
        
        finally:
            cursor.close()
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT * FROM users WHERE email = %s AND status = 'active'", (email,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                # Create JWT token
                token = jwt.encode({
                    'user_id': user['user_id'],
                    'exp': datetime.utcnow() + timedelta(hours=24)
                }, app.config['JWT_SECRET_KEY'])
                
                session['user_id'] = user['user_id']
                session['user_name'] = f"{user['first_name']} {user['last_name']}"
                session['token'] = token
                
                flash('Login successful!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid email or password', 'error')
        
        except Exception as e:
            print(f"Error in login: {e}")
            flash('Login failed. Please try again.', 'error')
        
        finally:
            cursor.close()
            conn.close()
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('home'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please login to view profile', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get user details
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (session['user_id'],))
        user = cursor.fetchone()
        
        # Get user addresses
        cursor.execute("SELECT * FROM addresses WHERE user_id = %s ORDER BY is_default DESC", (session['user_id'],))
        addresses = cursor.fetchall()
        
        return render_template('profile.html', user=user, addresses=addresses)
    
    except Exception as e:
        print(f"Error in profile route: {e}")
        flash('Error loading profile', 'error')
        return redirect(url_for('home'))
    
    finally:
        cursor.close()
        conn.close()

@app.route('/profile/edit', methods=['POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    phone = request.form['phone']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE users 
            SET first_name = %s, last_name = %s, phone = %s, updated_at = %s
            WHERE user_id = %s
        """, (first_name, last_name, phone, datetime.now(), session['user_id']))
        
        conn.commit()
        session['user_name'] = f"{first_name} {last_name}"  # Update session
        flash('Profile updated successfully!', 'success')
    
    except Exception as e:
        conn.rollback()
        print(f"Error updating profile: {e}")
        flash('Error updating profile', 'error')
    
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('profile'))

@app.route('/add_address', methods=['POST'])
def add_address():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    full_name = request.form['full_name']
    phone = request.form['phone']
    address_line1 = request.form['address_line1']
    address_line2 = request.form.get('address_line2', '')
    city = request.form['city']
    state = request.form['state']
    postal_code = request.form['postal_code']
    is_default = request.form.get('is_default') == 'on'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if is_default:
            cursor.execute("UPDATE addresses SET is_default = 0 WHERE user_id = %s", (session['user_id'],))
        
        cursor.execute("""
            INSERT INTO addresses 
            (user_id, full_name, phone, address_line1, address_line2, city, state, postal_code, is_default, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (session['user_id'], full_name, phone, address_line1, address_line2, 
              city, state, postal_code, is_default, datetime.now()))
        
        conn.commit()
        flash('Address added successfully!', 'success')
    
    except Exception as e:
        conn.rollback()
        print(f"Error adding address: {e}")
        flash('Error adding address', 'error')
    
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('profile'))

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Please login to view cart', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT c.*, p.product_name, p.price, p.discount_price, 
                   (SELECT pi.image_url FROM product_images pi WHERE pi.product_id = p.product_id LIMIT 1) as image_url
            FROM cart c 
            JOIN products p ON c.product_id = p.product_id 
            WHERE c.user_id = %s
        """, (session['user_id'],))
        cart_items = cursor.fetchall()
        total = 0
        total_savings = 0
        
        for item in cart_items:
            price = float(item['price'])
            discount_price = float(item['discount_price']) if item['discount_price'] else price
            quantity = item['quantity']
            
            total += quantity * discount_price
            
            if item['discount_price']:
                total_savings += quantity * (price - discount_price)
        
        return render_template('cart.html', cart_items=cart_items, total=total, total_savings=total_savings)
    
    except Exception as e:
        print(f"Error in cart route: {e}")
        flash('Error loading cart', 'error')
        return redirect(url_for('home'))
    
    finally:
        cursor.close()
        conn.close()

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    variant_id = data.get('variant_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if item already in cart
        cursor.execute("""
            SELECT cart_id, quantity FROM cart 
            WHERE user_id = %s AND product_id = %s AND (variant_id = %s OR (variant_id IS NULL AND %s IS NULL))
        """, (session['user_id'], product_id, variant_id, variant_id))
        existing_item = cursor.fetchone()
        
        if existing_item:
            # Update quantity
            new_quantity = existing_item[1] + quantity
            cursor.execute("""
                UPDATE cart SET quantity = %s, updated_at = %s 
                WHERE cart_id = %s
            """, (new_quantity, datetime.now(), existing_item[0]))
        else:
            # Add new item
            cursor.execute("""
                INSERT INTO cart (user_id, product_id, variant_id, quantity, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (session['user_id'], product_id, variant_id, quantity, datetime.now()))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Item added to cart successfully'})
    
    except Exception as e:
        conn.rollback()
        print(f"Error adding to cart: {e}")
        return jsonify({'success': False, 'message': 'Error adding item to cart'})
    
    finally:
        cursor.close()
        conn.close()


@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        flash('Please login to checkout', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get cart items with GST details
        cursor.execute("""
            SELECT c.*, p.product_name, p.price, p.discount_price, p.gst_rate, p.hsn_code,
                   (SELECT pi.image_url FROM product_images pi WHERE pi.product_id = p.product_id LIMIT 1) as image_url
            FROM cart c 
            JOIN products p ON c.product_id = p.product_id 
            WHERE c.user_id = %s
        """, (session['user_id'],))
        cart_items = cursor.fetchall()
        
        if not cart_items:
            flash('Your cart is empty', 'error')
            return redirect(url_for('cart'))
        
        # Get addresses
        cursor.execute("SELECT * FROM addresses WHERE user_id = %s ORDER BY is_default DESC", (session['user_id'],))
        addresses = cursor.fetchall()
        
        # Default state for tax calculation
        default_state_code = 'MH'  # Maharashtra
        if addresses:
            default_address = next((addr for addr in addresses if addr['is_default']), addresses[0])
            default_state_code = get_state_code_from_state_name(default_address['state'])
        
        # Calculate order totals
        totals = calculate_order_totals(cart_items, default_state_code)
        
        # Calculate GST breakdown
        tax_breakdown = calculate_product_wise_gst(cart_items, default_state_code)
        
        # Get applied promocode info
        applied_promocode = session.get('applied_promocode')
        
        # Indian states for dropdown
        indian_states = {
            'AN': 'Andaman and Nicobar Islands', 'AP': 'Andhra Pradesh', 'AR': 'Arunachal Pradesh',
            'AS': 'Assam', 'BR': 'Bihar', 'CH': 'Chandigarh', 'CG': 'Chhattisgarh',
            'DN': 'Dadra and Nagar Haveli', 'DD': 'Daman and Diu', 'DL': 'Delhi',
            'GA': 'Goa', 'GJ': 'Gujarat', 'HR': 'Haryana', 'HP': 'Himachal Pradesh',
            'JK': 'Jammu and Kashmir', 'JH': 'Jharkhand', 'KA': 'Karnataka', 'KL': 'Kerala',
            'LD': 'Lakshadweep', 'MP': 'Madhya Pradesh', 'MH': 'Maharashtra', 'MN': 'Manipur',
            'ML': 'Meghalaya', 'MZ': 'Mizoram', 'NL': 'Nagaland', 'OR': 'Odisha',
            'PY': 'Puducherry', 'PB': 'Punjab', 'RJ': 'Rajasthan', 'SK': 'Sikkim',
            'TN': 'Tamil Nadu', 'TS': 'Telangana', 'TR': 'Tripura', 'UP': 'Uttar Pradesh',
            'UK': 'Uttarakhand', 'WB': 'West Bengal'
        }
        
        return render_template('checkout.html', 
                             cart_items=cart_items,
                             addresses=addresses,
                             subtotal=totals['subtotal'],
                             shipping_charge=totals['shipping_amount'],
                             tax_amount=totals['tax_amount'],
                             tax_breakdown=tax_breakdown,
                             discount_amount=totals['discount_amount'],
                             total_amount=totals['total_amount'],
                             applied_promocode=applied_promocode,
                             indian_states=indian_states)
    
    except Exception as e:
        print(f"Error in checkout route: {e}")
        flash('Error loading checkout', 'error')
        return redirect(url_for('cart'))
    
    finally:
        cursor.close()
        conn.close()

# Also fix the existing apply_promocode route to work with cart page
@app.route('/apply_promocode', methods=['POST'])
def apply_promocode():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    data = request.get_json()
    code = data.get('code', '').upper().strip()
    
    if not code:
        return jsonify({'success': False, 'message': 'Please enter a promocode'})
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Validate promocode
        cursor.execute("""
            SELECT * FROM promocodes 
            WHERE code = %s AND status = 'active' 
            AND valid_from <= NOW() AND valid_until >= NOW()
            AND (usage_limit IS NULL OR used_count < usage_limit)
        """, (code,))
        promocode = cursor.fetchone()
        
        if not promocode:
            return jsonify({'success': False, 'message': 'Invalid or expired promocode'})
        
        # Get cart items to calculate subtotal
        cursor.execute("""
            SELECT c.*, p.price, p.discount_price
            FROM cart c 
            JOIN products p ON c.product_id = p.product_id 
            WHERE c.user_id = %s
        """, (session['user_id'],))
        cart_items = cursor.fetchall()
        
        if not cart_items:
            return jsonify({'success': False, 'message': 'Cart is empty'})
        
        # Calculate subtotal
        subtotal = sum([
            (float(item['discount_price']) if item['discount_price'] else float(item['price'])) * item['quantity']
            for item in cart_items
        ])
        
        # Check minimum order amount
        min_order = float(promocode.get('min_order_amount') or 0)
        if subtotal < min_order:
            return jsonify({
                'success': False, 
                'message': f'Minimum order amount ₹{min_order} required for this promocode'
            })
        
        # Store promocode in session
        session['applied_promocode'] = {
            'code': promocode['code'],
            'discount_type': promocode['discount_type'],
            'discount_value': float(promocode['discount_value']),
            'min_order_amount': min_order,
            'max_discount_amount': float(promocode.get('max_discount_amount') or 0)
        }
        
        return jsonify({
            'success': True, 
            'message': f'Promocode {code} applied successfully!'
        })
    
    except Exception as e:
        print(f"Error applying promocode: {e}")
        return jsonify({'success': False, 'message': 'Error applying promocode'})
    
    finally:
        cursor.close()
        conn.close()

# Fix the calculate_product_wise_gst function 


@app.route('/wallet')
def wallet():
    if 'user_id' not in session:
        flash('Please login to view wallet', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT balance FROM wallet WHERE user_id = %s", (session['user_id'],))
        wallet_data = cursor.fetchone()
        balance = wallet_data['balance'] if wallet_data else 0.00
        
        cursor.execute("""
            SELECT * FROM wallet_transactions 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT 10
        """, (session['user_id'],))
        transactions = cursor.fetchall()
        
        return render_template('wallet.html', balance=balance, transactions=transactions)
    
    except Exception as e:
        print(f"Error in wallet route: {e}")
        flash('Error loading wallet', 'error')
        return redirect(url_for('home'))
    
    finally:
        cursor.close()
        conn.close()

@app.route('/add_money', methods=['POST'])
def add_money():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    amount = float(request.form.get('amount', 0))
    
    if amount <= 0:
        flash('Invalid amount', 'error')
        return redirect(url_for('wallet'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if wallet exists, create if not
        cursor.execute("SELECT balance FROM wallet WHERE user_id = %s", (session['user_id'],))
        wallet_data = cursor.fetchone()
        
        if not wallet_data:
            cursor.execute("INSERT INTO wallet (user_id, balance) VALUES (%s, %s)", 
                          (session['user_id'], amount))
            new_balance = amount
        else:
            new_balance = wallet_data[0] + amount
            cursor.execute("UPDATE wallet SET balance = %s WHERE user_id = %s", 
                          (new_balance, session['user_id']))
        
        # Add transaction record
        transaction_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO wallet_transactions 
            (transaction_id, user_id, transaction_type, amount, balance_after, description, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (transaction_id, session['user_id'], 'credit', amount, new_balance, 
              f'Money added to wallet', datetime.now()))
        
        conn.commit()
        flash(f'₹{amount} added to your wallet successfully!', 'success')
    
    except Exception as e:
        conn.rollback()
        print(f"Error adding money: {e}")
        flash('Error adding money to wallet', 'error')
    
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('wallet'))

@app.route('/orders')
def user_orders():
    if 'user_id' not in session:
        flash('Please login to view orders', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT o.*, COUNT(oi.item_id) as item_count
            FROM orders o 
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.user_id = %s 
            GROUP BY o.order_id
            ORDER BY o.created_at DESC
        """, (session['user_id'],))
        orders = cursor.fetchall()
        
        return render_template('orders.html', orders=orders)
    
    except Exception as e:
        print(f"Error in user_orders route: {e}")
        flash('Error loading orders', 'error')
        return redirect(url_for('home'))
    
    finally:
        cursor.close()
        conn.close()

@app.route('/orders/<order_id>')
def order_detail(order_id):
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT * FROM orders 
            WHERE order_id = %s AND user_id = %s
        """, (order_id, session['user_id']))
        order = cursor.fetchone()
        
        if not order:
            flash('Order not found', 'error')
            return redirect(url_for('user_orders'))
        
        cursor.execute("""
            SELECT oi.*, p.product_name,
                   (SELECT pi.image_url FROM product_images pi WHERE pi.product_id = p.product_id LIMIT 1) as image_url
            FROM order_items oi
            LEFT JOIN products p ON oi.product_id = p.product_id
            WHERE oi.order_id = %s
        """, (order_id,))
        order_items = cursor.fetchall()
        
        return render_template('order_detail.html', order=order, order_items=order_items)
    
    except Exception as e:
        print(f"Error in order_detail route: {e}")
        flash('Error loading order details', 'error')
        return redirect(url_for('user_orders'))
    
    finally:
        cursor.close()
        conn.close()

@app.route('/order-success/<order_id>')
def order_success(order_id):
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get order details
        cursor.execute("""
            SELECT * FROM orders 
            WHERE order_id = %s AND user_id = %s
        """, (order_id, session['user_id']))
        order = cursor.fetchone()
        
        if not order:
            flash('Order not found', 'error')
            return redirect(url_for('user_orders'))
        
        return render_template('order_success.html', order=order, timedelta=timedelta)
    
    except Exception as e:
        print(f"Error in order_success route: {e}")
        flash('Error loading order', 'error')
        return redirect(url_for('user_orders'))
    
    finally:
        cursor.close()
        conn.close()

@app.route('/track-order')
def track_order_page():
    return render_template('track_order.html')

@app.route('/api/track-order', methods=['POST'])
def api_track_order():
    data = request.get_json()
    order_number = data.get('order_number')
    phone = data.get('phone')
    
    if not order_number:
        return jsonify({'success': False, 'message': 'Order number is required'})
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT o.*, u.first_name, u.last_name, u.phone as user_phone
            FROM orders o 
            LEFT JOIN users u ON o.user_id = u.user_id 
            WHERE o.order_number = %s
        """, (order_number,))
        order = cursor.fetchone()
        
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'})
        
        if not session.get('user_id') and phone:
            if order.get('user_phone') != phone:
                return jsonify({'success': False, 'message': 'Invalid phone number'})
        
        cursor.execute("""
            SELECT oi.*, p.product_name,
                   (SELECT pi.image_url FROM product_images pi WHERE pi.product_id = p.product_id LIMIT 1) as image_url
            FROM order_items oi
            LEFT JOIN products p ON oi.product_id = p.product_id
            WHERE oi.order_id = %s
        """, (order['order_id'],))
        order_items = cursor.fetchall()
        
        cursor.execute("""
            SELECT * FROM order_tracking 
            WHERE order_id = %s 
            ORDER BY created_at ASC
        """, (order['order_id'],))
        tracking_history = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'order': order,
            'order_items': order_items,
            'tracking_history': tracking_history
        })
    
    except Exception as e:
        print(f"Error tracking order: {e}")
        return jsonify({'success': False, 'message': 'Error tracking order'})
    
    finally:
        cursor.close()
        conn.close()

@app.route('/wishlist')
def wishlist():
    if 'user_id' not in session:
        flash('Please login to view wishlist', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT w.*, p.product_name, p.price, p.discount_price,
                   (SELECT pi.image_url FROM product_images pi WHERE pi.product_id = p.product_id LIMIT 1) as image_url
            FROM wishlist w
            JOIN products p ON w.product_id = p.product_id
            WHERE w.user_id = %s AND p.status = 'active'
            ORDER BY w.created_at DESC
        """, (session['user_id'],))
        wishlist_items = cursor.fetchall()
        
        return render_template('wishlist.html', wishlist_items=wishlist_items)
    
    except Exception as e:
        print(f"Error in wishlist route: {e}")
        flash('Error loading wishlist', 'error')
        return redirect(url_for('home'))
    
    finally:
        cursor.close()
        conn.close()

@app.route('/wishlist/add', methods=['POST'])
def add_to_wishlist():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    data = request.get_json()
    product_id = data.get('product_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT wishlist_id FROM wishlist WHERE user_id = %s AND product_id = %s", 
                      (session['user_id'], product_id))
        existing = cursor.fetchone()
        
        if existing:
            return jsonify({'success': False, 'message': 'Already in wishlist'})
        
        cursor.execute("""
            INSERT INTO wishlist (user_id, product_id, created_at)
            VALUES (%s, %s, %s)
        """, (session['user_id'], product_id, datetime.now()))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Added to wishlist'})
    
    except Exception as e:
        conn.rollback()
        print(f"Error adding to wishlist: {e}")
        return jsonify({'success': False, 'message': 'Error adding to wishlist'})
    
    finally:
        cursor.close()
        conn.close()

@app.route('/wishlist/remove', methods=['POST'])
def remove_from_wishlist():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    data = request.get_json()
    product_id = data.get('product_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM wishlist WHERE user_id = %s AND product_id = %s", 
                      (session['user_id'], product_id))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Removed from wishlist'})
    
    except Exception as e:
        conn.rollback()
        print(f"Error removing from wishlist: {e}")
        return jsonify({'success': False, 'message': 'Error removing from wishlist'})
    
    finally:
        cursor.close()
        conn.close()

@app.route('/promocodes')
def promocodes():
    if 'user_id' not in session:
        flash('Please login to view promocodes', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT * FROM promocodes 
            WHERE status = 'active' AND valid_until > NOW()
            ORDER BY created_at DESC
        """)
        available_codes = cursor.fetchall()
        
        return render_template('promocodes.html', promocodes=available_codes)
    
    except Exception as e:
        print(f"Error in promocodes route: {e}")
        flash('Error loading promocodes', 'error')
        return redirect(url_for('home'))
    
    finally:
        cursor.close()
        conn.close()



@app.route('/referrals')
def referrals():
    if 'user_id' not in session:
        flash('Please login to view referrals', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT first_name, last_name FROM users WHERE user_id = %s", (session['user_id'],))
        user = cursor.fetchone()
        referral_code = f"{user['first_name'][:2]}{user['last_name'][:2]}{session['user_id'][:6]}".upper()
        
        stats = {
            'total_referrals': 0,
            'total_earned': 0
        }
        
        recent_referrals = []
        
        return render_template('referrals.html', 
                              referral_code=referral_code,
                              stats=stats,
                              recent_referrals=recent_referrals)
    
    except Exception as e:
        print(f"Error in referrals route: {e}")
        flash('Error loading referrals', 'error')
        return redirect(url_for('home'))
    
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT * FROM admin_users 
                WHERE username = %s AND status = 'active'
            """, (username,))
            admin = cursor.fetchone()
            
            if admin and admin['password_hash'] and check_password_hash(admin['password_hash'], password):
                session['admin_logged_in'] = True
                session['admin_id'] = admin['admin_id']
                session['admin_name'] = admin['full_name']
                session['admin_role'] = admin['role']
                
                flash('Admin login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid credentials', 'error')
        
        except Exception as e:
            print(f"Error in admin login: {e}")
            flash('Login failed', 'error')
        
        finally:
            cursor.close()
            conn.close()
    
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT COUNT(*) as total_users FROM users WHERE status = 'active'")
        total_users = cursor.fetchone()['total_users']
        
        cursor.execute("SELECT COUNT(*) as total_products FROM products WHERE status = 'active'")
        total_products = cursor.fetchone()['total_products']
        
        cursor.execute("SELECT COUNT(*) as total_orders FROM orders")
        total_orders = cursor.fetchone()['total_orders']
        
        cursor.execute("SELECT COALESCE(SUM(total_amount), 0) as total_revenue FROM orders WHERE status = 'delivered'")
        total_revenue = cursor.fetchone()['total_revenue'] or 0
        
        stats = {
            'total_users': total_users,
            'total_products': total_products,
            'total_orders': total_orders,
            'total_revenue': total_revenue
        }
        
        return render_template('admin/dashboard.html', stats=stats)
    
    except Exception as e:
        print(f"Error in admin dashboard: {e}")
        stats = {'total_users': 0, 'total_products': 0, 'total_orders': 0, 'total_revenue': 0}
        return render_template('admin/dashboard.html', stats=stats)
    
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/products')
@admin_required
def admin_products():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT p.*, c.category_name,
                   (SELECT pi.image_url FROM product_images pi WHERE pi.product_id = p.product_id LIMIT 1) as image_url
            FROM products p 
            LEFT JOIN categories c ON p.category_id = c.category_id 
            ORDER BY p.created_at DESC
        """)
        products = cursor.fetchall()
        
        return render_template('admin/products.html', products=products)
    
    except Exception as e:
        print(f"Error in admin products: {e}")
        return render_template('admin/products.html', products=[])
    
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/orders')
@admin_required
def admin_orders():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT o.*, u.first_name, u.last_name, u.email 
            FROM orders o 
            LEFT JOIN users u ON o.user_id = u.user_id 
            ORDER BY o.created_at DESC
        """)
        orders = cursor.fetchall()
        
        return render_template('admin/orders.html', orders=orders)
    
    except Exception as e:
        print(f"Error in admin orders: {e}")
        return render_template('admin/orders.html', orders=[])
    
    finally:
        cursor.close()
        conn.close()


@app.route('/api/cart/count')
def api_cart_count():
    if 'user_id' not in session:
        return jsonify({'success': True, 'count': 0})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT SUM(quantity) as total_items FROM cart WHERE user_id = %s", (session['user_id'],))
        result = cursor.fetchone()
        total_items = result[0] if result and result[0] else 0
        
        return jsonify({'success': True, 'count': total_items})
    
    except Exception as e:
        print(f"Error getting cart count: {e}")
        return jsonify({'success': True, 'count': 0})
    
    finally:
        cursor.close()
        conn.close()

@app.route('/api/cart/remove', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    data = request.get_json()
    cart_id = data.get('cart_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM cart WHERE cart_id = %s AND user_id = %s", (cart_id, session['user_id']))
        conn.commit()
        return jsonify({'success': True, 'message': 'Item removed from cart'})
    
    except Exception as e:
        conn.rollback()
        print(f"Error removing from cart: {e}")
        return jsonify({'success': False, 'message': 'Error removing item'})
    
    finally:
        cursor.close()
        conn.close()

@app.route('/api/cart/update', methods=['POST'])
def update_cart_quantity():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    data = request.get_json()
    cart_id = data.get('cart_id')
    quantity = data.get('quantity', 1)
    
    if quantity <= 0:
        return jsonify({'success': False, 'message': 'Invalid quantity'})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE cart SET quantity = %s, updated_at = %s 
            WHERE cart_id = %s AND user_id = %s
        """, (quantity, datetime.now(), cart_id, session['user_id']))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Cart updated successfully'})
    
    except Exception as e:
        conn.rollback()
        print(f"Error updating cart: {e}")
        return jsonify({'success': False, 'message': 'Error updating cart'})
    
    finally:
        cursor.close()
        conn.close()

@app.route('/api/wallet/balance')
def api_wallet_balance():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in', 'balance': 0})
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT balance FROM wallet WHERE user_id = %s", (session['user_id'],))
        wallet_data = cursor.fetchone()
        balance = float(wallet_data['balance']) if wallet_data else 0.00
        
        return jsonify({'success': True, 'balance': balance})
    
    except Exception as e:
        print(f"Error getting wallet balance: {e}")
        return jsonify({'success': False, 'message': 'Error getting balance', 'balance': 0})
    
    finally:
        cursor.close()
        conn.close()


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone', '')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        if not all([name, email, subject, message]):
            flash('Please fill in all required fields', 'error')
            return render_template('contact.html')
        
        flash('Your message has been sent successfully! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
    
    return render_template('contact.html')
@app.route('/api/calculate-checkout-totals', methods=['POST'])
def calculate_checkout_totals():
    """Calculate checkout totals with tax and discounts"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    data = request.get_json()
    state_code = data.get('state_code', 'MH')  # Default to Maharashtra
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get cart items with GST details
        cursor.execute("""
            SELECT c.*, p.product_name, p.price, p.discount_price, p.gst_rate, p.hsn_code
            FROM cart c 
            JOIN products p ON c.product_id = p.product_id 
            WHERE c.user_id = %s
        """, (session['user_id'],))
        cart_items = cursor.fetchall()
        
        if not cart_items:
            return jsonify({'success': False, 'message': 'Cart is empty'})
        
        # Calculate totals
        totals = calculate_order_totals(cart_items, state_code)
        
        # Get tax breakdown
        tax_breakdown = calculate_product_wise_gst(cart_items, state_code)
        
        return jsonify({
            'success': True,
            'totals': totals,
            'tax_breakdown': tax_breakdown,
            'applied_promocode': session.get('applied_promocode')
        })
    
    except Exception as e:
        print(f"Error calculating totals: {e}")
        return jsonify({'success': False, 'message': 'Error calculating totals'})
    
    finally:
        cursor.close()
        conn.close()

@app.route('/api/apply-checkout-promocode', methods=['POST'])
def apply_checkout_promocode():
    """Apply promocode and return updated totals"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    data = request.get_json()
    code = data.get('code', '').upper().strip()
    state_code = data.get('state_code', 'MH')
    
    if not code:
        return jsonify({'success': False, 'message': 'Please enter a promocode'})
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Validate promocode
        cursor.execute("""
            SELECT * FROM promocodes 
            WHERE code = %s AND status = 'active' 
            AND valid_from <= NOW() AND valid_until >= NOW()
            AND (usage_limit IS NULL OR used_count < usage_limit)
        """, (code,))
        promocode = cursor.fetchone()
        
        if not promocode:
            return jsonify({'success': False, 'message': 'Invalid or expired promocode'})
        
        # Get cart items
        cursor.execute("""
            SELECT c.*, p.product_name, p.price, p.discount_price, p.gst_rate, p.hsn_code
            FROM cart c 
            JOIN products p ON c.product_id = p.product_id 
            WHERE c.user_id = %s
        """, (session['user_id'],))
        cart_items = cursor.fetchall()
        
        # Calculate subtotal first
        subtotal = sum([
            (float(item['discount_price']) if item['discount_price'] else float(item['price'])) * item['quantity']
            for item in cart_items
        ])
        
        # Check minimum order amount
        min_order = float(promocode.get('min_order_amount') or 0)
        if subtotal < min_order:
            return jsonify({
                'success': False, 
                'message': f'Minimum order amount ₹{min_order} required for this promocode'
            })
        
        # Store promocode in session
        session['applied_promocode'] = {
            'code': promocode['code'],
            'discount_type': promocode['discount_type'],
            'discount_value': float(promocode['discount_value']),
            'min_order_amount': min_order,
            'max_discount_amount': float(promocode.get('max_discount_amount') or 0)
        }
        
        # Calculate new totals
        totals = calculate_order_totals(cart_items, state_code)
        tax_breakdown = calculate_product_wise_gst(cart_items, state_code)
        
        return jsonify({
            'success': True,
            'message': f'Promocode {code} applied successfully!',
            'totals': totals,
            'tax_breakdown': tax_breakdown,
            'applied_promocode': session['applied_promocode']
        })
    
    except Exception as e:
        print(f"Error applying promocode: {e}")
        return jsonify({'success': False, 'message': 'Error applying promocode'})
    
    finally:
        cursor.close()
        conn.close()

@app.route('/api/remove-promocode', methods=['POST'])
def remove_promocode():
    """Remove applied promocode"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    data = request.get_json()
    state_code = data.get('state_code', 'MH')
    
    # Remove promocode from session
    if 'applied_promocode' in session:
        del session['applied_promocode']
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get cart items and recalculate
        cursor.execute("""
            SELECT c.*, p.product_name, p.price, p.discount_price, p.gst_rate, p.hsn_code
            FROM cart c 
            JOIN products p ON c.product_id = p.product_id 
            WHERE c.user_id = %s
        """, (session['user_id'],))
        cart_items = cursor.fetchall()
        
        totals = calculate_order_totals(cart_items, state_code)
        tax_breakdown = calculate_product_wise_gst(cart_items, state_code)
        
        return jsonify({
            'success': True,
            'message': 'Promocode removed',
            'totals': totals,
            'tax_breakdown': tax_breakdown,
            'applied_promocode': None
        })
    
    except Exception as e:
        print(f"Error removing promocode: {e}")
        return jsonify({'success': False, 'message': 'Error removing promocode'})
    
    finally:
        cursor.close()
        conn.close()

# Fix the calculate_order_totals function


@app.route('/faq')
def faq():
    faq_categories = {
        'Orders': [
            {'faq_id': 1, 'question': 'How do I place an order?', 'answer': 'You can place an order by adding items to your cart and proceeding to checkout.'},
            {'faq_id': 2, 'question': 'Can I modify my order?', 'answer': 'Orders can be modified within 30 minutes of placement. Contact support for assistance.'}
        ],
        'Shipping': [
            {'faq_id': 3, 'question': 'What are the delivery charges?', 'answer': 'Free delivery on orders above ₹500. Below that, ₹50 delivery charge applies.'},
            {'faq_id': 4, 'question': 'How long does delivery take?', 'answer': 'We typically deliver within 2-5 business days.'}
        ],
        'Returns': [
            {'faq_id': 5, 'question': 'What is your return policy?', 'answer': '7-day return policy for unopened products in original packaging.'}
        ]
    }
    
    return render_template('faq.html', faq_categories=faq_categories)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

def create_default_admin():
    """Create default admin user if none exists"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM admin_users")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            admin_id = str(uuid.uuid4())
            password_hash = generate_password_hash('admin123')
            
            cursor.execute("""
                INSERT INTO admin_users (admin_id, username, email, password_hash, full_name, role, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (admin_id, 'admin', 'admin@example.com', password_hash, 'System Administrator', 'super_admin', 'active', datetime.now()))
            
            conn.commit()
            print("Default admin user created: username=admin, password=admin123")
    
    except Exception as e:
        conn.rollback()
        print(f"Error creating default admin: {e}")
    
    finally:
        cursor.close()
        conn.close()
import uuid
import json
from decimal import Decimal

@app.route('/api/place-order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    data = request.get_json()
    address_id = data.get('address_id')
    payment_method = data.get('payment_method')
    notes = data.get('notes', '')
    
    if not address_id or not payment_method:
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get cart items with all details
        cursor.execute("""
            SELECT c.*, p.product_name, p.price, p.discount_price, p.gst_rate, p.hsn_code,
                   i.quantity as stock_quantity
            FROM cart c 
            JOIN products p ON c.product_id = p.product_id 
            LEFT JOIN inventory i ON p.product_id = i.product_id 
            WHERE c.user_id = %s
        """, (session['user_id'],))
        cart_items = cursor.fetchall()
        
        if not cart_items:
            return jsonify({'success': False, 'message': 'Cart is empty'})
        
        # Validate inventory for all items
        for item in cart_items:
            stock_qty = item.get('stock_quantity', 0) or 0
            if stock_qty < item['quantity']:
                return jsonify({
                    'success': False, 
                    'message': f'{item["product_name"]} is out of stock. Available: {stock_qty}'
                })
        
        # Get shipping address
        cursor.execute("SELECT * FROM addresses WHERE address_id = %s AND user_id = %s", 
                      (address_id, session['user_id']))
        address = cursor.fetchone()
        
        if not address:
            return jsonify({'success': False, 'message': 'Invalid address'})
        
        # Calculate order totals
        order_totals = calculate_order_totals(cart_items, address['state'])
        
        # Validate wallet balance if payment method is wallet
        if payment_method == 'wallet':
            cursor.execute("SELECT balance FROM wallet WHERE user_id = %s", (session['user_id'],))
            wallet_data = cursor.fetchone()
            wallet_balance = float(wallet_data['balance']) if wallet_data else 0.0
            
            if wallet_balance < order_totals['total_amount']:
                return jsonify({
                    'success': False, 
                    'message': f'Insufficient wallet balance. Available: ₹{wallet_balance}'
                })
        
        # Generate order ID and number
        order_id = str(uuid.uuid4())
        order_number = generate_order_number()
        
        # Prepare address JSON
        shipping_address_json = json.dumps({
            'full_name': address['full_name'],
            'phone': address['phone'],
            'address_line1': address['address_line1'],
            'address_line2': address['address_line2'] or '',
            'city': address['city'],
            'state': address['state'],
            'postal_code': address['postal_code'],
            'country': address.get('country', 'India')
        })
        
        # Create order
        cursor.execute("""
            INSERT INTO orders (
                order_id, user_id, order_number, status, subtotal, tax_amount, 
                shipping_amount, discount_amount, total_amount, payment_method, 
                payment_status, shipping_address, notes, cgst_amount, sgst_amount, 
                igst_amount, tax_rate, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            order_id, session['user_id'], order_number, 'pending', 
            order_totals['subtotal'], order_totals['tax_amount'],
            order_totals['shipping_amount'], order_totals['discount_amount'],
            order_totals['total_amount'], payment_method,
            'pending' if payment_method in ['cod'] else 'pending',
            shipping_address_json, notes,
            order_totals['cgst_amount'], order_totals['sgst_amount'],
            order_totals['igst_amount'], order_totals['avg_tax_rate'],
            datetime.now()
        ))
        
        # Create order items
        for item in cart_items:
            unit_price = float(item['discount_price']) if item['discount_price'] else float(item['price'])
            total_price = unit_price * item['quantity']
            
            cursor.execute("""
                INSERT INTO order_items (
                    order_id, product_id, variant_id, product_name, variant_name,
                    quantity, unit_price, total_price, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                order_id, item['product_id'], item.get('variant_id'),
                item['product_name'], item.get('variant_name'),
                item['quantity'], unit_price, total_price, datetime.now()
            ))
        
        # Update inventory
        for item in cart_items:
            cursor.execute("""
                UPDATE inventory 
                SET quantity = quantity - %s, reserved_quantity = reserved_quantity + %s
                WHERE product_id = %s
            """, (item['quantity'], item['quantity'], item['product_id']))
        
        # Process payment
        payment_result = process_payment(order_id, payment_method, order_totals['total_amount'], cursor, conn)
        
        if not payment_result['success']:
            # Rollback inventory changes
            for item in cart_items:
                cursor.execute("""
                    UPDATE inventory 
                    SET quantity = quantity + %s, reserved_quantity = reserved_quantity - %s
                    WHERE product_id = %s
                """, (item['quantity'], item['quantity'], item['product_id']))
            
            return jsonify(payment_result)
        
        # Create initial order tracking
        cursor.execute("""
            INSERT INTO order_tracking (order_id, status, message, created_at)
            VALUES (%s, %s, %s, %s)
        """, (order_id, 'order_placed', 'Order has been placed successfully', datetime.now()))
        
        # Clear cart
        cursor.execute("DELETE FROM cart WHERE user_id = %s", (session['user_id'],))
        
        # Commit all changes
        conn.commit()
        
        # Send order confirmation email (basic)
        try:
            send_order_confirmation_email(order_id, order_number, session['user_id'])
        except Exception as e:
            print(f"Email sending failed: {e}")
            # Don't fail the order if email fails
        
        return jsonify({
            'success': True,
            'message': 'Order placed successfully!',
            'order_id': order_id,
            'order_number': order_number,
            'total_amount': order_totals['total_amount']
        })
    
    except Exception as e:
        conn.rollback()
        print(f"Error placing order: {e}")
        return jsonify({'success': False, 'message': 'Error placing order. Please try again.'})
    
    finally:
        cursor.close()
        conn.close()


@app.route('/api/check-stock', methods=['POST'])
def check_stock():
    """API endpoint to check stock availability"""
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    is_available, message = check_and_reserve_inventory(product_id, quantity)
    
    return jsonify({
        'success': is_available,
        'message': message,
        'available': is_available
    })
if __name__ == '__main__':
    create_default_admin()
    
   
    app.run(debug=True)