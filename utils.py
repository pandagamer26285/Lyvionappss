from werkzeug.security import generate_password_hash, check_password_hash
import os
import secrets

def hash_password(password):
    return generate_password_hash(password)

def verify_password(hash, password):
    from werkzeug.security import check_password_hash
    return check_password_hash(hash, password)

def save_video_file(file, upload_folder):
    # Guarda el archivo con un nombre aleatorio para evitar colisiones
    ext = os.path.splitext(file.filename)[1]
    nombre_aleatorio = secrets.token_hex(16) + ext
    filepath = os.path.join(upload_folder, nombre_aleatorio)
    file.save(filepath)
    return nombre_aleatorio
