# app.py - The main file that runs our Blood Bank website

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
import config

from constants import BLOOD_TYPES, ROLES, URGENCY_LEVELS, STATUS_LEVELS
from utils import logger, sanitize_input, validate_enum, parse_positive_int, DBHelper

# Start the Flask app
app = Flask(__name__)
app.config.from_object(config.Config)

# Connect to database and security tools
mysql = MySQL(app)
bcrypt = Bcrypt(app)
db = DBHelper(mysql)

# ================================================
# HOME PAGE
# ================================================
@app.route('/')
def home():
    return render_template('home.html')

# ================================================
# REGISTER PAGE
# ================================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name     = sanitize_input(request.form.get('name'))
        email    = sanitize_input(request.form.get('email'))
        if email: email = email.lower()
        password = request.form.get('password')
        role     = validate_enum(sanitize_input(request.form.get('role')), ROLES)

        if not role:
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('register'))

        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Check if email already exists
        existing_user = db.fetch_one("SELECT * FROM users WHERE email = %s", (email,))
        if existing_user:
            flash('Email already registered! Please login.', 'danger')
            return redirect(url_for('register'))

        # Save new user to database
        query = "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)"
        if db.safe_execute(query, (name, email, hashed_password, role), "Account created successfully! Please login."):
            return redirect(url_for('login'))
        else:
            return redirect(url_for('register'))

    return render_template('register.html')

# ================================================
# LOGIN PAGE
# ================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = sanitize_input(request.form.get('email'))
        if email: email = email.lower()
        password = request.form.get('password')

        user = db.fetch_one("SELECT * FROM users WHERE email = %s", (email,))

        is_valid_password = False
        if user:
            try:
                is_valid_password = bcrypt.check_password_hash(user['password'], password)
            except ValueError:
                # Handle legacy plain-text passwords
                is_valid_password = (user['password'] == password)
                # Rehash and update the database if the plaintext password is correct
                if is_valid_password:
                    new_hash = bcrypt.generate_password_hash(password).decode('utf-8')
                    db.safe_execute("UPDATE users SET password = %s WHERE user_id = %s", (new_hash, user['user_id']))

        if user and is_valid_password:
            session['user_id']   = user['user_id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']

            flash(f"Welcome back, {user['name']}!", 'success')

            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))

            elif user['role'] == 'donor':
                donor_profile = db.fetch_one("SELECT * FROM donors WHERE user_id = %s", (user['user_id'],))
                if donor_profile:
                    session['blood_type'] = donor_profile['blood_type']
                    return redirect(url_for('donor_dashboard'))
                else:
                    flash('Please complete your donor profile first!', 'info')
                    return redirect(url_for('donor_profile'))

            elif user['role'] == 'hospital':
                hospital_profile = db.fetch_one("SELECT * FROM hospitals WHERE user_id = %s", (user['user_id'],))
                if hospital_profile:
                    return redirect(url_for('hospital_dashboard'))
                else:
                    flash('Please complete your hospital profile first!', 'info')
                    return redirect(url_for('hospital_profile'))
        else:
            flash('Wrong email or password!', 'danger')

    return render_template('login.html')

# ================================================
# LOGOUT
# ================================================
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out!', 'success')
    return redirect(url_for('home'))

