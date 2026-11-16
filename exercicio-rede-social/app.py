# Configurações do Flask, Banco de Dados e SocketIO
import os

from flask import Flask
from flask_socketio import SocketIO

from models.database import db
from controllers import routes, chat

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# template_folder='views' -> os HTMLs ficam na pasta views/
app = Flask(__name__, template_folder='views')

# ---------------- Configurações ----------------
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'pw3-rede-social-chave-secreta-troque-em-producao')
app.config['PERMANENT_SESSION_LIFETIME'] = 3600          # sessão expira em 1 hora (segundos)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'models', 'rede_social.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'            # pasta onde as imagens são salvas
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024       # limite de 16 MB por requisição

# SocketIO para o chat em tempo real
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# db.init_app FORA do if __name__ == '__main__' (o app precisa do banco mesmo
# quando é importado por outro servidor/ferramenta)
db.init_app(app)

# Registra as rotas HTTP e os eventos do chat
routes.init_app(app)
chat.init_app(socketio)


if __name__ == '__main__':
    # Garante que a pasta de uploads existe
    os.makedirs(os.path.join(BASE_DIR, app.config['UPLOAD_FOLDER']), exist_ok=True)

    # Cria as tabelas (usuario, post, curtida) caso ainda não existam
    with app.app_context():
        db.create_all()

    socketio.run(app, port=5000, debug=True, allow_unsafe_werkzeug=True)
