# Handlers e eventos do SocketIO (connect, join, msg, disconnect)
import threading
from datetime import datetime

from flask import request, session
from flask_socketio import emit

from models.database import Usuario, db

# Conexões ativas: sid (id da conexão) -> {'user_id', 'nome'}
conexoes = {}
trava = threading.Lock()     # async_mode="threading": protege o dicionário


def _foto_url(user_id):
    usuario = db.session.get(Usuario, user_id)
    return f'/static/uploads/{usuario.foto}' if usuario and usuario.foto else None


def _online():
    """Lista de nomes (sem repetir usuário com várias abas abertas)."""
    with trava:
        usuarios = {c['user_id']: c['nome'] for c in conexoes.values() if c.get('entrou')}
    return sorted(usuarios.values(), key=str.lower)


def _avisar_online():
    nomes = _online()
    emit('online', {'total': len(nomes), 'nomes': nomes}, broadcast=True)


def _sistema(texto):
    """Mensagem de sistema (cinza, centralizada no chat)."""
    emit('status', {'msg': texto, 'hora': datetime.now().strftime('%H:%M')}, broadcast=True)


def init_app(socketio):

    @socketio.on('connect')
    def on_connect(auth=None):
        # Recusa a conexão de quem não está logado (retornar False rejeita)
        if 'user_id' not in session:
            return False
        with trava:
            conexoes[request.sid] = {'user_id': session['user_id'],
                                     'nome': session['usuario_nome'],
                                     'entrou': False}

    @socketio.on('join')
    def on_join(_data=None):
        if 'user_id' not in session:
            return
        # Nome de exibição vem da SESSÃO no servidor, nunca do navegador
        nome = session['usuario_nome']
        user_id = session['user_id']
        with trava:
            ja_estava = any(c['user_id'] == user_id and c.get('entrou')
                            for sid, c in conexoes.items() if sid != request.sid)
            if request.sid in conexoes:
                conexoes[request.sid]['entrou'] = True
        if not ja_estava:                 # outra aba do mesmo usuário não repete o aviso
            _sistema(f'{nome} entrou no chat')
        _avisar_online()

    @socketio.on('msg')
    def on_msg(data):
        if 'user_id' not in session:
            return
        texto = ''
        if isinstance(data, dict):
            texto = str(data.get('msg', ''))
        elif isinstance(data, str):
            texto = data
        texto = texto.strip()[:1000]
        if not texto:
            return

        # Monta a mensagem no servidor: o remetente é SEMPRE o da sessão
        data = {
            'user_id': session['user_id'],
            'nome': session['usuario_nome'],
            'foto': _foto_url(session['user_id']),
            'msg': texto,
            'hora': datetime.now().strftime('%H:%M'),
        }
        # Retransmite para todos os conectados
        emit("showmsg", data, broadcast=True)

    @socketio.on('disconnect')
    def on_disconnect(*_args):
        with trava:
            conexao = conexoes.pop(request.sid, None)
            ainda_online = conexao and any(
                c['user_id'] == conexao['user_id'] and c.get('entrou') for c in conexoes.values())
        if conexao and conexao.get('entrou') and not ainda_online:
            _sistema(f"{conexao['nome']} saiu do chat")
        _avisar_online()
