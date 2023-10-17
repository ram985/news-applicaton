from newsapi import NewsApiClient
from flask import Flask,redirect,url_for,render_template,request,flash,abort,session,send_file
from flask_session import Session
from key import secret_key,salt1,salt2
import flask_excel as excel
from stoken import token
from cmail import sendmail
from itsdangerous import URLSafeTimedSerializer
import mysql.connector
from io import BytesIO
import requests
from flask_mail import Mail, Message
from newsapi import NewsApiClient
app = Flask(__name__)
# key = 'f13cee9c9c63461f8381faab7019337f'
key = '29ad574b6c09412dbe7c7ae20d95373c'
#newsapi = NewsApiClient(api_key='f13cee9c9c63461f8381faab7019337f')
newsapi = NewsApiClient(api_key='29ad574b6c09412dbe7c7ae20d95373c')
app=Flask(__name__)
app.secret_key=secret_key
app.config['SESSION_TYPE']='filesystem'
Session(app)
excel.init_excel(app)
mydb=mysql.connector.connect(host='localhost',user='root',password='admin',db='newsapi')
response1 = requests.get("https://newsapi.org/v2/top-headlines?country=in", params={'apikey': key, 'category': 'business'}).json()
response2 = requests.get("https://newsapi.org/v2/top-headlines?country=in", params={'apikey': key, 'category': 'entertainment'}).json()
response3 = requests.get("https://newsapi.org/v2/top-headlines?country=in", params={'apikey': key, 'category': 'general'}).json()
response4 = requests.get("https://newsapi.org/v2/top-headlines?country=in", params={'apikey': key, 'category': 'health'}).json()
response5 = requests.get("https://newsapi.org/v2/top-headlines?country=in", params={'apikey': key, 'category': 'science'}).json()
response6 = requests.get("https://newsapi.org/v2/top-headlines?country=in", params={'apikey': key, 'category': 'sports'}).json()
response7 = requests.get("https://newsapi.org/v2/top-headlines?country=in", params={'apikey': key, 'category': 'technology'}).json()

'''db= os.environ['RDS_DB_NAME']
user=os.environ['RDS_USERNAME']
password=os.environ['RDS_PASSWORD']
host=os.environ['RDS_HOSTNAME']
port=os.environ['RDS_PORT']
with mysql.connector.connect(host=host,user=user,password=password,db=db) as conn:
    cursor=conn.cursor(buffered=True)
    cursor.execute('create table if not exists users(username varchar(15) primary key,password varchar(15),email varchar(80),email_status enum("confirmed","not confirmed"))')
    cursor.execute('create table if not exists notes(nid BINARY(16) PRIMARY KEY,title TINYTEXT,content TEXT,date TIMESTAMP DEFAULT CURRENT_TIMESTAMP on update current_timestamp,added_by VARCHAR(15),FOREIGN KEY (added_by) REFERENCES users(username))')
    cursor.execute('create table if not exists files(fid binary(16) primary key,extension varchar(8),filedata longblob,date timestamp default now() on update now(),added_by varchar(15), FOREIGN KEY (added_by) REFERENCES users(username))')
mydb=mysql.connector.connect(host=host,user=user,password=password,db=db)'''
@app.route('/')
def index():
    return render_template('title.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('user'):
        return redirect(url_for('home'))
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where username=%s',[username])
        count=cursor.fetchone()[0]
        if count==1:
            cursor.execute('select count(*) from users where username=%s and password=%s',[username,password])
            p_count=cursor.fetchone()[0]
            if p_count==1:
                session['user']=username
                cursor.execute('select email_status from users where username=%s',[username])
                status=cursor.fetchone()[0]
                cursor.close()
                if status!='confirmed':
                    return redirect(url_for('inactive'))
                else:
                    return redirect(url_for('home'))
            else:
                cursor.close()
                flash('invalid password')
                return render_template('login.html')
        else:
            cursor.close()
            flash('invalid username')
            return render_template('login.html')
    return render_template('login.html')
@app.route('/inactive')
def inactive():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            return redirect(url_for('home'))
        else:
            return render_template('inactive.html')
    else:
        return redirect(url_for('login'))
@app.route('/homepage',methods=['GET','POST'])
def home():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            if request.method=='POST':
                result=f"%{request.form['search']}%"
                cursor=mydb.cursor(buffered=True)
                cursor.execute("select bin_to_uuid(nid) as uid,title,date from notes where  title like %s  and added_by=%s",[result,username])
                data=cursor.fetchall()
                if len(data)==0:
                    data='empty'
                return render_template('table.html',data=data)
            return render_template('index.html')
        else:
            return redirect(url_for('inactive'))
    else:
        return redirect(url_for('login'))
@app.route('/resendconfirmation')
def resend():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.execute('select email from users where username=%s',[username])
        email=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('Email already confirmed')
            return redirect(url_for('home'))
        else:
            subject='Email Confirmation'
            confirm_link=url_for('confirm',token=token(email,salt1),_external=True)
            body=f"Please confirm your mail-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Confirmation link sent check your email')
            return redirect(url_for('inactive'))
    else:
        return redirect(url_for('login'))
@app.route('/registration',methods=['GET','POST'])
def registration():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        try:
            cursor.execute('insert into users (username,password,email) values(%s,%s,%s)',(username,password,email))
        except mysql.connector.IntegrityError:
            flash('Username or email is already in use')
            return render_template('registration.html')
        else:
            mydb.commit()
            cursor.close()
            subject='Email Confirmation'
            confirm_link=url_for('confirm',token=token(email,salt1),_external=True)
            body=f"Thanks for signing up.Follow this link-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Confirmation link sent check your email')
            return render_template('registration.html')
    return render_template('registration.html')
    
@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt1,max_age=120)
    except Exception as e:
        #print(e)
        abort(404,'Link expired')
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where email=%s',[email])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('Email already confirmed')
            return redirect(url_for('login'))
        else:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("update users set email_status='confirmed' where email=%s",[email])
            mydb.commit()
            flash('Email confirmation success')
            return redirect(url_for('login'))
