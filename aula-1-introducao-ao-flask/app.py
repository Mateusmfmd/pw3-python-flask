# Comentario no Python
# importnado o flask para a aplicaçao 
from flask import Flask,render_template
#carregando o Flask na variavel "app"
app = Flask(__name__, template_folder='views')
#variaveis com __ sao variaveis do ambiente do python
#__name__ representa o nome da aplicaçao 

#criando a rota principal do site
@app.route('/')
#def cria funçoes bo python
def home():
    return render_template('index.html')

@app.route('/consoles')

def consoles():
    return render_template('consoles.html')

@app.route('/games')

def games():
    return render_template('games.html')

# Iniciando o servidor na porta 5000
if __name__ == '__main__':
#verificando se o arquivo gravado em __name__ é o arquivo principal
    app.run(port=5000, debug=True)
#metodo .run inicia o servidor