from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import re
import os
import csv
import io
import random
import string
import pandas as pd
from PIL import Image
import io as pil_io

# Set secret key before loading config
os.environ['SECRET_KEY'] = 'hard-to-guess-string'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard-to-guess-string'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROFILE_PHOTO_FOLDER'] = 'uploads/profile'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///retrix.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
ALLOWED_EXTENSIONS = {'csv'}
ALLOWED_PHOTO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'jfif', 'gif'}

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROFILE_PHOTO_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

# Database Models
class Seller(db.Model):
    __tablename__ = 'sellers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    store_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    unique_code = db.Column(db.String(6), unique=True, nullable=False)
    profile_icon = db.Column(db.String(50), default='fa-user')
    profile_photo = db.Column(db.String(200), nullable=True)

class CSVUpload(db.Model):
    __tablename__ = 'csv_uploads'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    seller_id = db.Column(db.Integer, nullable=True)
    filename = db.Column(db.String(200), nullable=False)
    original_name = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    upload_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    row_count = db.Column(db.Integer, default=0)

# Function to get upload statistics by date
def get_upload_stats_by_date(seller_id):
    """Get CSV upload counts grouped by date for a seller"""
    uploads = CSVUpload.query.filter_by(seller_id=seller_id).all()
    date_counts = {}
    for upload in uploads:
        date_key = upload.upload_date.strftime('%Y-%m-%d')
        if date_key in date_counts:
            date_counts[date_key] += 1
        else:
            date_counts[date_key] = 1
    return date_counts

# Helper function to check allowed file extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Password validation function
def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

# Function to generate unique 6-digit code
def generate_unique_code():
    while True:
        code = ''.join(random.choices(string.digits, k=6))
        # Ensure the code doesn't start with 0 (optional, but common practice)
        if code[0] == '0':
            continue
        # Check if code already exists (only check non-null values)
        existing = Seller.query.filter(Seller.unique_code != None, Seller.unique_code == code).first()
        if not existing:
            return code

# Login required decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'seller_id' not in session:
            return redirect(url_for('login_selection'))
        return f(*args, **kwargs)
    return decorated_function

def seller_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'seller_id' not in session:
            return redirect(url_for('seller_login'))
        return f(*args, **kwargs)
    return decorated_function

# CSV Processing Functions
def format_day(day):
    if 11 <= day <= 13:
        return f"{day}th"
    elif day % 10 == 1:
        return f"{day}st"
    elif day % 10 == 2:
        return f"{day}nd"
    elif day % 10 == 3:
        return f"{day}rd"
    else:
        return f"{day}th"

def get_latest_uploaded_file(seller_id):
    upload = CSVUpload.query.filter_by(seller_id=seller_id).order_by(CSVUpload.upload_date.desc()).first()
    if upload:
        return upload.filepath
    return None

