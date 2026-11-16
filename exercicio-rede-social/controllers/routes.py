# Rotas HTTP (login, cadastro, feed, upload, logout + perfil, curtir, excluir)
import os
import uuid
from datetime import datetime

from flask import (abort, current_app, flash, g, jsonify, redirect,
                   render_template, request, session, url_for)
from markupsafe import Markup, escape
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from models.database import Curtida, Post, Usuario, db

# Extensões de imagem aceitas no upload
EXTENSOES_PERMITIDAS = {'png', 'jpg', 'jpeg', 'gif'}

# Rotas que exigem login (verificadas no @app.before_request)
ROTAS_PROTEGIDAS = ('/feed', '/upload', '/chat', '/perfil', '/post')


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
def arquivo_permitido(nome_arquivo):
    """True se o arquivo tem extensão png, jpg, jpeg ou gif."""
    return '.' in nome_arquivo and nome_arquivo.rsplit('.', 1)[1].lower() in EXTENSOES_PERMITIDAS


def pasta_uploads():
    """Caminho absoluto de static/uploads (independe da pasta de onde o app foi iniciado)."""
    return os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])


def salvar_imagem(arquivo):
    """Valida a extensão, renomeia com uuid4 e salva em UPLOAD_FOLDER.
    Retorna o novo nome do arquivo ou None se for inválido."""
    if not arquivo or arquivo.filename == '' or not arquivo_permitido(arquivo.filename):
        return None
    extensao = arquivo.filename.rsplit('.', 1)[1].lower()
    # uuid4 gera um nome único e impede sobrescrever arquivos ou usar nomes maliciosos
    novo_nome = f'{uuid.uuid4().hex}.{extensao}'
    os.makedirs(pasta_uploads(), exist_ok=True)
    arquivo.save(os.path.join(pasta_uploads(), novo_nome))
    return novo_nome


def remover_imagem(nome_arquivo):
    """Apaga um arquivo de static/uploads, se existir (os.remove)."""
    if not nome_arquivo:
        return
    caminho = os.path.join(pasta_uploads(), os.path.basename(nome_arquivo))
    if os.path.exists(caminho):
        os.remove(caminho)


def tempo_relativo(data):
    """Converte uma data em texto amigável: 'agora mesmo', 'há 5 minutos'..."""
    if not data:
        return ''
    segundos = int((datetime.now() - data).total_seconds())
    if segundos < 60:
        return 'agora mesmo'
    minutos = segundos // 60
    if minutos < 60:
        return f'há {minutos} minuto{"s" if minutos > 1 else ""}'
    horas = minutos // 60
    if horas < 24:
        return f'há {horas} hora{"s" if horas > 1 else ""}'
    dias = horas // 24
    if dias < 7:
        return f'há {dias} dia{"s" if dias > 1 else ""}'
    return data.strftime('%d/%m/%Y')


def avatar(usuario, tamanho='md'):
    """HTML do avatar: foto de perfil ou círculo colorido com a inicial do nome."""
    if usuario is None:
        return Markup('')
    classe = f'avatar avatar-{tamanho}'
    if usuario.foto:
        src = url_for('static', filename=f'uploads/{usuario.foto}')
        return Markup(f'<img src="{escape(src)}" class="{classe}" alt="Foto de perfil de {escape(usuario.nome)}">')
    matiz = (usuario.id * 47) % 360   # cor fixa por usuário
    return Markup(f'<span class="{classe} avatar-inicial" style="--matiz:{matiz}" role="img" '
                  f'aria-label="Avatar de {escape(usuario.nome)}">{escape(usuario.inicial)}</span>')


def requisicao_ajax():
    return request.headers.get('X-Requested-With') == 'fetch'