@app.route('/forget',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where email=%s',[email])
        count=cursor.fetchone()[0]
        cursor.close()
        if count==1:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('SELECT email_status from users where email=%s',[email])
            status=cursor.fetchone()[0]
            cursor.close()
            if status!='confirmed':
                flash('Please Confirm your email first')
                return render_template('forgot.html')
            else:
                subject='Forget Password'
                confirm_link=url_for('reset',token=token(email,salt=salt2),_external=True)
                body=f"Use this link to reset your password-\n\n{confirm_link}"
                sendmail(to=email,body=body,subject=subject)
                flash('Reset link sent check your email')
                return redirect(url_for('login'))
        else:
            flash('Invalid email id')
            return render_template('forgot.html')
    return render_template('forgot.html')
@app.route('/reset/<token>',methods=['GET','POST'])
def reset(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt2,max_age=180)
    except:
        abort(404,'Link Expired')
    else:
        if request.method=='POST':
            newpassword=request.form['npassword']
            confirmpassword=request.form['cpassword']
            if newpassword==confirmpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update users set password=%s where email=%s',[newpassword,email])
                mydb.commit()
                flash('Reset Successful')
                return redirect(url_for('login'))
            else:
                flash('Passwords mismatched')
                return render_template('newpassword.html')
        return render_template('newpassword.html')

@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))


@app.route("/newshome", methods=['GET', 'POST'])
def newshome():
	if request.method == "POST":
		sources, domains = get_sources_and_domains()
		keyword = request.form["keyword"]
		related_news = newsapi.get_everything(q=keyword,
									sources=sources,
									domains=domains,
									language='en',
									sort_by='relevancy')
		no_of_articles = related_news['totalResults']
		if no_of_articles > 100:
			no_of_articles = 100
		all_articles = newsapi.get_everything(q=keyword,
									sources=sources,
									domains=domains,
									language='en',
									sort_by='relevancy',
									page_size = no_of_articles)['articles']
		return render_template("newshome.html", all_articles = all_articles,
							keyword=keyword)
	else:
		top_headlines = newsapi.get_top_headlines(country="in", language="en")
		total_results = top_headlines['totalResults']
		if total_results > 100:
			total_results = 100
		all_headlines = newsapi.get_top_headlines(country="in",
													language="en",
													page_size=total_results)['articles']
		return render_template("newshome.html", all_headlines = all_headlines)
	return render_template("newshome.html")
@app.route('/category/<category>',methods=['GET','POST'])
def category(category):
	if category=='business':
		return render_template('home.html',all_headlines=response1)
	if category=='entertainment':
		return render_template('home.html',all_headlines=response2)
	if category=='general':
		return render_template('home.html',all_headlines=response3)
	if category=='health':
		return render_template('home.html',all_headlines=response4)
	if category=='science':
		return render_template('home.html',all_headlines=response5)
	if category=='sports':
		return render_template('home.html',all_headlines=response6)
	if category=='technology':
		return render_template('home.html',all_headlines=response7)

if __name__ == "__main__":
	app.run(debug = True)














