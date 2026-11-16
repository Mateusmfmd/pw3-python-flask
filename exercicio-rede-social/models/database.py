# Instância do SQLAlchemy e classes Usuario, Post e Curtida
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

# Instância única do banco. É ligada ao app em app.py com db.init_app(app)
db = SQLAlchemy()


class Usuario(db.Model):
    """Usuário da rede social."""
    __tablename__ = 'usuario'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)
    # E-mail único: o banco também impede duplicidade
    email = db.Column(db.String(120), unique=True, nullable=False)
    # Guarda apenas o HASH da senha (scrypt), nunca a senha pura
    senha = db.Column(db.String(255), nullable=False)
    # Desafio extra 2: nome do arquivo da foto de perfil (opcional)
    foto = db.Column(db.String(255), nullable=True)

    # Relacionamento 1:N -> um usuário tem vários posts.
    # O backref cria o atributo post.autor, usado no feed para exibir o nome.
    posts = db.relationship('Post', backref='autor', lazy=True,
                            cascade='all, delete-orphan')

    curtidas = db.relationship('Curtida', backref='usuario', lazy=True,
                               cascade='all, delete-orphan')

    @property
    def inicial(self):
        """Primeira letra do nome, usada no avatar quando não há foto."""
        return (self.nome or '?').strip()[:1].upper() or '?'

    def __repr__(self):
        return f'<Usuario {self.email}>'


class Post(db.Model):
    """Publicação (imagem + legenda) feita por um usuário."""
    __tablename__ = 'post'

    id = db.Column(db.Integer, primary_key=True)
    imagem = db.Column(db.String(255), nullable=False)   # nome do arquivo em static/uploads
    legenda = db.Column(db.String(300), nullable=True)
    data_post = db.Column(db.DateTime, nullable=False, default=datetime.now)
    # Chave estrangeira para o autor do post
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    # Desafio extra 3: curtidas do post (apagadas junto com o post)
    curtidas = db.relationship('Curtida', backref='post', lazy=True,
                               cascade='all, delete-orphan')

    @property
    def total_curtidas(self):
        return len(self.curtidas)

    def __repr__(self):
        return f'<Post {self.id} de {self.usuario_id}>'


class Curtida(db.Model):
    """Desafio extra 3: tabela associativa N:N entre Usuario e Post."""
    __tablename__ = 'curtida'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    data = db.Column(db.DateTime, nullable=False, default=datetime.now)

    # Um usuário só pode curtir o mesmo post UMA vez
    __table_args__ = (
        db.UniqueConstraint('usuario_id', 'post_id', name='uq_curtida_usuario_post'),
    )
