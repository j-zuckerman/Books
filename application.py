import os
import requests

from flask import Flask, request, session, jsonify, render_template, flash, redirect, url_for,logging
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from passlib.hash import sha256_crypt

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
    books = db.execute("SELECT * FROM books").fetchall()
    return render_template("index.html", books=books)

@app.route("/register", methods =['GET', 'POST'])
def register():
    form = request.form

    if request.method == 'POST':
        name = form.get('name')
        password = sha256_crypt.encrypt(str(form.get('password')))
        db.execute("INSERT INTO users(name, password) VALUES(:name, :password)",{"name": name, "password": password})
        db.commit()
        print(f"Added user with name {name} and password: {password}.")
        return redirect(url_for("index"))
        
    return render_template("register.html", form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    form = request.form
    if request.method == 'POST':
        name = form.get('name')
        password_entered = form.get('password')

        account = db.execute('SELECT * from users WHERE name =:name',{'name': name}).fetchone()
        
        #Extract encrypted password from account
        password = account[2]
        print(password)
        if account is None:
            return render_template("error.html")
        print(password_entered)
        if sha256_crypt.verify(password_entered, password):
            # Passed
            session['logged_in'] = True
            session['username'] = name
            return redirect(url_for('search'))
        else:
            return render_template("error.html")  

    return render_template("login.html")      

@app.route('/search', methods = ['POST', 'GET'])
def search():
    form = request.form
    results = None
    if request.method == 'POST':
        title = form.get("title")
        author = form.get("author")
        isbn = form.get("isbn")

        results = db.execute('Select * from books WHERE title =:title AND author =:author AND isbn =:isbn', 
        {'title': title, 'author': author, 'isbn':isbn}).fetchall()


    return render_template("search.html", results =results)

@app.route('/book/<string:isbn>', methods = ['POST', 'GET'])
def book(isbn):
   
    res = requests.get("http://localhost:5000/api/%s" % isbn)
    goodReadsRes = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "ByIHq0mOFio269JypMnkTg", "isbns": isbn})
    data = res.json()
    goodReadsData = goodReadsRes.json()
    print(data)
    print(goodReadsData)

    form = request.form
    if request.method == 'POST':
        rating = form.get('rating')
        review = form.get('review')
        book_id = data.book_id
        db.execute("INSERT INTO reviews(rating, review, book_id) VALUES(:rating, :review, :book_id)",{"rating": rating, "review": review, "book_id": book_id})
        db.commit()

    return render_template("book.html", book = data)

@app.route('/api/<string:isbn>')
def book_api(isbn):
    """Return details about a single book."""
    bookInformation = db.execute('SELECT * FROM books WHERE isbn =:isbn', {'isbn': isbn}).fetchone()
    
    if bookInformation is None:
        return jsonify({"error": "Invalid isbn"}), 404

    book_id = bookInformation.id
    bookReviews = db.execute('Select rating, review FROM reviews WHERE book_id =:book_id ',{'book_id': book_id}).fetchall()
    
    #Calculate average rating and gather all reviews 
    rating_sum = 0
    average_rating = None
    reviews = []
    if len(bookReviews) > 0:
        for bookReview in bookReviews:
            rating_sum += bookReview.rating
            reviews.append(bookReview.review)
    
        average_rating = rating_sum/len(bookReviews)

    return jsonify({
            "book_id": bookInformation.id,
              "title": bookInformation.title,
              "author": bookInformation.author,
              "year": bookInformation.year,
              "isbn": bookInformation.isbn,
              "reviews": reviews,
              "average_rating": average_rating
          })
   