import os

from flask import Flask, request, session, render_template, flash, redirect, url_for,logging
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
            return redirect(url_for('index'))
        else:
            return render_template("error.html")  

    return render_template("login.html")      
