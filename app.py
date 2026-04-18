from flask import Flask, render_template, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'dealzim-secret-key-change-later'

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/post', methods=['GET', 'POST'])
def post():
    return render_template('post.html')

@app.route('/listing/<int:id>')
def listing(id):
    # Placeholder listing data for now
    listing = {
        'id': id,
        'title': 'Sample Product',
        'price': '5,000',
        'description': 'This is a sample product description.',
        'seller': 'testuser',
        'location': 'University of Lagos',
        'date': 'April 2026'
    }
    whatsapp_url = (
        f"https://wa.me/?text="
        f"*{listing['title']}*%0A"
        f"Price: ₦{listing['price']}%0A"
        f"Seller: @{listing['seller']}%0A"
        f"Location: {listing['location']}%0A"
        f"Posted via Dealzim%0A"
        f"👉 http://127.0.0.1:5000/listing/{listing['id']}"
    )
    return render_template('listing.html', listing=listing, whatsapp_url=whatsapp_url)

@app.route('/dashboard')
def dashboard():
    # Placeholder user data for now
    user = {
        'username': 'testuser',
        'fullname': 'Test User',
        'location': 'University of Lagos',
        'whatsapp': '+2340000000000'
    }
    return render_template('dashboard.html', user=user)

if __name__ == '__main__':
    app.run(debug=True)
