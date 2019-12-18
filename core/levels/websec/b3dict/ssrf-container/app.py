from flask import Flask, flash, redirect, render_template, request, url_for, session, abort
import os
import random 


app = Flask(__name__)
app.secret_key = os.urandom(16)

rname = (os.getenv('USERNAME')) if os.getenv('USERNAME') else 'debug'
rpasswords = (os.getenv('PASSWORD')) if os.getenv('PASSWORD') else 'debug'
rusers={rname:rpasswords}


@app.route('/')
def index():
    if (not session.get('logged_in')) or (not session.get('user')):
        return redirect(url_for('login'))
    else:
        msg='You are successfully logged in. Welcome '+ session['user'] +'!' 
        return render_template('index.html', msg=msg)

@app.route('/login', methods=[ 'GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        #if request.form['username'] != 'admin' or request.form['password'] != 'secret':
        username=request.form['username']
        password=request.form['password']
        print(rusers)
        if username not in rusers or rusers[username] != password:
            error = 'Invalid credentials'
           
        else:
            session['logged_in'] = True
            session['user'] = username
            msg='You are successfully logged in. Welcome '+ session['user'] +'!'          
            #flash(msg)     
            return render_template('index.html', msg=msg)
    return render_template('login.html', error=error)

@app.route("/logout")
def logout():
    session['logged_in'] = False
    session['user'] = None
    return redirect(url_for('login'))




if __name__ == '__main__':
    app.secret_key = os.urandom(12)
    PORT = (os.getenv('PORT')) if os.getenv('PORT') else 8888
    app.run(host='0.0.0.0', port=PORT, debug=True)
    #app.run(host='127.0.0.1', port=8080, debug=True)

