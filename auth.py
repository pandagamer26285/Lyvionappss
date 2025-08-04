from flask import Blueprint, request, render_template, redirect, url_for, flash
from models import User, db
from utils import hash_password, verify_password
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password')
        if not username or not email or not password:
            flash("Completa todos los campos", "danger")
            return render_template('register.html')
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Usuario o email ya existe", "danger")
            return render_template('register.html')
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password)
        )
        db.session.add(user)
        db.session.commit()

        # Auto seguir al dueño (id=1)
        from models import Follow
        if user.id != 1:
            follow = Follow(follower_id=user.id, followed_id=1)
            db.session.add(follow)
            db.session.commit()

        flash("Registrado correctamente, ya puedes iniciar sesión.", "success")
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email').strip()
        password = request.form.get('password')
        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()
        if user and verify_password(user.password_hash, password):
            access_token = create_access_token(identity=user.id, expires_delta=datetime.timedelta(days=1))
            response = redirect(url_for('main.index'))
            response.set_cookie('access_token', access_token, httponly=True, max_age=86400)
            return response
        flash("Usuario o contraseña incorrectos", "danger")
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    response = redirect(url_for('auth.login'))
    response.delete_cookie('access_token')
    return response
