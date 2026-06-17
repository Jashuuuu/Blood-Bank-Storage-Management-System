import json
from flask import Flask, render_template_string
from flask_mysqldb import MySQL
import config
from utils import DBHelper

app = Flask(__name__)
app.config.from_object(config.Config)
mysql = MySQL(app)

with app.app_context():
    db = DBHelper(mysql)
    blood_type = 'B+'
    print(f"SESSION MOCK: {{'blood_type': '{blood_type}'}}")
    print(f"BLOOD TYPE: {blood_type}")

    alerts = db.fetch_all("""
        SELECT br.*, h.hospital_name 
        FROM blood_requests br
        JOIN hospitals h ON br.hospital_id = h.hospital_id
        WHERE br.status = 'open'
        AND br.urgency = 'critical'
        AND br.blood_type = %s
        ORDER BY br.created_at DESC
    """, (blood_type,))
    
    print("ALERTS:", alerts)
    if len(alerts) > 0:
        print("Success! Alerts retrieved:", len(alerts))
        print("First alert dictionary keys:", alerts[0].keys())
        print("First alert blood_type:", alerts[0]['blood_type'])
    else:
        print("No alerts found.")
