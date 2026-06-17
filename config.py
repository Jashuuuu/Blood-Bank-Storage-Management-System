# config.py - This file tells Flask how to connect to our database

class Config:
    # Secret key - used to keep login sessions secure
    SECRET_KEY = 'bloodbank_secret_key_2024'
    
    # Database connection settings
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'Qwerty'  # ⚠️ Change this to YOUR MySQL password!
    MYSQL_DB = 'blood_bank_db'
    MYSQL_CURSORCLASS = 'DictCursor'