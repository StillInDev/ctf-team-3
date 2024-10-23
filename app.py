# Import the required libraries hi
#lkasjdflksjdf
from flask import Flask, request, jsonify, make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time
import os
from logger import setup_logging, log_request_and_response, log_security_event
import uuid
from bcrypt import hashpw, gensalt, checkpw

# Import functions from utils.py
from utils import get_user_from_cookie, get_db_connection

login_attempts = {}


app = Flask(__name__)

# Initialize the Limiter
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Set up logging
setup_logging(app)

@app.after_request
def after_request(response):
    return log_request_and_response(request, response, app)

@app.route('/register')
def register():
    user = request.args.get('user')
    password = request.args.get('pass')
    
    if not user or not password:
        log_security_event(app, request.remote_addr, "Registration attempt with missing credentials")
        return make_response("Missing credentials", 400)
    
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE username = %s;", (user,))
    if cursor.fetchone():
        log_security_event(app, request.remote_addr, f"Attempted to register existing user: {user}")
        cursor.close()
        conn.close()
        return make_response("User already exists", 400)

    # Hash the password before storing
    hashed_password = hashpw(password.encode(), gensalt()).decode('utf-8')
    
    # Insert new user
    cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s);", (user, hashed_password))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return make_response("User registered successfully", 201)

@app.route('/login')
@limiter.limit("5 per minute")  # Allow only 5 login attempts per minute per IP
def login():
    user = request.args.get('user')
    password = request.args.get('pass')
    ip = request.remote_addr
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Track login attempts
    if ip not in login_attempts:
        login_attempts[ip] = {'count': 0, 'last_attempt': time.time()}
    
    # Reset counter if last attempt was more than 5 minutes ago
    if time.time() - login_attempts[ip]['last_attempt'] > 300:
        login_attempts[ip]['count'] = 0
    
    login_attempts[ip]['count'] += 1
    login_attempts[ip]['last_attempt'] = time.time()
    
    # Check for brute force attempts
    if login_attempts[ip]['count'] > 5:
        log_security_event(app, ip, f"Possible brute force attack detected from IP: {ip}", level='critical')
        cursor.close()
        conn.close()
        return make_response("Too many login attempts", 429)
    
    # Retrieve the hashed password from the database
    cursor.execute("SELECT id, password_hash FROM users WHERE username = %s;", (user,))
    user_data = cursor.fetchone()
    
    if user_data:
        user_id, stored_hashed_password = user_data
        
        # Verify the provided password against the stored hashed password
        if checkpw(password.encode(), stored_hashed_password.encode('utf-8')):
            # Generate a unique session cookie
            session_cookie = str(uuid.uuid4())
            
            # Store the session in the database
            cursor.execute("INSERT INTO sessions (user_id, cookie) VALUES (%s, %s);", (user_id, session_cookie))
            conn.commit()

            response = make_response(jsonify({"message": "Login successful"}))
            response.set_cookie('session', session_cookie)

            
            cursor.close()
            conn.close()
            return response
    
    log_security_event(app, ip, f"Failed login attempt for user: {user}")
    cursor.close()
    conn.close()
    return make_response("Invalid login", 401)

@app.route('/manage')
@limiter.limit("10 per minute")  # Allow only 10 manage requests per minute per IP
def manage():
    cookie = request.cookies.get('session')
    user_data = get_user_from_cookie(cookie)

    if not user_data:
        log_security_event(app, request.remote_addr, "Attempt to manage without valid session")
        return make_response("Invalid session", 401)

    user_id = user_data[0]
    action = request.args.get('action')
    amount = request.args.get('amount', type=float)

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Handle different actions
    if action == "deposit":
        if amount is None or amount <= 0:
            log_security_event(app, request.remote_addr, f"Invalid deposit amount: {amount}")
            cursor.close()
            conn.close()
            return make_response("Invalid amount", 400)
        
        cursor.execute("UPDATE users SET balance = balance + %s WHERE id = %s;", (amount, user_id))
        conn.commit()

        cursor.execute("SELECT balance FROM users WHERE id = %s;", (user_id,))
        new_balance = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        return make_response(f"balance={new_balance}", 200)

    elif action == "withdraw":
        if amount is None or amount <= 0:
            log_security_event(app, request.remote_addr, f"Invalid withdrawal amount: {amount}")
            cursor.close()
            conn.close()
            return make_response("Invalid amount", 400)

        # Attempt to deduct the amount only if the balance is sufficient
        cursor.execute("""
            UPDATE users
            SET balance = balance - %s
            WHERE id = %s AND balance >= %s
            RETURNING balance;
        """, (amount, user_id, amount))
        result = cursor.fetchone()
        
        if result:
            new_balance = result[0]
            conn.commit()
            cursor.close()
            conn.close()
            return make_response(f"balance={new_balance}", 200)
        else:
            log_security_event(app, request.remote_addr, f"Insufficient funds withdrawal attempt: {user_data[1]}, amount: {amount}")
            conn.rollback()
            cursor.close()
            conn.close()
            return make_response(f"balance=insufficient funds", 400)

    elif action == "balance":
        cursor.execute("SELECT balance FROM users WHERE id = %s;", (user_id,))
        current_balance = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        return make_response(f"balance={current_balance}", 200)

    elif action == "close":
        # Delete all sessions for the user
        cursor.execute("DELETE FROM sessions WHERE user_id = %s;", (user_id,))

        # Delete the user
        cursor.execute("DELETE FROM users WHERE id = %s;", (user_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        return make_response("Account closed", 200)

    log_security_event(app, request.remote_addr, f"Invalid action attempted: {action}")
    cursor.close()
    conn.close()
    return make_response("Invalid action", 400)

@app.route('/logout')
def logout():
    cookie = request.cookies.get('session')
    
    if cookie:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Remove the session from the database
        cursor.execute("DELETE FROM sessions WHERE cookie = %s;", (cookie,))
        conn.commit()
        
        cursor.close()
        conn.close()
    
    response = make_response("Logged out", 200)
    response.delete_cookie('session')
    return response

@app.route('/')
def index():
    return "Welcome to the bank!"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