def calculate_dashboard_metrics(csv_path):
    try:
        df = pd.read_csv(csv_path)
        
        total_orders = len(df)
        total_returns = (df["order_status"] == "returned").sum() if "order_status" in df.columns else 0
        return_percent = round((total_returns / total_orders) * 100, 2) if total_orders > 0 else 0
        
        net_sales = df['order_price'].sum() if 'order_price' in df.columns else 0
        return_cost = df['return_cost'].sum() if 'return_cost' in df.columns else 0
        net_profit = net_sales - return_cost
        
        # Line chart data
        if 'order_date' in df.columns:
            daily_sales = df.groupby("order_date").agg(
                total_amount=("order_price", "sum"),
                order_count=("order_price", "count")
            ).reset_index()
            
            chart_dates = daily_sales["order_date"].apply(
                lambda x: format_day(int(x.split("-")[0])) if isinstance(x, str) and "-" in str(x) else str(x)
            ).tolist()
            chart_amounts = daily_sales["total_amount"].tolist()
            chart_order_counts = daily_sales["order_count"].tolist()
        else:
            chart_dates = []
            chart_amounts = []
            chart_order_counts = []
        
        # Pie chart data (Return Reasons)
        pie_labels = []
        pie_values = []
        if "order_status" in df.columns and "return_reason" in df.columns:
            returned_df = df[df["order_status"] == "returned"]
            if len(returned_df) > 0:
                reason_counts = returned_df["return_reason"].value_counts().reset_index()
                reason_counts.columns = ["return_reason", "count"]
                pie_labels = reason_counts["return_reason"].tolist()
                pie_values = reason_counts["count"].tolist()
        
        # Bar chart data (Top Catalogues)
        catalogue_labels = []
        catalogue_values = []
        if "catalogue_id" in df.columns and "order_status" in df.columns:
            returned_df = df[df["order_status"] == "returned"]
            if len(returned_df) > 0:
                top_catalogues = returned_df.groupby('catalogue_id').agg(
                    return_count=('order_id', "count")
                ).reset_index().sort_values('return_count', ascending=False).head(5)
                catalogue_labels = top_catalogues["catalogue_id"].astype(str).tolist()
                catalogue_values = top_catalogues["return_count"].tolist()
        
        # Bar chart data (Top SKUs)
        sku_labels = []
        sku_values = []
        if "sku_description" in df.columns and "order_status" in df.columns:
            returned_df = df[df["order_status"] == "returned"]
            if len(returned_df) > 0:
                top_skus = returned_df.groupby("sku_description").agg(
                    return_count=("order_id", "count")
                ).reset_index().sort_values("return_count", ascending=False).head(5)
                sku_labels = top_skus["sku_description"].tolist()
                sku_values = top_skus["return_count"].tolist()
        
        return {
            "total_orders": total_orders,
            "total_returns": total_returns,
            "return_percent": return_percent,
            "net_sales": net_sales,
            "return_cost": return_cost,
            "net_profit": net_profit,
            "chart_dates": chart_dates,
            "chart_amounts": chart_amounts,
            "chart_order_counts": chart_order_counts,
            "pie_labels": pie_labels,
            "pie_values": pie_values,
            "catalogue_labels": catalogue_labels,
            "catalogue_values": catalogue_values,
            "sku_labels": sku_labels,
            "sku_values": sku_values
        }
    except Exception as e:
        print(f"Error processing CSV: {e}")
        return {
            "total_orders": 0,
            "total_returns": 0,
            "return_percent": 0,
            "net_sales": 0,
            "return_cost": 0,
            "net_profit": 0,
            "chart_dates": [],
            "chart_amounts": [],
            "chart_order_counts": [],
            "pie_labels": [],
            "pie_values": [],
            "catalogue_labels": [],
            "catalogue_values": [],
            "sku_labels": [],
            "sku_values": []
        }

# Routes
@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/login-selection')
def login_selection():
    return render_template('login_selection.html')

