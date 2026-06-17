import bcrypt

hash = '$2b$12$0mtov9/gpnNiD48X0Tn4QuznzDJpOdZ10eeE6O3.766dOnRXYvQGW'
passwords_to_try = ['admin123', 'admin', 'password', 'Qwerty', 'admin@123', 'admin@321', 'admin@bloodbank.com']

for password in passwords_to_try:
    if bcrypt.checkpw(password.encode('utf-8'), hash.encode('utf-8')):
        print(f"MATCH FOUND: {password}")
        break
else:
    print("NO MATCH FOUND")
