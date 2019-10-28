from flask import Flask, flash, redirect, render_template, request, url_for, session, abort
import os
from users import users

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    else:
        return render_template('index.html')

@app.route('/login', methods=[ 'GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        #if request.form['username'] != 'admin' or request.form['password'] != 'secret':
        username=request.form['username']
        password=request.form['password']
        print(users)
        if username not in users or users[username] != password:
            error = 'Invalid credentials'
           
        else:
            session['logged_in'] = True
            session['user'] = username
            msg='You were successfully logged in. Welcome '+ session['user'] +'!'          
            flash(msg)     
            return redirect(url_for('index'))
    return render_template('login.html', error=error)

@app.route("/logout")
def logout():
    session['logged_in'] = False
    session['user'] = None
    return redirect(url_for('login'))




if __name__ == '__main__':
    app.secret_key = os.urandom(12)
    #app.run(host='127.0.0.1', port=8000, debug=True)
    app.run(host='0.0.0.0', port=80, debug=True)

