from flask import *
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from functools import *
from flask_avatars import Avatars
from hashlib import *


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.app_context().push()

login_manager = LoginManager()
login_manager.init_app(app)


avatars = Avatars(app)


##CONFIGURE TABLES

class RegisteredUser(UserMixin, db.Model):
    __tablename__ = "registered_user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    post = relationship("BlogPost", back_populates="author")
    comment = relationship("Comment", back_populates="comment_author")


class BlogPost(UserMixin, db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.String, db.ForeignKey("registered_user.id"))
    author = relationship("RegisteredUser", back_populates="post")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comment = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comment"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("registered_user.id"))
    comment_author = relationship("RegisteredUser", back_populates="comment")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comment")
    comment = db.Column(db.Text, nullable=False)


# db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return RegisteredUser.query.get(user_id)


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if current_user.id != 1:
                return abort(403)
        except AttributeError:
            return abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    is_admin = False
    try:
        if current_user.id == 1:
            ## it's admin
            is_admin = True
    except AttributeError:
        pass
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated, admin=is_admin)


@app.route('/register', methods=["GET", "POST"])
def register():
    reg_form = RegisterForm()
    data = RegisteredUser.query.filter_by(email=reg_form.email.data).first()
    if reg_form.validate_on_submit():
        if data:
            flash("You've already signed up with this email. Login instead!!")
            return redirect(url_for("login"))
        new_register = RegisteredUser(
            email=reg_form.email.data,
            password=generate_password_hash(reg_form.password.data, method="scrypt", salt_length=16),
            name=reg_form.name.data
        )
        db.session.add(new_register)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=reg_form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        email = login_form.email.data
        password = login_form.password.data
        data = RegisteredUser.query.filter_by(email=email).first()
        print(data)
        if not data:
            flash("Email does not exist. please try again.")
            return redirect(url_for("login"))
        elif not check_password_hash(data.password, password):
            flash("Password incorrect, please try again.")
            return redirect(url_for("login"))
        else:
            login_user(data)
            return redirect(url_for("get_all_posts", id=data.id))
    return render_template("login.html", form=login_form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    comment_form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    is_admin = False
    try:
        if current_user.id == 1:
            ## it's admin
            is_admin = True
    except AttributeError:
        pass

    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You are not logged in. Please login to submit comment.")
            return redirect(url_for("login"))
        new_comment = Comment(
            comment=comment_form.comment.data,
            comment_author=current_user,
            parent_post=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()


    return render_template("post.html", post=requested_post, admin=is_admin, logged_in=current_user.is_authenticated,
                           form=comment_form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=['GET', 'POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, logged_in=current_user.is_authenticated)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