@app.route('/seller-register', methods=['GET', 'POST'])
def seller_register():
    if request.method == 'POST':
        name = request.form['name']
        store_name = request.form['store_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validate password
        valid, message = validate_password(password)
        if not valid:
            flash(message, 'danger')
            return render_template('seller_register.html')
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('seller_register.html')
        
        # Check if email already exists
        existing_seller = Seller.query.filter_by(email=email).first()
        if existing_seller:
            flash('Email already registered', 'danger')
            return render_template('seller_register.html')
        
        # Generate unique 6-digit code
        unique_code = generate_unique_code()
        
        # Create new seller
        hashed_password = generate_password_hash(password)
        new_seller = Seller(name=name, store_name=store_name, email=email, password=hashed_password, unique_code=unique_code)
        db.session.add(new_seller)
        db.session.commit()
        
        # Store the unique code in session to display on success page
        session['seller_registration_success'] = True
        session['seller_unique_code'] = unique_code
        session['seller_store_name'] = store_name
        
        return redirect(url_for('seller_registration_success'))
    
    return render_template('seller_register.html')

@app.route('/seller-registration-success')
def seller_registration_success():
    if not session.get('seller_registration_success'):
        return redirect(url_for('seller_register'))
    
    unique_code = session.get('seller_unique_code')
    store_name = session.get('seller_store_name')
    
    # Clear the registration success flags
    session.pop('seller_registration_success', None)
    session.pop('seller_unique_code', None)
    session.pop('seller_store_name', None)
    
    return render_template('seller_registration_success.html', unique_code=unique_code, store_name=store_name)

@app.route('/seller-login', methods=['GET', 'POST'])
def seller_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        seller = Seller.query.filter_by(email=email).first()
        
        if seller and check_password_hash(seller.password, password):
            session['seller_id'] = seller.id
            session['seller_name'] = seller.name
            flash('Login successful!', 'success')
            return redirect(url_for('seller_dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('seller_login.html')

@app.route('/seller-logout')
def seller_logout():
    session.pop('seller_id', None)
    session.pop('seller_name', None)
    flash('Logged out successfully', 'info')
    return redirect(url_for('login_selection'))

@app.route('/seller-forgot-password', methods=['GET', 'POST'])
def seller_forgot_password():
    if request.method == 'POST':
        store_name = request.form.get('store_name')
        email = request.form.get('email')
        unique_code = request.form.get('unique_code')
        
        # If unique_code is provided, we're in step 2 (code verification)
        if unique_code:
            seller_id = session.get('reset_seller_id')
            if not seller_id:
                flash('Please verify your account first', 'danger')
                return render_template('seller_forgot_password.html')
            
            seller = Seller.query.get(seller_id)
            if seller and seller.unique_code == unique_code:
                # Code verified, proceed to reset password
                return redirect(url_for('seller_reset_password'))
            else:
                flash('Invalid unique code. Please try again.', 'danger')
                return render_template('seller_forgot_password.html', 
                                      store_name=store_name, 
                                      email=email, 
                                      step=2,
                                      seller_id=seller_id)
        else:
            # Step 1: Verify store name and email
            seller = Seller.query.filter_by(store_name=store_name, email=email).first()
            
            if seller:
                session['reset_seller_id'] = seller.id
                # Show step 2 (unique code verification)
                return render_template('seller_forgot_password.html', 
                                      store_name=store_name, 
                                      email=email, 
                                      step=2,
                                      seller_id=seller.id)
            else:
                flash('Store name and email do not match any account', 'danger')
    
    return render_template('seller_forgot_password.html')

@app.route('/seller-reset-password', methods=['GET', 'POST'])
def seller_reset_password():
    if 'reset_seller_id' not in session:
        return redirect(url_for('seller_forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # Validate password
        valid, message = validate_password(new_password)
        if not valid:
            flash(message, 'danger')
            return render_template('seller_reset_password.html')
        
        # Check if passwords match
        if new_password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('seller_reset_password.html')
        
        # Update password
        seller = Seller.query.get(session['reset_seller_id'])
        seller.password = generate_password_hash(new_password)
        db.session.commit()
        
        session.pop('reset_seller_id', None)
        flash('Password reset successful! Please login.', 'success')
        return redirect(url_for('seller_login'))
    
    return render_template('seller_reset_password.html')

@app.route('/seller-dashboard/view/<int:upload_id>')
@seller_login_required
def seller_dashboard_view(upload_id):
    seller = Seller.query.get(session.get('seller_id'))
    uploads = CSVUpload.query.filter_by(seller_id=session.get('seller_id')).order_by(CSVUpload.upload_date.desc()).all()
    
    # Get upload by ID
    upload = CSVUpload.query.filter_by(id=upload_id, seller_id=session.get('seller_id')).first()
    if upload and os.path.exists(upload.filepath):
        data = calculate_dashboard_metrics(upload.filepath)
    else:
        flash('File not found', 'danger')
        return redirect(url_for('seller_dashboard'))
    
    # Calculate current index for navigation
    upload_ids = [u.id for u in uploads]
    current_index = upload_ids.index(upload_id) if upload_id in upload_ids else 0
    
    return render_template('seller_dashboard.html', name=seller.name, uploads=uploads, data=data, seller=seller, current_upload_id=upload_id, current_index=current_index)

@app.route('/seller-dashboard')
@seller_login_required
def seller_dashboard():
    seller = Seller.query.get(session.get('seller_id'))
    uploads = CSVUpload.query.filter_by(seller_id=session.get('seller_id')).order_by(CSVUpload.upload_date.desc()).all()
    
    # Get data from latest uploaded file
    csv_path = get_latest_uploaded_file(session.get('seller_id'))
    if csv_path and os.path.exists(csv_path):
        data = calculate_dashboard_metrics(csv_path)
    else:
        data = {
            "total_orders": 0,
            "total_returns": 0,
            "return_percent": 0,
            "net_sales": 0,
            "return_cost": 0,
            "net_profit": 0,
            "chart_dates": [],
            "chart_amounts": [],
            "chart_order_counts": [],
            "pie_labels": [],
            "pie_values": [],
            "catalogue_labels": [],
            "catalogue_values": [],
            "sku_labels": [],
            "sku_values": []
        }
    
    # Get current index (0 for latest)
    upload_ids = [u.id for u in uploads] if uploads else []
    current_index = 0
    current_upload_id = uploads[0].id if uploads else None
    
    return render_template('seller_dashboard.html', name=seller.name, uploads=uploads, data=data, seller=seller, current_upload_id=current_upload_id, current_index=current_index)

@app.route('/seller-upload-csv', methods=['GET', 'POST'])
@seller_login_required
def seller_upload_csv():
    uploads = CSVUpload.query.filter_by(seller_id=session.get('seller_id')).order_by(CSVUpload.upload_date.desc()).all()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(str(session.get('seller_id')) + '_' + file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Count rows in CSV
            try:
                df = pd.read_csv(filepath)
                row_count = len(df)
            except:
                row_count = 0
            
            # Save to database
            upload = CSVUpload(
                seller_id=session.get('seller_id'),
                filename=filename,
                original_name=file.filename,
                filepath=filepath,
                row_count=row_count
            )
            db.session.add(upload)
            db.session.commit()
            
            flash(f'File uploaded successfully! {row_count} rows processed.', 'success')
            return redirect(url_for('seller_dashboard'))
        else:
            flash('Invalid file type. Please upload a CSV file.', 'danger')
    
    return render_template('seller_dashboard.html', name=session.get('seller_name'), show_upload=True, uploads=uploads)

@app.route('/download-csv/<filename>')
def download_csv(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

@app.route('/delete-csv/<int:upload_id>')
def delete_csv(upload_id):
    upload = CSVUpload.query.get_or_404(upload_id)
    
    # Delete file from disk
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], upload.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    
    # Delete from database
    db.session.delete(upload)
    db.session.commit()
    
    flash('File deleted successfully', 'info')
    
    # Redirect back to seller dashboard
    return redirect(url_for('seller_dashboard'))

@app.route('/seller-settings')
@seller_login_required
def seller_settings():
    seller = Seller.query.get(session.get('seller_id'))
    upload_stats = get_upload_stats_by_date(seller.id)
    return render_template('seller_settings.html', seller=seller, upload_stats=upload_stats)

@app.route('/seller-update-profile', methods=['POST'])
@seller_login_required
def seller_update_profile():
    seller = Seller.query.get(session.get('seller_id'))
    
    name = request.form.get('name')
    store_name = request.form.get('store_name')
    email = request.form.get('email')
    profile_icon = request.form.get('profile_icon', 'fa-user')
    remove_photo = request.form.get('remove_photo', 'false') == 'true'
    
    # Check if email is being changed and if it already exists
    if email != seller.email:
        existing_email = Seller.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered by another account', 'danger')
            return redirect(url_for('seller_settings'))
    
    # Check if store name is being changed and if it already exists
    if store_name != seller.store_name:
        existing_store = Seller.query.filter_by(store_name=store_name).first()
        if existing_store:
            flash('Store name already taken', 'danger')
            return redirect(url_for('seller_settings'))
    
    # Handle profile photo upload
    if 'profile_photo' in request.files:
        file = request.files['profile_photo']
        if file and file.filename != '':
            # Check file extension
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            if ext in ALLOWED_PHOTO_EXTENSIONS:
                # Generate unique filename - always use jpg extension for consistency
                filename = f"profile_{seller.id}.jpg"
                filepath = os.path.join(app.config['PROFILE_PHOTO_FOLDER'], filename)
                
                # Resize and save image
                try:
                    img = Image.open(file)
                    # Convert to RGB if necessary (handles JFIF, PNG, GIF and other formats)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img = img.resize((200, 200), Image.Resampling.LANCZOS)
                    img.save(filepath, 'JPEG', quality=95)
                    seller.profile_photo = filename
                except Exception as e:
                    print(f"Error saving profile photo: {e}")
                    flash('Error saving profile photo. Please try a different format.', 'danger')
    
    # Handle remove photo request
    if remove_photo and seller.profile_photo:
        filepath = os.path.join(app.config['PROFILE_PHOTO_FOLDER'], seller.profile_photo)
        if os.path.exists(filepath):
            os.remove(filepath)
        seller.profile_photo = None
    
    # Update seller profile
    seller.name = name
    seller.store_name = store_name
    seller.email = email
    seller.profile_icon = profile_icon
    db.session.commit()
    
    # Update session
    session['seller_name'] = name
    
    flash('Profile updated successfully', 'success')
    return redirect(url_for('seller_dashboard'))

@app.route('/seller-delete-account', methods=['POST'])
@seller_login_required
def seller_delete_account():
    seller_id = session.get('seller_id')
    seller = Seller.query.get(seller_id)
    
    if seller:
        # Delete profile photo if exists
        if seller.profile_photo:
            filepath = os.path.join(app.config['PROFILE_PHOTO_FOLDER'], seller.profile_photo)
            if os.path.exists(filepath):
                os.remove(filepath)
        
        # Delete all CSV uploads for this seller
        uploads = CSVUpload.query.filter_by(seller_id=seller_id).all()
        for upload in uploads:
            # Delete file from disk
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], upload.filename)
            if os.path.exists(filepath):
                os.remove(filepath)
            db.session.delete(upload)
        
        # Delete seller from database
        db.session.delete(seller)
        db.session.commit()
        
        # Clear session
        session.clear()
        
        flash('Your account has been permanently deleted', 'info')
    
    return redirect(url_for('login_selection'))

@app.route('/profile-photo/<int:seller_id>')
def get_profile_photo(seller_id):
    seller = Seller.query.get(seller_id)
    if seller and seller.profile_photo:
        filepath = os.path.join(app.config['PROFILE_PHOTO_FOLDER'], seller.profile_photo)
        if os.path.exists(filepath):
            return send_file(filepath)
    # Return default icon as SVG
    return send_file(
        pil_io.BytesIO(
            b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="200" height="200">'
            b'<path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>'
            b'</svg>'),
        mimetype='image/svg+xml'
    )

# Initialize database on first request
@app.before_request
def initialize_database():
    if not hasattr(initialize_database, 'initialized'):
        initialize_database.initialized = True
        with app.app_context():
            db.create_all()

# Comparison functions
def parse_order_date(date_str):
    """Parse date string in DD-MM-YYYY format"""
    try:
        from datetime import datetime
        return datetime.strptime(date_str, '%d-%m-%Y')
    except:
        return None

def get_all_csv_files_for_seller(seller_id):
    """Get all CSV files uploaded by a seller"""
    uploads = CSVUpload.query.filter_by(seller_id=seller_id).order_by(CSVUpload.upload_date.desc()).all()
    return [upload.filepath for upload in uploads if os.path.exists(upload.filepath)]

def get_month_comparison_data(seller_id, from_month, from_year, to_month, to_year):
    """Get month-wise comparison data from all CSV files for a seller"""
    try:
        import pandas as pd
        from datetime import datetime
        
        # Get all CSV files for the seller
        csv_files = get_all_csv_files_for_seller(seller_id)
        
        if not csv_files:
            return None
        
        # Read and merge all CSV files
        dataframes = []
        for csv_path in csv_files:
            try:
                df = pd.read_csv(csv_path)
                dataframes.append(df)
            except Exception as e:
                print(f"Error reading {csv_path}: {e}")
        
        if not dataframes:
            return None
        
        # Concatenate all dataframes
        df = pd.concat(dataframes, ignore_index=True)
        
        # Parse dates
        df['parsed_date'] = df['order_date'].apply(parse_order_date)
        df = df.dropna(subset=['parsed_date'])
        
        # Extract year and month
        df['year'] = df['parsed_date'].apply(lambda x: x.year)
        df['month'] = df['parsed_date'].apply(lambda x: x.month)
        df['month_year'] = df['parsed_date'].apply(lambda x: f"{x.strftime('%B')} {x.year}")
        
        # Filter by date range
        from_date = datetime(from_year, from_month, 1)
        
        # Get the last day of to_month
        if to_month == 12:
            to_end_date = datetime(to_year + 1, 1, 1)
        else:
            to_end_date = datetime(to_year, to_month + 1, 1)
        
        df = df[(df['parsed_date'] >= from_date) & (df['parsed_date'] < to_end_date)]
        
        if df.empty:
            return None
        
        # Group by month
        monthly_data = df.groupby(['year', 'month', 'month_year']).agg({
            'order_id': 'count',
            'quantity': 'sum',
            'order_price': 'sum',
            'return_cost': 'sum'
        }).reset_index()
        
        monthly_data.columns = ['year', 'month', 'month_year', 'total_orders', 'total_quantity', 'total_revenue', 'total_return_cost']
        
        # Calculate average order value
        monthly_data['avg_order_value'] = monthly_data['total_revenue'] / monthly_data['total_orders']
        
        # Count status types
        delivered = df[df['order_status'] == 'delivered'].groupby(['year', 'month']).size().reset_index(name='delivered_count')
        cancelled = df[df['order_status'] == 'cancelled'].groupby(['year', 'month']).size().reset_index(name='cancelled_count')
        returned = df[df['order_status'] == 'returned'].groupby(['year', 'month']).size().reset_index(name='returned_count')
        
        # Merge status counts
        monthly_data = monthly_data.merge(delivered, on=['year', 'month'], how='left')
        monthly_data = monthly_data.merge(cancelled, on=['year', 'month'], how='left')
        monthly_data = monthly_data.merge(returned, on=['year', 'month'], how='left')
        
        monthly_data['delivered_count'] = monthly_data['delivered_count'].fillna(0).astype(int)
        monthly_data['cancelled_count'] = monthly_data['cancelled_count'].fillna(0).astype(int)
        monthly_data['returned_count'] = monthly_data['returned_count'].fillna(0).astype(int)
        
        # Calculate return rate
        monthly_data['return_rate'] = (monthly_data['returned_count'] / monthly_data['total_orders'] * 100).round(2)
        
        # Sort by year and month
        monthly_data = monthly_data.sort_values(['year', 'month']).reset_index(drop=True)
        
        # Calculate month-over-month differences
        monthly_data['revenue_change'] = 0.0
        monthly_data['orders_change'] = 0.0
        monthly_data['return_rate_change'] = 0.0
        
        for i in range(1, len(monthly_data)):
            prev = monthly_data.iloc[i-1]
            curr = monthly_data.iloc[i]
            
            # Revenue change
            if prev['total_revenue'] > 0:
                monthly_data.loc[i, 'revenue_change'] = round(((curr['total_revenue'] - prev['total_revenue']) / prev['total_revenue'] * 100), 2)
            else:
                monthly_data.loc[i, 'revenue_change'] = 0
            
            # Orders change
            if prev['total_orders'] > 0:
                monthly_data.loc[i, 'orders_change'] = round(((curr['total_orders'] - prev['total_orders']) / prev['total_orders'] * 100), 2)
            else:
                monthly_data.loc[i, 'orders_change'] = 0
            
            # Return rate change
            monthly_data.loc[i, 'return_rate_change'] = round(curr['return_rate'] - prev['return_rate'], 2)
        
        # SKU comparison
        sku_data = df.groupby(['year', 'month', 'sku_description']).agg({
            'order_id': 'count',
            'quantity': 'sum',
            'order_price': 'sum',
            'return_cost': 'sum'
        }).reset_index()
        
        sku_data.columns = ['year', 'month', 'sku_description', 'orders', 'quantity', 'revenue', 'return_cost']
        
        # Add month_year to SKU data
        sku_data['month_year'] = sku_data.apply(lambda x: f"{datetime(x['year'], x['month'], 1).strftime('%B')} {x['year']}", axis=1)
        
        # Calculate SKU return rate
        sku_returned = df[df['order_status'] == 'returned'].groupby(['year', 'month', 'sku_description']).size().reset_index(name='returned_count')
        sku_data = sku_data.merge(sku_returned, on=['year', 'month', 'sku_description'], how='left')
        sku_data['returned_count'] = sku_data['returned_count'].fillna(0).astype(int)
        sku_data['return_rate'] = (sku_data['returned_count'] / sku_data['orders'] * 100).round(2)
        
        # Calculate insights
        insights = {}
        if len(monthly_data) >= 2:
            best_revenue = max(monthly_data.to_dict('records'), key=lambda x: x['total_revenue'])
            best_orders = max(monthly_data.to_dict('records'), key=lambda x: x['total_orders'])
            lowest_return = min(monthly_data.to_dict('records'), key=lambda x: x['return_rate'])
            
            insights = {
                'best_revenue_month': best_revenue['month_year'],
                'best_revenue_value': best_revenue['total_revenue'],
                'best_revenue_orders': best_revenue['total_orders'],
                'best_orders_month': best_orders['month_year'],
                'best_orders_count': best_orders['total_orders'],
                'lowest_return_month': lowest_return['month_year'],
                'lowest_return_rate': lowest_return['return_rate']
            }
        
        return {
            'monthly_data': monthly_data.to_dict(orient='records'),
            'sku_data': sku_data.to_dict(orient='records'),
            'months': monthly_data['month_year'].tolist(),
            'revenue_data': monthly_data['total_revenue'].tolist(),
            'orders_data': monthly_data['total_orders'].tolist(),
            'return_rate_data': monthly_data['return_rate'].tolist(),
            'revenue_changes': monthly_data['revenue_change'].tolist() if 'revenue_change' in monthly_data.columns else [],
            'orders_changes': monthly_data['orders_change'].tolist() if 'orders_change' in monthly_data.columns else [],
            'return_rate_changes': monthly_data['return_rate_change'].tolist() if 'return_rate_change' in monthly_data.columns else [],
            'insights': insights
        }
        
    except Exception as e:
        print(f"Error in comparison: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_available_years_months(seller_id):
    """Get available years and months from all CSV files"""
    try:
        import pandas as pd
        from datetime import datetime
        
        csv_files = get_all_csv_files_for_seller(seller_id)
        
        if not csv_files:
            return [2024, 2025, 2026]
        
        all_years = set()
        for csv_path in csv_files:
            try:
                df = pd.read_csv(csv_path)
                df['parsed_date'] = df['order_date'].apply(parse_order_date)
                df = df.dropna(subset=['parsed_date'])
                df['year'] = df['parsed_date'].apply(lambda x: x.year)
                all_years.update(df['year'].unique())
            except:
                continue
        
        return sorted(list(all_years)) if all_years else [2024, 2025, 2026]
        
    except Exception as e:
        print(f"Error getting available dates: {e}")
        return [2024, 2025, 2026]

# Routes
@app.route('/seller-comparison')
@seller_login_required
def seller_comparison():
    """Month-wise comparison page - compare two specific months"""
    seller = Seller.query.get(session.get('seller_id'))
    
    # Get all uploaded CSV files
    csv_files = get_all_csv_files_for_seller(session.get('seller_id'))
    
    if not csv_files:
        return render_template('seller_comparison.html', name=session.get('seller_name'), seller=seller, 
                              has_data=False, available_years=[])
    
    # Get available years
    available_years = get_available_years_months(session.get('seller_id'))
    
    # Check if filters are provided
    month1 = request.args.get('month1', type=int)
    year1 = request.args.get('year1', type=int)
    month2 = request.args.get('month2', type=int)
    year2 = request.args.get('year2', type=int)
    
    # If no filters provided, show empty state
    if not month1 or not year1 or not month2 or not year2:
        return render_template('seller_comparison.html', 
                              name=session.get('seller_name'), 
                              seller=seller,
                              has_data=False, 
                              available_years=available_years)
    
    # Get comparison data for the two selected months
    comparison_data = get_two_month_comparison_data(session.get('seller_id'), month1, year1, month2, year2)
    
    # Check if same month and year are selected
    if month1 == month2 and year1 == year2:
        return render_template('seller_comparison.html', 
                              name=session.get('seller_name'), 
                              seller=seller,
                              has_data=False, 
                              available_years=available_years,
                              error="Please select two different months for comparison.")
    
    if not comparison_data:
        return render_template('seller_comparison.html', 
                              name=session.get('seller_name'), 
                              seller=seller,
                              has_data=False, 
                              available_years=available_years,
                              error="No data found for one or both of the selected months.")
    
    return render_template('seller_comparison.html', 
                          name=session.get('seller_name'), 
                          seller=seller,
                          has_data=True,
                          comparison_data=comparison_data,
                          available_years=available_years,
                          month1=month1,
                          year1=year1,
                          month2=month2,
                          year2=year2)


def get_two_month_comparison_data(seller_id, month1, year1, month2, year2):
    """Get comparison data for two specific months"""
    try:
        import pandas as pd
        from datetime import datetime
        
        # Get all CSV files for the seller
        csv_files = get_all_csv_files_for_seller(seller_id)
        
        if not csv_files:
            return None
        
        # Read and merge all CSV files
        dataframes = []
        for csv_path in csv_files:
            try:
                df = pd.read_csv(csv_path)
                dataframes.append(df)
            except Exception as e:
                print(f"Error reading {csv_path}: {e}")
        
        if not dataframes:
            return None
        
        # Concatenate all dataframes
        df = pd.concat(dataframes, ignore_index=True)
        
        # Parse dates
        df['parsed_date'] = df['order_date'].apply(parse_order_date)
        df = df.dropna(subset=['parsed_date'])
        
        # Extract year, month, and day
        df['year'] = df['parsed_date'].apply(lambda x: x.year)
        df['month'] = df['parsed_date'].apply(lambda x: x.month)
        df['day'] = df['parsed_date'].apply(lambda x: x.day)
        
        # Filter for the two selected months
        df1 = df[(df['year'] == year1) & (df['month'] == month1)]
        df2 = df[(df['year'] == year2) & (df['month'] == month2)]
        
        if df1.empty and df2.empty:
            return None
        
        # Calculate daily revenue for month 1
        daily_revenue1 = {}
        if not df1.empty:
            daily_revenue1 = df1.groupby('day')['order_price'].sum().to_dict()
        
        # Calculate daily revenue for month 2
        daily_revenue2 = {}
        if not df2.empty:
            daily_revenue2 = df2.groupby('day')['order_price'].sum().to_dict()
        
        # Calculate metrics for month 1
        month1_data = {}
        if not df1.empty:
            # Get return reasons for month 1
            return_reasons1 = {}
            returned_df1 = df1[df1['order_status'] == 'returned']
            if not returned_df1.empty and 'return_reason' in returned_df1.columns:
                return_reasons1 = returned_df1['return_reason'].value_counts().to_dict()
            
            month1_data = {
                'month_year': f"{datetime(year1, month1, 1).strftime('%B')} {year1}",
                'total_orders': len(df1),
                'total_quantity': df1['quantity'].sum(),
                'total_revenue': df1['order_price'].sum(),
                'avg_order_value': df1['order_price'].sum() / len(df1) if len(df1) > 0 else 0,
                'delivered_count': len(df1[df1['order_status'] == 'delivered']),
                'cancelled_count': len(df1[df1['order_status'] == 'cancelled']),
                'returned_count': len(df1[df1['order_status'] == 'returned']),
                'return_cost': df1['return_cost'].sum() if 'return_cost' in df1.columns else 0,
                'return_rate': round((len(df1[df1['order_status'] == 'returned']) / len(df1) * 100), 2) if len(df1) > 0 else 0,
                'daily_revenue': daily_revenue1,
                'return_reasons': return_reasons1,
                'has_data': True
            }
        else:
            # Month 1 has no data - still create empty structure
            month1_data = {
                'month_year': f"{datetime(year1, month1, 1).strftime('%B')} {year1}",
                'total_orders': 0,
                'total_quantity': 0,
                'total_revenue': 0,
                'avg_order_value': 0,
                'delivered_count': 0,
                'cancelled_count': 0,
                'returned_count': 0,
                'return_cost': 0,
                'return_rate': 0,
                'daily_revenue': {},
                'return_reasons': {},
                'has_data': False
            }
        
        # Calculate metrics for month 2
        month2_data = {}
        if not df2.empty:
            # Get return reasons for month 2
            return_reasons2 = {}
            returned_df2 = df2[df2['order_status'] == 'returned']
            if not returned_df2.empty and 'return_reason' in returned_df2.columns:
                return_reasons2 = returned_df2['return_reason'].value_counts().to_dict()
            
            month2_data = {
                'month_year': f"{datetime(year2, month2, 1).strftime('%B')} {year2}",
                'total_orders': len(df2),
                'total_quantity': df2['quantity'].sum(),
                'total_revenue': df2['order_price'].sum(),
                'avg_order_value': df2['order_price'].sum() / len(df2) if len(df2) > 0 else 0,
                'delivered_count': len(df2[df2['order_status'] == 'delivered']),
                'cancelled_count': len(df2[df2['order_status'] == 'cancelled']),
                'returned_count': len(df2[df2['order_status'] == 'returned']),
                'return_cost': df2['return_cost'].sum() if 'return_cost' in df2.columns else 0,
                'return_rate': round((len(df2[df2['order_status'] == 'returned']) / len(df2) * 100), 2) if len(df2) > 0 else 0,
                'daily_revenue': daily_revenue2,
                'return_reasons': return_reasons2,
                'has_data': True
            }
        else:
            # Month 2 has no data - still create empty structure
            month2_data = {
                'month_year': f"{datetime(year2, month2, 1).strftime('%B')} {year2}",
                'total_orders': 0,
                'total_quantity': 0,
                'total_revenue': 0,
                'avg_order_value': 0,
                'delivered_count': 0,
                'cancelled_count': 0,
                'returned_count': 0,
                'return_cost': 0,
                'return_rate': 0,
                'daily_revenue': {},
                'return_reasons': {},
                'has_data': False
            }
        
        # Check if at least one month has data
        if not month1_data.get('has_data') and not month2_data.get('has_data'):
            return None
        
        # Calculate differences and percentage changes
        if month1_data and month2_data:
            revenue_diff = month2_data['total_revenue'] - month1_data['total_revenue']
            revenue_pct = round((revenue_diff / month1_data['total_revenue'] * 100), 2) if month1_data['total_revenue'] > 0 else 0
            
            orders_diff = month2_data['total_orders'] - month1_data['total_orders']
            orders_pct = round((orders_diff / month1_data['total_orders'] * 100), 2) if month1_data['total_orders'] > 0 else 0
            
            return_rate_diff = month2_data['return_rate'] - month1_data['return_rate']
            
            aov_diff = month2_data['avg_order_value'] - month1_data['avg_order_value']
            aov_pct = round((aov_diff / month1_data['avg_order_value'] * 100), 2) if month1_data['avg_order_value'] > 0 else 0
            
            comparison = {
                'revenue_change': revenue_diff,
                'revenue_change_pct': revenue_pct,
                'orders_change': orders_diff,
                'orders_change_pct': orders_pct,
                'return_rate_change': return_rate_diff,
                'aov_change': aov_diff,
                'aov_change_pct': aov_pct
            }
        else:
            comparison = {}
        
        return {
            'month1': month1_data,
            'month2': month2_data,
            'comparison': comparison
        }
        
    except Exception as e:
        print(f"Error in two-month comparison: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    app.run(debug=True)
