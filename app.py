#** Nunez, Priscilla
#** SI 364 F18
#** HW4

#** Created an application in Flask where you can log in and create user accounts to save Gif collections
#** Followed the instructions in giphy_api_key.py before proceeding to view functions.
#** Templates are good to go. 

#** Import statements
import os
import requests
import json
from giphy_api_key import api_key
from flask import Flask, render_template, session, redirect, request, url_for, flash
from flask_script import Manager, Shell
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField, PasswordField, BooleanField, SelectMultipleField, ValidationError
from wtforms.validators import Required, Length, Email, Regexp, EqualTo
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from werkzeug.security import generate_password_hash, check_password_hash

#** Imports for login management
from flask_login import LoginManager, login_required, logout_user, login_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

#** Application configurations
app = Flask(__name__)
app.debug = True
app.use_reloader = True
app.config['SECRET_KEY'] = 'hardtoguessstring'
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL') or "postgresql://localhost/priscillaHW4db" #** My database corresponds with my unique name.
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#** App addition setups
manager = Manager(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)

#** Login configurations setup
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.init_app(app) #** set up login manager

########################
#******* Models ********
########################

#** Association tables
#** Association tables have the same structure.
#** Created an association Table between search terms and GIFs.
#** Created association Table between GIFs and collections prepared by user.



#** User-related Models

#** Special model for users to log in
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    personal_gif_collections = db.relationship("PersonalGifCollection",
                            backref='user',
                            cascade="all, delete-orphan", lazy='dynamic')
    #** Added field to user model

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

#** DB load function
#** Necessary for behind the scenes login manager that comes with flask_login capabilities - ** Won't run without this.
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) #** returns User object or None

#** Model to store gifs
class Gif(db.Model):
    __tablename__ = "gifs"
    id = db.Column(db.Integer,primary_key=True)
    title = db.Column(db.String(128))
    embedURL = db.Column(db.String(256))

    def __repr__(self):
        return "{} (URL: {})".format(self.title, self.embedURL)

    #** Added code for the Gif model such that it has the following fields:
    #** id (Integer, primary key)
    #** title (String up to 128 characters)
    #** embedURL (String up to 256 characters)

    #** Defined a __repr__ method for the Gif model that shows the title and the URL of the gif

#** Model to store a personal gif collection
class PersonalGifCollection(db.Model):
    __tablename__ = "personal_gif_collections"
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(255))
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('users.id'))
    gifs = db.relationship("Gif",
                           secondary="user_collections",
                           backref='collections', lazy="dynamic")
    #** Added code for the PersonalGifCollection model such that it has the following fields:
    #** id (Integer, primary key) ** 
    #** name (String, up to 255 characters) **

    #** Model has a one-to-many relationship with the User model. 
    #** Model has a many to many relationship with the Gif model. 

class SearchTerm(db.Model):
    __tablename__ = "search_terms"
    id = db.Column(db.Integer,primary_key=True)
    term = db.Column(db.String(32))
    gifs = db.relationship("Gif",
                           secondary="search_gifs",
                           backref='searchterms', lazy="dynamic")
    def __repr__(self):
        return self.term
    #** Added code for the SearchTerm model such that it has the following fields:
    #** id (Integer, primary key)
    #** term (String, up to 32 characters, unique) -- You want to ensure the database cannot save non-unique search terms
    #** This model should have a many to many relationship with gifs (a search will generate many gifs to save, and one gif could potentially appear in many searches)

    #** Defined a __repr__ method for this model class that returns the term string


SearchGif = db.Table('search_gifs', db.Column('gif_id', db.Integer,db.ForeignKey('gifs.id'),
                                                nullable=False),
                                    db.Column('search_term_id', db.Integer,db.ForeignKey('search_terms.id'),
                                                nullable=False))

UserCollection = db.Table('user_collections',
                                      db.Column('gif_id', db.Integer,db.ForeignKey('gifs.id'),
                                                nullable=False),
                                      db.Column('collection_id', db.Integer,db.ForeignKey('personal_gif_collections.id'),
                                                nullable=False))
########################
#******** Forms ********
########################

#** Provided
class RegistrationForm(FlaskForm):
    email = StringField('Email:', validators=[Required(),Length(1,64),Email()])
    username = StringField('Username:',validators=[Required(),Length(1,64),Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,'Usernames must have only letters, numbers, dots or underscores')])
    password = PasswordField('Password:',validators=[Required(),EqualTo('password2',message="Passwords must match")])
    password2 = PasswordField("Confirm Password:",validators=[Required()])
    submit = SubmitField('Register User')

    #** Additional checking methods for the form
    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self,field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken')