# ---------------------------------------------------------------------------
# Registro das rotas
# ---------------------------------------------------------------------------
def init_app(app):

    app.jinja_env.filters['tempo_relativo'] = tempo_relativo

    @app.context_processor
    def variaveis_globais():
        # Disponível em todos os templates
        return {'usuario_atual': g.get('usuario'), 'avatar': avatar}

    # ---------------- Proteção das rotas ----------------
    @app.before_request
    def verificar_login():
        g.usuario = None
        if 'user_id' in session:
            g.usuario = db.session.get(Usuario, session['user_id'])
            if g.usuario is None:          # usuário apagado / banco recriado
                session.clear()

        # Bloqueia /feed, /upload, /chat, /perfil e /post/... para quem não está logado
        if request.path.startswith(ROTAS_PROTEGIDAS) and g.usuario is None:
            if requisicao_ajax():
                return jsonify({'erro': 'Faça login para continuar.'}), 401
            flash('Faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))

    @app.errorhandler(413)
    def arquivo_grande(_erro):
        flash('Arquivo muito grande! O limite é 16 MB.', 'danger')
        return redirect(request.referrer or url_for('feed'))

    @app.route('/')
    def index():
        return redirect(url_for('feed' if 'user_id' in session else 'login'))

    # ---------------- Cadastro ----------------
    @app.route('/cadastro', methods=['GET', 'POST'])
    def cadastro():
        if g.usuario:
            return redirect(url_for('feed'))

        if request.method == 'POST':
            nome = request.form.get('nome', '').strip()
            email = request.form.get('email', '').strip().lower()
            senha = request.form.get('senha', '')
            confirmar = request.form.get('confirmar_senha', senha)

            if not nome or not email or not senha:
                flash('Preencha nome, e-mail e senha.', 'warning')
            elif len(senha) < 6:
                flash('A senha deve ter pelo menos 6 caracteres.', 'warning')
            elif senha != confirmar:
                flash('As senhas não conferem.', 'warning')
            # Bloqueia e-mail duplicado
            elif Usuario.query.filter_by(email=email).first():
                flash('Este e-mail já está cadastrado. Faça login.', 'danger')
            else:
                # Senha guardada como hash scrypt
                usuario = Usuario(nome=nome, email=email,
                                  senha=generate_password_hash(senha, method='scrypt'))
                db.session.add(usuario)
                try:
                    db.session.commit()
                except IntegrityError:          # segurança extra (UNIQUE do banco)
                    db.session.rollback()
                    flash('Este e-mail já está cadastrado. Faça login.', 'danger')
                    return render_template('cadastro.html', nome=nome, email=email)
                flash('Conta criada com sucesso! Agora é só entrar.', 'success')
                return redirect(url_for('login'))

            return render_template('cadastro.html', nome=nome, email=email)

        return render_template('cadastro.html')

    # ---------------- Login ----------------
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if g.usuario:
            return redirect(url_for('feed'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            senha = request.form.get('senha', '')
            usuario = Usuario.query.filter_by(email=email).first()

            # check_password_hash compara a senha digitada com o hash salvo
            if usuario and check_password_hash(usuario.senha, senha):
                session.clear()
                session.permanent = True      # usa PERMANENT_SESSION_LIFETIME (1h)
                session['user_id'] = usuario.id
                session['usuario_nome'] = usuario.nome
                session['usuario_email'] = usuario.email
                flash(f'Bem-vindo(a), {usuario.nome}!', 'success')
                return redirect(url_for('feed'))

            flash('E-mail ou senha inválidos.', 'danger')
            return render_template('login.html', email=email)

        return render_template('login.html')

    # ---------------- Logout ----------------
    @app.route('/logout')
    def logout():
        session.clear()
        flash('Você saiu da sua conta. Até logo!', 'info')
        return redirect(url_for('login'))

    # ---------------- Feed ----------------
    @app.route('/feed')
    def feed():
        # Posts do mais recente para o mais antigo
        posts = Post.query.order_by(Post.data_post.desc()).all()
        # IDs dos posts que o usuário logado já curtiu (para pintar o coração)
        curtidos = {c.post_id for c in Curtida.query.filter_by(usuario_id=g.usuario.id)}
        return render_template('feed.html', posts=posts, curtidos=curtidos)

    # ---------------- Upload de post ----------------
    @app.route('/upload', methods=['POST'])
    def upload():
        arquivo = request.files.get('file')
        legenda = request.form.get('legenda', '').strip()[:300]

        if not arquivo or arquivo.filename == '':
            flash('Selecione uma imagem para publicar.', 'warning')
            return redirect(url_for('feed'))

        nome_arquivo = salvar_imagem(arquivo)
        if not nome_arquivo:
            flash('Formato inválido. Envie apenas PNG, JPG, JPEG ou GIF.', 'danger')
            return redirect(url_for('feed'))

        post = Post(imagem=nome_arquivo, legenda=legenda, usuario_id=g.usuario.id)
        db.session.add(post)
        db.session.commit()
        flash('Publicação feita com sucesso!', 'success')
        return redirect(url_for('feed'))

    # ---------------- Desafio 1: excluir post ----------------
    @app.route('/post/<int:post_id>/excluir', methods=['POST'])
    def excluir_post(post_id):
        post = db.session.get(Post, post_id) or abort(404)

        # Só o autor pode excluir
        if post.usuario_id != g.usuario.id:
            flash('Você só pode excluir as suas próprias publicações.', 'danger')
            return redirect(url_for('feed'))

        imagem = post.imagem
        db.session.delete(post)          # apaga do banco (curtidas vão junto)
        db.session.commit()
        remover_imagem(imagem)           # apaga do disco com os.remove
        flash('Publicação excluída.', 'success')
        voltar = request.form.get('voltar', '')
        # Só aceita caminhos internos (evita redirecionamento para outro site)
        if not voltar.startswith('/') or voltar.startswith('//'):
            voltar = url_for('feed')
        return redirect(voltar)

    # ---------------- Desafio 3: curtir / descurtir ----------------
    @app.route('/post/<int:post_id>/curtir', methods=['POST'])
    def curtir(post_id):
        post = db.session.get(Post, post_id) or abort(404)
        curtida = Curtida.query.filter_by(usuario_id=g.usuario.id, post_id=post.id).first()

        if curtida:                       # já curtiu -> descurte
            db.session.delete(curtida)
            curtido = False
        else:                             # ainda não curtiu -> curte
            db.session.add(Curtida(usuario_id=g.usuario.id, post_id=post.id))
            curtido = True
        try:
            db.session.commit()
        except IntegrityError:            # clique duplo muito rápido (UniqueConstraint)
            db.session.rollback()
            curtido = True

        total = Curtida.query.filter_by(post_id=post.id).count()
        if requisicao_ajax():
            return jsonify({'curtido': curtido, 'total': total})
        return redirect(url_for('feed') + f'#post-{post.id}')

    # ---------------- Desafio 2: perfil e foto ----------------
    @app.route('/perfil', methods=['GET', 'POST'])
    def perfil():
        usuario = g.usuario

        if request.method == 'POST':
            if request.form.get('acao') == 'remover':
                remover_imagem(usuario.foto)
                usuario.foto = None
                db.session.commit()
                flash('Foto de perfil removida.', 'info')
                return redirect(url_for('perfil'))

            arquivo = request.files.get('foto')
            if not arquivo or arquivo.filename == '':
                flash('Selecione uma imagem.', 'warning')
                return redirect(url_for('perfil'))

            # Mesma validação do upload de posts + nome com uuid
            nome_arquivo = salvar_imagem(arquivo)
            if not nome_arquivo:
                flash('Formato inválido. Envie apenas PNG, JPG, JPEG ou GIF.', 'danger')
                return redirect(url_for('perfil'))

            remover_imagem(usuario.foto)      # apaga a foto antiga do disco
            usuario.foto = nome_arquivo
            db.session.commit()
            flash('Foto de perfil atualizada!', 'success')
            return redirect(url_for('perfil'))

        posts = Post.query.filter_by(usuario_id=usuario.id).order_by(Post.data_post.desc()).all()
        total_curtidas = sum(p.total_curtidas for p in posts)
        return render_template('perfil.html', posts=posts, total_curtidas=total_curtidas)

    # ---------------- Chat ----------------
    @app.route('/chat')
    def chat():
        return render_template('chat.html')
