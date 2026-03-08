from flask import Flask, render_template, url_for, redirect, request
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length
from wtforms import SubmitField, FileField, EmailField, StringField, PasswordField
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, relationship
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from flask_bootstrap import Bootstrap5
import os
import requests
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play


class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
secret_key = secrets.token_urlsafe(64)
app.config['SECRET_KEY'] = secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///potatopotato.db'
featherlessapikey = os.getenv('FEATHERLESS_API_KEY')
elevenlabsapikey = os.getenv('ELEVENLABS_API_KEY')
db.init_app(app)
bootstrap = Bootstrap5(app)

class SignupForm(FlaskForm):
    email = EmailField('email', validators=[DataRequired()])
    username = StringField('username',validators=[DataRequired(), Length(
        min=5,max=20, message='username must be between 5 and 20 characters :D')])
    password = PasswordField('password', validators=[DataRequired(), Length(
        min=8,max=20, message='password must be between 8 and 20 characters :D')])
    submit = SubmitField('Submit')

class LoginForm(FlaskForm):
    username = StringField('username', validators=[DataRequired(), Length(
        min=5, max=20, message='username must be between 5 and 20 characters :D')])
    password = PasswordField('password', validators=[DataRequired(), Length(
        min=8, max=20, message='password must be between 8 and 20 characters :D')])
    submit = SubmitField('Submit')

class ThingsYouWantToTranslate(FlaskForm):
    message = StringField('message', validators=[DataRequired()])
    languagetyped = StringField('What language are you writing in?', validators=[DataRequired()])
    langoutput = StringField('What language do you want to output', validators=[DataRequired()])
    submit = SubmitField('translate')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            return redirect(url_for('home', userid=user.id))
    return render_template('login.html', form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data
        username = form.username.data
        password = form.password.data
        user = User(username=username, email=email, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html', form=form)

@app.route("/")
def index():
    return "potato"

@app.route("/home")
def home():
    userid = request.args.get('userid')
    return render_template("home.html")

@app.route("/translation", methods=['GET', 'POST'])
def translation():
    form = ThingsYouWantToTranslate()
    if form.validate_on_submit():
        apikey = featherlessapikey
        data = form.message.data
        langinptu = form.languagetyped.data
        langoutput = form.langoutput.data
        response = requests.post(
            url="https://api.featherless.ai/v1/chat/completions",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {apikey}"
            },
            json={
                'model': "Qwen/Qwen2.5-7B-Instruct",
                "messages": [
                    {'role':'system',"content": "you are a helpful translator that is extremely skilled"},
                    {'role':'user',"content": f"Hello! can you please translate {data} from {langinptu} to {langoutput}? thank you so much, but only translate it, no additional sure or ok"}
                ]
            }
        )
        message = response.json()['choices'][0]['message']['content']
        print(message)
        apikeyforelevenlabs = elevenlabsapikey
        client = ElevenLabs(
            api_key = apikeyforelevenlabs,
        )
        audio = client.text_to_speech.convert(
            text=message,
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )

        play(audio)

    return render_template("translation.html", form=form)

with app.app_context():
    db.create_all()
# translator app so that if you dont understand the lang u can use the app to say it
# so you input some text in ur native lnag and u click and it speaks text in the lang u awnt it to say
if __name__ == '__main__':
    app.run(debug=True)