# ================================================
# DONOR PROFILE SETUP
# ================================================
@app.route('/donor/profile', methods=['GET', 'POST'])
def donor_profile():
    if 'user_id' not in session or session['user_role'] != 'donor':
        return redirect(url_for('login'))

    cities = db.fetch_all("SELECT * FROM cities ORDER BY city_name")

    if request.method == 'POST':
        blood_type    = validate_enum(sanitize_input(request.form.get('blood_type')), BLOOD_TYPES)
        phone         = sanitize_input(request.form.get('phone'))
        city_id       = sanitize_input(request.form.get('city_id'))
        date_of_birth = sanitize_input(request.form.get('date_of_birth'))

        if not blood_type:
            flash('Invalid blood type selected.', 'danger')
            return redirect(url_for('donor_profile'))

        existing = db.fetch_one("SELECT * FROM donors WHERE user_id = %s", (session['user_id'],))

        if existing:
            query = """
                UPDATE donors
                SET blood_type = %s, phone = %s, city_id = %s, date_of_birth = %s, is_available = 1
                WHERE user_id = %s
            """
            params = (blood_type, phone, city_id, date_of_birth, session['user_id'])
        else:
            query = """
                INSERT INTO donors (user_id, city_id, blood_type, phone, date_of_birth, is_available)
                VALUES (%s, %s, %s, %s, %s, 1)
            """
            params = (session['user_id'], city_id, blood_type, phone, date_of_birth)

        if db.safe_execute(query, params, "Donor profile saved! Welcome to the Blood Bank network! 🩸", "Failed to save profile."):
            session['blood_type'] = blood_type
            return redirect(url_for('donor_dashboard'))
        else:
            return redirect(url_for('donor_profile'))

    return render_template('donor_profile.html', cities=cities)

# ================================================
# HOSPITAL PROFILE SETUP
# ================================================
@app.route('/hospital/profile', methods=['GET', 'POST'])
def hospital_profile():
    if 'user_id' not in session or session['user_role'] != 'hospital':
        return redirect(url_for('login'))

    cities = db.fetch_all("SELECT * FROM cities ORDER BY city_name")

    if request.method == 'POST':
        hospital_name = sanitize_input(request.form.get('hospital_name'))
        phone         = sanitize_input(request.form.get('phone'))
        address       = sanitize_input(request.form.get('address'))
        city_id       = sanitize_input(request.form.get('city_id'))

        existing = db.fetch_one("SELECT * FROM hospitals WHERE user_id = %s", (session['user_id'],))

        if existing:
            query = """
                UPDATE hospitals
                SET hospital_name = %s, phone = %s, address = %s, city_id = %s
                WHERE user_id = %s
            """
            params = (hospital_name, phone, address, city_id, session['user_id'])
        else:
            query = """
                INSERT INTO hospitals (user_id, city_id, hospital_name, phone, address, is_verified)
                VALUES (%s, %s, %s, %s, %s, 0)
            """
            params = (session['user_id'], city_id, hospital_name, phone, address)

        if db.safe_execute(query, params, "Hospital profile saved! You can now post blood requests. 🏥", "Failed to save profile."):
            return redirect(url_for('hospital_dashboard'))
        else:
            return redirect(url_for('hospital_profile'))

    return render_template('hospital_profile.html', cities=cities)

# ================================================
# DONOR DASHBOARD
# ================================================
@app.route('/donor/dashboard')
def donor_dashboard():
    if 'user_id' not in session or session['user_role'] != 'donor':
        return redirect(url_for('login'))

    donor = db.fetch_one("""
        SELECT d.*, c.city_name
        FROM donors d
        JOIN cities c ON d.city_id = c.city_id
        WHERE d.user_id = %s
    """, (session['user_id'],))

    if not donor:
        flash('Please complete your profile first!', 'info')
        return redirect(url_for('donor_profile'))

    if 'blood_type' not in session:
        session['blood_type'] = donor['blood_type']

    blood_type = session['blood_type']
    
    # User-requested debug logs removed to prevent UnicodeEncodeError

    try:
        alerts = db.fetch_all("""
            SELECT br.*, h.hospital_name 
            FROM blood_requests br
            JOIN hospitals h ON br.hospital_id = h.hospital_id
            WHERE br.status = 'open'
            AND br.urgency = 'critical'
            AND br.blood_type = %s
            ORDER BY br.created_at DESC
        """, (blood_type,))
        
        # User-requested debug log removed to prevent UnicodeEncodeError

    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")

        alerts = []

    donations = db.fetch_all("""
        SELECT dn.*, h.hospital_name
        FROM donations dn
        JOIN hospitals h ON dn.hospital_id = h.hospital_id
        WHERE dn.donor_id = %s
        ORDER BY dn.donation_date DESC
    """, (donor['donor_id'],))

    return render_template('donor_dashboard.html',
                           donor=donor,
                           alerts=alerts,
                           donations=donations)

