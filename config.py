import os
from dotenv import load_dotenv


class Config:

    SECRET_KEY = 'kkkkkkkkkkkkkkkkkk'
    JWT_SECRET_KEY = 'hhhhhhhhhhhhhhhhh'
    
    # Database Configuration
    DB_HOST =  'localhost'
    DB_USER = 'root'
    DB_PASSWORD =  'password'
    DB_NAME =  'ecommerce_db'
    DB_PORT = 3306
    
    # File Upload Configuration
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Email Configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT =  587
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = 'san@gmail.com'
    
    # Cache Configuration
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT =  300
    REDIS_URL = 'redis://localhost:6379'
    
    # Payment Gateway Configuration (Placeholder)
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    
    # SMS Configuration (Placeholder)
    SMS_API_KEY = os.environ.get('SMS_API_KEY')
    SMS_API_URL = os.environ.get('SMS_API_URL')
    
    # Courier/Shipping Configuration (Placeholder)
    SHIPROCKET_API_KEY = os.environ.get('SHIPROCKET_API_KEY')
    DELHIVERY_API_KEY = os.environ.get('DELHIVERY_API_KEY')
    
    # Application Settings
    ITEMS_PER_PAGE =  12
    JWT_EXPIRATION_DELTA =  24
    PASSWORD_MIN_LENGTH = 6
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_DEFAULT = '200/hour'
    
    # Session Configuration
    SESSION_PERMANENT = False
    SESSION_TYPE = 'filesystem'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in ['true', 'on', '1']
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'"
    }
    
    # Business Configuration
    COMPANY_NAME = 'Lorem ipsum'
    COMPANY_EMAIL = 'info@Loremipsum.com'
    COMPANY_PHONE = '+91 6261116108'
    COMPANY_ADDRESS = 'India'
    
    # Delivery Configuration
    FREE_DELIVERY_THRESHOLD = 500
    STANDARD_DELIVERY_CHARGE = 50
    EXPRESS_DELIVERY_CHARGE =  100
    # Indian States with codes for GST calculation
    INDIAN_STATES = {
        'AN': 'Andaman and Nicobar Islands',
        'AP': 'Andhra Pradesh', 
        'AR': 'Arunachal Pradesh',
        'AS': 'Assam',
        'BR': 'Bihar',
        'CH': 'Chandigarh',
        'CG': 'Chhattisgarh',
        'DN': 'Dadra and Nagar Haveli',
        'DD': 'Daman and Diu',
        'DL': 'Delhi',
        'GA': 'Goa',
        'GJ': 'Gujarat',
        'HR': 'Haryana',
        'HP': 'Himachal Pradesh',
        'JK': 'Jammu and Kashmir',
        'JH': 'Jharkhand',
        'KA': 'Karnataka',
        'KL': 'Kerala',
        'LD': 'Lakshadweep',
        'MP': 'Madhya Pradesh',
        'MH': 'Maharashtra',
        'MN': 'Manipur',
        'ML': 'Meghalaya',
        'MZ': 'Mizoram',
        'NL': 'Nagaland',
        'OR': 'Odisha',
        'PY': 'Puducherry',
        'PB': 'Punjab',
        'RJ': 'Rajasthan',
        'SK': 'Sikkim',
        'TN': 'Tamil Nadu',
        'TS': 'Telangana',
        'TR': 'Tripura',
        'UP': 'Uttar Pradesh',
        'UK': 'Uttarakhand',
        'WB': 'West Bengal'
    }

    # Your business state (change as per your registration)
    BUSINESS_STATE_CODE = 'MP'  
    BUSINESS_GSTIN = 'YOUR_GSTIN_NUMBER'
    # Tax Configuration
    
    @staticmethod
    def get_db_config():
       
        return {
            'host': Config.DB_HOST,
            'user': Config.DB_USER,
            'password': Config.DB_PASSWORD,
            'database': Config.DB_NAME,
            'port': Config.DB_PORT,
            'autocommit': True,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci'
        }
    
    @staticmethod
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    

class DevelopmentConfig(Config):
  
    DEBUG = True
    TESTING = False
    
    
    MAIL_SUPPRESS_SEND = False
    CACHE_TYPE = 'simple'
    
  
    DB_NAME = os.environ.get('DEV_DB_NAME') or Config.DB_NAME

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    
   
    SESSION_COOKIE_SECURE = True
   
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = Config.REDIS_URL
    
  
    RATELIMIT_STORAGE_URL = Config.REDIS_URL

class TestingConfig(Config):
    
    DEBUG = True
    TESTING = True
    
   
    DB_NAME = os.environ.get('TEST_DB_NAME') or 'test_ecommerce_db'
    
    
    MAIL_SUPPRESS_SEND = True
    
    
    CACHE_TYPE = 'null'
    
    
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])