#** Provided
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[Required(), Length(1,64), Email()])
    password = PasswordField('Password', validators=[Required()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')

#** The following forms are for searching for gifs and creating collections are provided. 
class GifSearchForm(FlaskForm):
    search = StringField("Enter a term to search GIFs", validators=[Required()])
    submit = SubmitField('Submit')

class CollectionCreateForm(FlaskForm):
    name = StringField('Collection Name',validators=[Required()])
    gif_picks = SelectMultipleField('GIFs to include')
    submit = SubmitField("Create Collection")

########################
#** Helper functions ***
########################

def get_gifs_from_giphy(search_string):
    """ Returns data from Giphy API with up to 5 gifs corresponding to the search input"""
    baseurl = "https://api.giphy.com/v1/gifs/search"
    res = requests.get(baseurl, params={
        "api_key": api_key,     #** api_key calls my api key without writing out the key
        "q": search_string,
        "limit": 5              #** placed limit of 5
    })
    data = res.json()["data"]
    return data
    #** Function makes a request to the Giphy API using the input search_string, and your api_key (imported at the top of this file)
    #** The function should process the response in order to return a list of 5 gif dictionaries.

#** Provided
def get_gif_by_id(id):
    """Should return gif object or None"""
    g = Gif.query.filter_by(id=id).first()
    return g

def get_or_create_gif(title, url):
    """Always returns a Gif instance"""
    g = Gif.query.filter_by(title=title).first()
    if not g:
        g = Gif(title=title, embedURL=url)
        db.session.add(g)
        db.session.commit()
    return g 

def get_or_create_search_term(term):
    """Always returns a SearchTerm instance"""
    #** Function returns the search term instance if it already exists.

    #** If it does not exist in the database yet, this function creates a new SearchTerm instance.
    search_term = SearchTerm.query.filter_by(term=term).first()
    if not search_term:
        search_term = SearchTerm(term=term)
        db.session.add(search_term)
    gifs = get_gifs_from_giphy(term)
    for g in gifs:
        g = get_or_create_gif(g['title'], g['url'])
        search_term.gifs.append(g)
    db.session.commit()

    return search_term
    #** Function invokes the get_gifs_from_giphy function to get a list of gif data from Giphy.
    #** Iterates over that list acquired from Giphy and invoke get_or_create_gif for each, and then appends the return value from get_or_create_gif to the search term's associated gifs.
    #** Once a new search term is created, it will be added and committed to the database.
    #** The SearchTerm instance that was got or created should be returned.
    #** Tested with print statements. 

def get_or_create_collection(name, current_user, gif_list=[]):
    """Always returns a PersonalGifCollection instance"""
    collection = PersonalGifCollection.query.filter_by(name=name, user_id=current_user.id).first()
    if not collection:
        collection = PersonalGifCollection(name=name, user_id=current_user.id)
        db.session.add(collection)
        for g in gif_list:
            collection.gifs.append(g)
        db.session.commit()
    return collection

    #** Function gets or creates a personal gif collection. 

########################
#*** View functions ****
########################

#** Error handling routes
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


#** Login-related routes - provided
@app.route('/login',methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('index'))
        flash('Invalid username or password.')
    return render_template('login.html',form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out')
    return redirect(url_for('index'))

@app.route('/register',methods=["GET","POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,username=form.username.data,password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('You can now log in!')
        return redirect(url_for('login'))
    return render_template('register.html',form=form)

@app.route('/secret')
@login_required
def secret():
    return "Only authenticated users can do this! Try to log in or contact the site admin."

#** Other routes
@app.route('/', methods=['GET', 'POST'])
def index():
    form = GifSearchForm()
    #** Edited function
    #** Once the form is submitted successfully:
    #** invokes get_or_create_search_term on the form input and redirects to the function corresponding to the path /gifs_searched/<search_term> in order to see the results of the gif search. 
    if form.validate_on_submit():
        search_term = form.search.data
        get_or_create_search_term(search_term)
        return redirect(url_for('search_results', search_term=search_term))
    return render_template('index.html',form=form)

#** Provided
@app.route('/gifs_searched/<search_term>')
def search_results(search_term):
    term = SearchTerm.query.filter_by(term=search_term).first()
    relevant_gifs = term.gifs.all()
    return render_template('searched_gifs.html',gifs=relevant_gifs,term=term)

@app.route('/search_terms')
def search_terms():
    #** Edited view function so it renders search_terms.html.
    #** Template shows a list of all the search terms that have been searched so far. Each one should link to the gifs that resulted from that search.
    all_terms = SearchTerm.query.all()
    return render_template('search_terms.html',all_terms=all_terms)
    
#** Provided
@app.route('/all_gifs')
def all_gifs():
    gifs = Gif.query.all()
    return render_template('all_gifs.html',all_gifs=gifs)

@app.route('/create_collection',methods=["GET","POST"])
@login_required
def create_collection():
    form = CollectionCreateForm()
    gifs = Gif.query.all()
    choices = [(g.id, g.title) for g in gifs]
    form.gif_picks.choices = choices
    
    if request.method == "POST":
        picks = form.gif_picks.data
        name = form.name.data
        print(picks, name)
        gif_picks = []
        for g in picks:
            gif = get_gif_by_id(int(g))
            gif_picks.append(gif)
        print(name, gif_picks)
        get_or_create_collection(name, current_user, gif_picks)
        return redirect(url_for('collections'))
    return render_template('create_collection.html', form=form)
    #** Form validates on submit, gets the list of the gif ids that were selected from the form. Uses the get_gif_by_id function to create a list of Gif objects.  Then, uses the information available to invoke the get_or_create_collection function, and redirects to the page that shows a list of all collections.
    #** If the form is not validated, this view function renders the create_collection.html template and send the form to the template.


@app.route('/collections',methods=["GET","POST"])
@login_required
def collections():
    collections = PersonalGifCollection.query.filter_by(user_id=current_user.id).all()
    return render_template('collections.html', collections=collections)
    #** Function renders the collections.html template so that only the current user's personal gif collection links will render in that template. Renders correct data.

#** Provided
@app.route('/collection/<id_num>')
def single_collection(id_num):
    id_num = int(id_num)
    collection = PersonalGifCollection.query.filter_by(id=id_num).first()
    gifs = collection.gifs.all()
    return render_template('collection.html',collection=collection, gifs=gifs)

if __name__ == '__main__':
    db.create_all()
    manager.run()
