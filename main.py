from flask import Flask, render_template, url_for, redirect, request
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length
from wtforms import SubmitField, FileField, EmailField, StringField, PasswordField
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bootstrap import Bootstrap5
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
from io import BytesIO
import logging
logging.basicConfig(level=logging.INFO)
logging.info("Starting Flask app")

load_dotenv()

import requests
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play


class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./potatopotato.db'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
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
    langinput = StringField('What language do you want to input', validators=[DataRequired()])
    langoutput = StringField('What language do you want to output', validators=[DataRequired()])
    submit = SubmitField('translate')

class LanginputForm(FlaskForm):
    langinput = StringField('Input language', validators=[DataRequired()])
    langoutput = StringField('output language', validators=[DataRequired()])
    submit = SubmitField('transcribe and translate')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

class SavedTranslations(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    langinput = db.Column(db.String(120), nullable=False)
    wordinput = db.Column(db.String(120), nullable=False)
    langoutput = db.Column(db.String(120), nullable=False)
    wordoutput = db.Column(db.String(120), nullable=False)
    userid = db.Column(db.Integer, nullable=False)
    submit = SubmitField('save')

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
    return render_template('index.html')

@app.route("/home")
def home():
    userid = request.args.get('userid')
    user = User.query.filter_by(id=userid).first()
    return render_template("home.html", username = user.username, userid =userid)

@app.route("/translation", methods=['GET', 'POST'])
def translation():
    form = ThingsYouWantToTranslate()
    userid = request.args.get('userid')
    if form.validate_on_submit():
        apikey = featherlessapikey
        data = form.message.data
        langinput = form.langinput.data
        langoutput = form.langoutput.data
        message = translate(apikey,langinput, langoutput, data)
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

        
        return render_template('translation.html', form=form, message=message, userid=userid)

    return render_template("translation.html", form=form, userid=userid)

def translate(apikey, langinput, langoutput, message):
    response = requests.post(
        url="https://api.featherless.ai/v1/chat/completions",
        headers={
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {apikey}"
        },
        json={
            'model': "Qwen/Qwen2.5-7B-Instruct",
            "messages": [
                {'role': 'system', "content": "you are a helpful translator that is extremely skilled"},
                {'role': 'user',
                 "content": f"Hello! can you please translate {message} from {langinput} to {langoutput}? thank you so much, but only translate it, no additional sure or ok"}
            ]
        }
    )
    print(response.json())
    message = response.json()['choices'][0]['message']['content']
    return message

@app.route('/picklang', methods=['GET', 'POST'])
def picklang():
    form = LanginputForm()
    userid = request.args.get('userid')
    if form.validate_on_submit():
        langoutput = form.langoutput.data
        langinput = form.langinput.data
        return redirect(url_for('speechupload', langoutput=langoutput, langinput=langinput, userid=userid))
    return render_template('picklang.html', form=form, userid=userid)

@app.route('/speechupload', methods=['GET', 'POST'])
def speechupload():
    elevenlabs = ElevenLabs(
        api_key=elevenlabsapikey,
    )
    apikey = featherlessapikey
    userid = request.args.get('userid')
    UPLOAD_FOLDER = os.path.join('static','uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    langoutput = request.args.get('langoutput')
    langinput = request.args.get('langinput')
    if request.method == 'POST':
        audiofile = request.files.get('audio')
        if audiofile:
            afilename = secure_filename(audiofile.filename)
            filepath = os.path.join(UPLOAD_FOLDER, afilename)
            audiofile.save(filepath)

            url = url_for('static', filename=f'uploads/{afilename}')
            with open(filepath, 'rb') as f:
                audiodata = BytesIO(f.read())

            transcription = elevenlabs.speech_to_text.convert(
                file=audiodata,
                model_id="scribe_v2",  # Model to use
                tag_audio_events=True,  # Tag audio events like laughter, applause, etc.
                # Language of the audio file. If set to None, the model will detect the language automatically.
                diarize=True,  # Whether to annotate who is speaking
            )
            print(transcription.text)
            translatedtext = translate(apikey, langinput, langoutput, transcription.text)
            return render_template('speech.html', transcription=transcription.text, url=url, translatedtext=translatedtext, userid=userid, langinput=langinput, langoutput=langoutput)
        else:
            print("did not work")
            return render_template('speech.html')
    else:
        return render_template('speech.html')

def save_translations(userid, langinput, wordinput, langoutput, wordoutput):
    patata = SavedTranslations(
        wordoutput=wordoutput, userid=userid, langinput=langinput, langoutput=langoutput, wordinput=wordinput)
    db.session.add(patata)
    db.session.commit()

@app.route('/savedtranslations', methods=['GET', 'POST'])
def savedtranslations():
    userid = request.args.get('userid')
    langinput = request.args.get('langinput')
    wordinput = request.args.get('wordinput')
    langoutput = request.args.get('langoutput')
    wordoutput = request.args.get('wordoutput')
    save_translations(userid, langinput, wordinput, langoutput, wordoutput)
    thingy = SavedTranslations.query.filter_by(userid=userid).all()
    return render_template('savedtranslations.html', userid=userid, saved_translations= thingy)

@app.route('/saved_transcriptions')
def saved_transcriptions():
    userid = request.args.get('userid')
    thingy = SavedTranslations.query.filter_by(userid=userid).all()
    return render_template('savedtranslations.html', userid=userid, saved_translations=thingy)

with app.app_context():
    db.create_all()
# translator app so that if you dont understand the lang u can use the app to say it
# so you input some text in ur native lnag and u click and it speaks text in the lang u awnt it to say
