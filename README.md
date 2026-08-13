# 📦 Retrix — E-commerce Analytics Platform for Sellers

> A powerful, data-driven analytics platform built for e-commerce sellers to track orders, returns, revenue, and product performance — all in one place.

---

## 🚀 Features

- **Seller Authentication** — Register, login, OTP email verification, forgot/reset password
- **Dashboard** — Overview of total orders, returns, revenue, net profit with charts
- **Catalogue Analysis** — Breakdown by catalogue ID with return rates and profit margins
- **SKU Analysis** — Per-SKU deep dive into performance, return reasons, and trends
- **P&L Report** — Profit and loss analysis with date-range filtering
- **Seller Comparison** — Compare performance across multiple CSV datasets
- **CSV Upload & Management** — Upload, switch between, and delete datasets
- **Profile & Settings** — Update profile photo, name, store info, and delete account
- **Secure Sessions** — No-cache headers prevent access after logout via back button

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask 3.0 |
| Database | SQLite (default) / PostgreSQL |
| ORM | Flask-SQLAlchemy |
| Data Processing | Pandas, NumPy |
| Email (OTP) | Gmail SMTP via smtplib |
| Image Handling | Pillow |
| Frontend | HTML, CSS, Bootstrap 5, Chart.js |

---

## 📁 Project Structure

```
Retrix/
├── app.py                  # Main Flask application (routes, models, logic)
├── config.py               # App configuration class
├── run.py                  # Entry point to run the app
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Build system config
├── .env                    # Environment variables (not committed)
├── .env.example            # Example environment file
├── .gitignore
│
├── templates/              # Jinja2 HTML templates
│   ├── home.html
│   ├── splash.html
│   ├── about.html
│   ├── login_selection.html
│   ├── seller_register.html
│   ├── verify_otp.html
│   ├── seller_login.html
│   ├── seller_forgot_password.html
│   ├── seller_reset_password.html
│   ├── seller_registration_success.html
│   ├── seller_dashboard.html
│   ├── catalogue.html
│   ├── sku_analysis.html
│   ├── pl.html
│   ├── seller_comparison.html
│   └── seller_settings.html
│
├── static/                 # Static assets (CSS, JS, images)
│   └── uploads/
│       └── profile/        # Seller profile photos
│
└── uploads/                # Uploaded CSV datasets
    └── profile/
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository

`ash
git clone https://github.com/your-username/retrix.git
cd retrix
`

### 2. Create a virtual environment

`ash
python -m venv env
# Windows
env\Scripts\activate
# macOS/Linux
source env/bin/activate
`

### 3. Install dependencies

`ash
pip install -r requirements.txt
`

### 4. Configure environment variables

Copy .env.example to .env and fill in your values:

`env
# Flask
SECRET_KEY=your-secret-key-here

# Email (Gmail SMTP for OTP)
EMAIL_USER=your-gmail@gmail.com
EMAIL_PASS=your-16-char-app-password

# Database (optional — uses SQLite by default)
# DATABASE_URL=postgresql://user:password@localhost/retrix
`

> **Gmail App Password setup:**
> 1. Enable 2-Step Verification on your Google account
> 2. Go to https://myaccount.google.com/apppasswords
> 3. Create an App Password for Mail
> 4. Paste the 16-character password into EMAIL_PASS

### 5. Run the application

`ash
python app.py
`

The app will start at **http://127.0.0.1:5000**

---

## 📊 CSV Format

Upload CSV files with the following required columns:

| Column | Description |
|---|---|
| order_id | Unique order identifier |
| order_date | Date of the order |
| order_status | delivered or returned |
| order_price | Order value in Rs. |
| return_cost | Cost of return in Rs. |
| return_reason | Reason for return |
| catalogue_id | Product catalogue ID |
| sku_description | SKU / product name |
| quantity | Quantity ordered |
| category | Product category |

---

## 🔗 Application Routes

| Route | Description |
|---|---|
| / | Home page |
| /about | About page |
| /seller-register | Seller registration |
| /verify-otp | OTP email verification |
| /seller-login | Seller login |
| /seller-forgot-password | Forgot password |
| /seller-reset-password | Reset password |
| /seller-dashboard | Main dashboard (protected) |
| /catalogue | Catalogue analysis (protected) |
| /sku-analysis | SKU performance analysis (protected) |
| /pl | Profit and Loss report (protected) |
| /seller-comparison | Multi-dataset comparison (protected) |
| /seller-settings | Account settings (protected) |
| /seller-upload-csv | Upload CSV dataset (protected) |

---

## 🔐 Security

- Passwords are hashed using Werkzeug PBKDF2-SHA256
- OTP codes expire after 5 minutes
- Protected routes use no-cache HTTP headers — pressing Back after logout redirects to login
- Session-based authentication with Flask sessions

---

## 📧 OTP Flow

1. Seller registers → OTP sent to their email via Gmail SMTP
2. Seller enters OTP on /verify-otp page
3. On success → account marked as verified → redirected to login
4. Forgot password → OTP sent → verified → new password set

---
