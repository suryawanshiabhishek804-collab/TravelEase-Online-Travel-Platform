# TravelEase – Online Travel Platform

A college-level full-stack travel platform demonstration built with Python Flask, SQLite, SQLAlchemy, HTML, CSS, JavaScript and Bootstrap.

## Features
- Responsive travel homepage
- Destination and hotel search
- Travel package listings
- User registration, login and logout
- Password hashing
- Booking creation and booking history
- Simulated payment confirmation (no real money is collected)
- Admin dashboard and booking status management
- Contact form

## Requirements
- Python 3.10+
- Internet connection for Bootstrap, Font Awesome, Google Fonts and remote sample photos

## Setup (Windows)
1. Extract the ZIP file.
2. Open the `TravelEase` folder in VS Code.
3. Open Terminal in that folder.
4. Create a virtual environment:

   `python -m venv venv`

5. Activate it:

   `venv\\Scripts\\activate`

6. Install dependencies:

   `pip install -r requirements.txt`

7. Run:

   `python app.py`

8. Open `http://127.0.0.1:5000` in your browser.

The SQLite database is created automatically on first run and sample data is inserted.

## Demo admin account
- Email: `admin@travelease.local`
- Password: `Admin@12345`

Change the demo admin password and `SECRET_KEY` before any real deployment. These credentials are for local academic demonstration only.

## Important notes
- The payment step is simulated for academic demonstration. It does not connect to a payment provider and must not be used to collect real card details.
- Sample destination photographs are loaded from Unsplash URLs and require internet access.
- This is a learning project starter. Before public production deployment, add CSRF protection to every form, rate limiting, stronger configuration management, email verification, logging, tests, and a real production database.