# ================================================
# RESPOND TO REQUEST
# ================================================
@app.route('/respond_request', methods=['POST'])
def respond_request():
    if 'user_id' not in session or session['user_role'] != 'donor':
        return redirect(url_for('login'))

    request_id = request.form.get('request_id')
    
    if not request_id:
        flash('Invalid request ID.', 'danger')
        return redirect(url_for('donor_dashboard'))

    try:
        # Get donor_id from session user_id
        donor = db.fetch_one("SELECT donor_id FROM donors WHERE user_id = %s", (session['user_id'],))
        if not donor:
            flash('Donor profile not found.', 'danger')
            return redirect(url_for('donor_profile'))

        # Get hospital_id from the blood request
        blood_request = db.fetch_one("SELECT hospital_id FROM blood_requests WHERE request_id = %s AND status = 'open'", (request_id,))
        if not blood_request:
            flash('Blood request not found or already fulfilled.', 'danger')
            return redirect(url_for('donor_dashboard'))

        # Perform transaction: Insert donation & update request status
        cur = db.mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO donations (donor_id, hospital_id, request_id, donation_date, status)
                VALUES (%s, %s, %s, CURDATE(), 'pending')
            """, (donor['donor_id'], blood_request['hospital_id'], request_id))
            
            cur.execute("""
                UPDATE blood_requests 
                SET status = 'fulfilled' 
                WHERE request_id = %s
            """, (request_id,))
            
            db.mysql.connection.commit()
            flash("You have successfully responded to the request!", 'success')
        except Exception as e:
            db.mysql.connection.rollback()
            raise e
        finally:
            cur.close()

    except Exception as e:
        from utils import logger
        logger.error(f"Error in respond_request: {e}")
        flash('An error occurred while responding. Please try again.', 'danger')

    return redirect(url_for('donor_dashboard'))

# ================================================
# HOSPITAL DASHBOARD
# ================================================
@app.route('/hospital/dashboard', methods=['GET', 'POST'])
def hospital_dashboard():
    if 'user_id' not in session or session['user_role'] != 'hospital':
        return redirect(url_for('login'))

    hospital = db.fetch_one("SELECT * FROM hospitals WHERE user_id = %s", (session['user_id'],))

    if not hospital:
        flash('Please complete your hospital profile first!', 'info')
        return redirect(url_for('hospital_profile'))

    if request.method == 'POST':
        blood_type   = validate_enum(sanitize_input(request.form.get('blood_type')), BLOOD_TYPES)
        units_needed = parse_positive_int(request.form.get('units_needed'))
        urgency      = sanitize_input(request.form.get('urgency'))
        notes        = sanitize_input(request.form.get('notes'))

        if urgency == 'emergency':
            urgency = 'critical'
        urgency = validate_enum(urgency, URGENCY_LEVELS, default='normal')

        if not blood_type:
            flash('Invalid blood type selected.', 'danger')
            return redirect(url_for('hospital_dashboard'))
            
        if not units_needed:
            flash('Units needed must be a valid positive number.', 'danger')
            return redirect(url_for('hospital_dashboard'))

        query = """
            INSERT INTO blood_requests (hospital_id, blood_type, units_needed, urgency, status, notes)
            VALUES (%s, %s, %s, %s, 'open', %s)
        """
        params = (hospital['hospital_id'], blood_type, units_needed, urgency, notes)
        
        db.safe_execute(query, params, "Blood request posted successfully! 🩸", "Failed to post request.")

    # Get this hospital's requests
    try:
        requests_data = db.fetch_all("""
            SELECT * FROM blood_requests
            WHERE hospital_id = %s
            ORDER BY created_at DESC
        """, (hospital['hospital_id'],))

        open_count_row = db.fetch_one("SELECT COUNT(*) as cnt FROM blood_requests WHERE hospital_id = %s AND status = 'open'", (hospital['hospital_id'],))
        open_count = open_count_row['cnt'] if open_count_row else 0

        fulfilled_count_row = db.fetch_one("SELECT COUNT(*) as cnt FROM blood_requests WHERE hospital_id = %s AND status = 'fulfilled'", (hospital['hospital_id'],))
        fulfilled_count = fulfilled_count_row['cnt'] if fulfilled_count_row else 0

        inventory = db.fetch_all("SELECT * FROM blood_inventory WHERE hospital_id = %s", (hospital['hospital_id'],))

        total_row = db.fetch_one("SELECT SUM(units_available) as total FROM blood_inventory WHERE hospital_id = %s", (hospital['hospital_id'],))
        total_inventory = total_row['total'] if total_row and total_row['total'] else 0
    except Exception as e:
        logger.error(f"Dashboard Data Load Error: {e}")
        requests_data, inventory = [], []
        open_count, fulfilled_count, total_inventory = 0, 0, 0

    return render_template('hospital_dashboard.html',
                           hospital=hospital,
                           requests=requests_data,
                           inventory=inventory,
                           open_count=open_count,
                           fulfilled_count=fulfilled_count,
                           total_inventory=total_inventory)

# ================================================
# ADMIN DASHBOARD
# ================================================
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))

    try:
        total_donors = db.fetch_one("SELECT COUNT(*) as cnt FROM donors")['cnt']
        total_hospitals = db.fetch_one("SELECT COUNT(*) as cnt FROM hospitals")['cnt']
        total_requests = db.fetch_one("SELECT COUNT(*) as cnt FROM blood_requests")['cnt']
        total_donations = db.fetch_one("SELECT COUNT(*) as cnt FROM donations")['cnt']

        donors = db.fetch_all("""
            SELECT u.name, d.blood_type, c.city_name, d.is_available
            FROM donors d
            JOIN users u ON d.user_id = u.user_id
            JOIN cities c ON d.city_id = c.city_id
            ORDER BY u.name
        """)

        all_requests = db.fetch_all("""
            SELECT br.*, h.hospital_name
            FROM blood_requests br
            JOIN hospitals h ON br.hospital_id = h.hospital_id
            ORDER BY br.created_at DESC
        """)

        # Blood type counts for bar chart
        bt_rows = db.fetch_all("SELECT blood_type, COUNT(*) as cnt FROM blood_requests GROUP BY blood_type")
        blood_types_order = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        bt_dict = {row['blood_type']: row['cnt'] for row in bt_rows}
        blood_type_counts = [bt_dict.get(bt, 0) for bt in blood_types_order]
        blood_type_counts = blood_type_counts if blood_type_counts else [0, 0, 0, 0, 0, 0, 0, 0]

        # Status counts for doughnut chart
        open_status = db.fetch_one("SELECT COUNT(*) as cnt FROM blood_requests WHERE status='open'")['cnt']
        fulfilled = db.fetch_one("SELECT COUNT(*) as cnt FROM blood_requests WHERE status='fulfilled'")['cnt']
        cancelled = db.fetch_one("SELECT COUNT(*) as cnt FROM blood_requests WHERE status='cancelled'")['cnt']
        status_counts = [open_status, fulfilled, cancelled]
        status_counts = status_counts if status_counts else [0, 0, 0]
    except Exception as e:
        logger.error(f"Admin Dashboard Data Load Error: {e}")
        return "An error occurred loading the dashboard.", 500

    return render_template('admin_dashboard.html',
                           total_donors=total_donors,
                           total_hospitals=total_hospitals,
                           total_requests=total_requests,
                           total_donations=total_donations,
                           donors=donors,
                           all_requests=all_requests,
                           blood_type_counts=blood_type_counts,
                           status_counts=status_counts)

# ================================================
# RUN THE APP
# ================================================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
