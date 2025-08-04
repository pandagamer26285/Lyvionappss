from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "clave_secreta"

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}
PROFILE_PICS_FOLDER = 'static/profile_pics'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROFILE_PICS_FOLDER'] = PROFILE_PICS_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(PROFILE_PICS_FOLDER):
    os.makedirs(PROFILE_PICS_FOLDER)

login_manager = LoginManager()
login_manager.init_app(app)

# Datos guardados en memoria para ejemplo
users = {}
videos = {}  # video_id: {uploader_email, title, filename, likes=set(), dislikes=set()}

class User(UserMixin):
    def __init__(self, email):
        self.id = email

@login_manager.user_loader
def load_user(email):
    if email in users:
        return User(email)
    return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/')
def index():
    # Mostrar todos los videos con datos básicos
    vids = []
    for vid_id, vid in videos.items():
        vids.append({
            'id': vid_id,
            'title': vid['title'],
            'filename': vid['filename'],
            'uploader': users[vid['uploader']]['username'],
            'likes': len(vid['likes']),
            'dislikes': len(vid['dislikes'])
        })
    return render_template('index.html', videos=vids)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']
        username = request.form['username']
        pic = request.files.get('profile_pic')

        if email in users:
            flash('Email ya registrado')
            return redirect(url_for('register'))
        if any(u['username'] == username for u in users.values()):
            flash('Nombre de usuario ya existe')
            return redirect(url_for('register'))

        filename = None
        if pic and allowed_image(pic.filename):
            filename = secure_filename(pic.filename)
            pic.save(os.path.join(app.config['PROFILE_PICS_FOLDER'], filename))

        users[email] = {
            'password': password,
            'username': username,
            'profile_pic': filename,
            'description': '',
            'followers': set(),
            'following': set(),
            'videos': set()
        }
        flash('Registro exitoso, ahora inicia sesión')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']
        user = users.get(email)
        if user and user['password'] == password:
            login_user(User(email))
            flash('Inicio de sesión exitoso')
            return redirect(url_for('index'))
        flash('Credenciales incorrectas')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada')
    return redirect(url_for('index'))

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files.get('video')
        title = request.form.get('title') or "Sin título"
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            video_id = str(len(videos) + 1)
            videos[video_id] = {
                'uploader': current_user.id,
                'title': title,
                'filename': filename,
                'likes': set(),
                'dislikes': set()
            }
            users[current_user.id]['videos'].add(video_id)
            flash('Video subido correctamente')
            return redirect(url_for('index'))
        flash('Formato no permitido o no seleccionaste video')
    return render_template('upload.html')

@app.route('/profile/<username>', methods=['GET', 'POST'])
@login_required
def profile(username):
    # Buscar usuario
    user_email = None
    for email, data in users.items():
        if data['username'] == username:
            user_email = email
            break
    if not user_email:
        flash('Usuario no encontrado')
        return redirect(url_for('index'))

    user_data = users[user_email]
    is_own = (user_email == current_user.id)
    is_following = (current_user.id in user_data['followers'])

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'follow':
            user_data['followers'].add(current_user.id)
            users[current_user.id]['following'].add(user_email)
            flash(f'Sigues a {username}')
        elif action == 'unfollow':
            user_data['followers'].discard(current_user.id)
            users[current_user.id]['following'].discard(user_email)
            flash(f'Has dejado de seguir a {username}')
        elif action == 'update_profile' and is_own:
            new_username = request.form.get('username')
            new_desc = request.form.get('description')
            if new_username != user_data['username'] and any(u['username'] == new_username for u in users.values()):
                flash('Nombre de usuario ya existe')
            else:
                user_data['username'] = new_username
                user_data['description'] = new_desc
                flash('Perfil actualizado')
        elif action == 'delete_video' and is_own:
            vid_id = request.form.get('video_id')
            if vid_id in user_data['videos']:
                # borrar video del sistema
                vid = videos.pop(vid_id)
                user_data['videos'].remove(vid_id)
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], vid['filename']))
                except:
                    pass
                flash('Video eliminado')

    # Cargar videos para mostrar en perfil
    user_videos = []
    for vid_id in user_data['videos']:
        vid = videos[vid_id]
        user_videos.append({
            'id': vid_id,
            'title': vid['title'],
            'filename': vid['filename'],
            'likes': len(vid['likes']),
            'dislikes': len(vid['dislikes'])
        })

    return render_template('profile.html', user=user_data, username=username,
                           is_own=is_own, is_following=is_following, user_videos=user_videos)

@app.route('/video/<video_id>/like')
@login_required
def like_video(video_id):
    if video_id in videos:
        vid = videos[video_id]
        if current_user.id in vid['dislikes']:
            vid['dislikes'].remove(current_user.id)
        vid['likes'].add(current_user.id)
        flash('Diste like al video')
    return redirect(request.referrer or url_for('index'))

@app.route('/video/<video_id>/dislike')
@login_required
def dislike_video(video_id):
    if video_id in videos:
        vid = videos[video_id]
        if current_user.id in vid['likes']:
            vid['likes'].remove(current_user.id)
        vid['dislikes'].add(current_user.id)
        flash('Diste dislike al video')
    return redirect(request.referrer or url_for('index'))

if __name__ == '__main__':
    print("Iniciando servidor en modo debug...")
    app.run(debug=True)
