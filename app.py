from flask import Flask, render_template, redirect, url_for, session, flash,request,jsonify
from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,SubmitField
from wtforms.validators import DataRequired, Email, ValidationError,Regexp
import bcrypt
from flask_mysqldb import MySQL
import re

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'carparking'
app.secret_key = 'moni'

mysql = MySQL(app)

class RegisterForm(FlaskForm):
    name = StringField("Name",validators=[DataRequired()])
    phone = StringField("Phone", validators=[
        DataRequired(), 
        Regexp(r'^\d{10}$', message="Phone number must be 10 digits.")
    ])
    email = StringField("Email",validators=[DataRequired(), Email()])
    password = PasswordField("Password",validators=[DataRequired()])
    submit = SubmitField("Register")

    def validate_email(self,field):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users where email=%s",(field.data,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            raise ValidationError('Email Already Taken')

class LoginForm(FlaskForm):
    email = StringField("Email",validators=[DataRequired(), Email()])
    password = PasswordField("Password",validators=[DataRequired()])
    submit = SubmitField("Login")



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register',methods=['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        phone=form.phone.data
        email = form.email.data
        password = form.password.data

        hashed_password = bcrypt.hashpw(password.encode('utf-8'),bcrypt.gensalt())

        # store data into database 
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users (name,phone,email,password) VALUES (%s,%s,%s,%s)",(name,phone,email,hashed_password))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('login'))
        

    return render_template('register.html',form=form)

@app.route('/login',methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s",(email,))
        user = cursor.fetchone()
        cursor.close()
        if user and bcrypt.checkpw(password.encode('utf-8'), user[4].encode('utf-8')):
            session['user_id'] = user[0]
            session['user'] = user[3] 
            return redirect(url_for('slot'))
        else:
            flash("Login failed. Please check your email and password")
            return redirect(url_for('login'))

    return render_template('login.html',form=form)



@app.route('/dashboards')
def dashboards():
    if 'user_id' in session:
        user_id = session['user_id']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users where user_id=%s",(user_id,))
        user = cursor.fetchone()
        
        cursor.execute("SELECT bid, bvehicleno, bdate, bfromtime, btotime FROM bookingdetails WHERE user_id = %s", (user_id,))
        bookings = cursor.fetchall()
        cursor.close()

        if user:
            return render_template('dashboard.html',user=user,bookings=bookings)
            
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear() 
    session.pop('user_id', None)
    session.pop('user', None)
    flash("You have been logged out successfully.")
    return redirect(url_for('login'))

@app.route('/booking', methods=['POST', 'GET'])
def book():
    if 'user_id' in session:
        if request.method == 'POST':
            bvehicleno = request.form['bvehicleno']
            bdate = request.form['bdate']
            bfromtime = request.form['bfromtime']
            btotime = request.form['btotime']
            user_id = session['user_id']

            if not re.match(r'^[A-Z]{2}\d{2}[A-Z]{2}\d{4}$', bvehicleno):
                flash('Invalid vehicle number format. Please use the format XX00XX0000.')
                return redirect(url_for('book'))
            

            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO BOOKINGDETAILS (user_id,bvehicleno, bdate, bfromtime, btotime) VALUES (%s,%s, %s, %s, %s)",
                           (user_id,bvehicleno, bdate, bfromtime, btotime))
            mysql.connection.commit()
            cursor.close()
            return redirect(url_for('dashboard'))

        return render_template('book.html')
    return redirect(url_for('login'))

@app.route("/display")
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']

       
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        

        
        cursor.execute("SELECT bid, bvehicleno, bdate, bfromtime, btotime FROM bookingdetails WHERE user_id = %s", (user_id,))
        bookings = cursor.fetchall()
        
        cursor.close()

        if user:
            return render_template('dashboard.html', user=user, bookings=bookings)

    return redirect(url_for('login'))

@app.route('/slot')
def slot():
    return render_template('selslot.html')

space_count = 0

@app.route('/update_space', methods=['POST'])
def update_space():
    global space_count
    data = request.get_json()
    if not data:
        return jsonify({'status': 'failure', 'message': 'No JSON data received'}), 400
    
    space = data.get('space')
    if space is not None:
        space_count = space
        print(f"Received space data: {space}")
        return jsonify({'status': 'success', 'space': space})
    else:
        return jsonify({'status': 'failure', 'message': 'No space data received'}), 400

@app.route('/get_space', methods=['GET'])
def get_space():
    return jsonify({'space': space_count})



if __name__ == '__main__':
    app.run(debug=True)