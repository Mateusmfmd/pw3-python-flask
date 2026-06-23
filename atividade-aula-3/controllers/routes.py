from flask import render_template, request

def init_app(app):

    # Dados iniciais (simulando banco de dados em memória)
    lista_filmes = [
        {
            "titulo": "Interestelar",
            "diretor": "Christopher Nolan",
            "ano": 2014,
            "genero": "Ficção Científica",
            "nota": 9.5
        },
        {
            "titulo": "O Poderoso Chefão",
            "diretor": "Francis Ford Coppola",
            "ano": 1972,
            "genero": "Drama/Crime",
            "nota": 9.2
        }
    ]

    lista_series = [
        {
            "titulo": "Breaking Bad",
            "criador": "Vince Gilligan",
            "ano": 2008,
            "genero": "Drama/Suspense",
            "temporadas": 5,
            "plataforma": "Netflix"
        },
        {
            "titulo": "Dark",
            "criador": "Baran bo Odar",
            "ano": 2017,
            "genero": "Ficção Científica",
            "temporadas": 3,
            "plataforma": "Netflix"
        }
    ]

    # HOME
    @app.route('/')
    def home():
        destaque = lista_filmes[0] if lista_filmes else None
        return render_template('index.html', destaque=destaque)

    # FILMES
    @app.route('/filmes')
    def filmes():
        return render_template('filmes.html', lista_filmes=lista_filmes)

    @app.route('/cadfilme', methods=['GET', 'POST'])
    def cadfilme():
        erro = None
        sucesso = None

        if request.method == 'POST':
            titulo = request.form.get('titulo', '').strip()
            diretor = request.form.get('diretor', '').strip()
            ano = request.form.get('ano', '').strip()
            genero = request.form.get('genero', '').strip()
            nota = request.form.get('nota', '').strip()

            if not all([titulo, diretor, ano, genero, nota]):
                erro = 'Preencha todos os campos.'
            else:
                try:
                    novo_filme = {
                        "titulo": titulo,
                        "diretor": diretor,
                        "ano": int(ano),
                        "genero": genero,
                        "nota": float(nota)
                    }

                    lista_filmes.append(novo_filme)
                    sucesso = f'Filme "{titulo}" cadastrado com sucesso!'

                except ValueError:
                    erro = 'Ano e Nota devem ser números válidos.'

        return render_template(
            'cadfilme.html',
            lista_filmes=lista_filmes,
            erro=erro,
            sucesso=sucesso
        )

    # SERIES
    @app.route('/series')
    def series():
        return render_template('series.html', lista_series=lista_series)

    @app.route('/cadserie', methods=['GET', 'POST'])
    def cadserie():
        erro = None
        sucesso = None

        if request.method == 'POST':
            titulo = request.form.get('titulo', '').strip()
            criador = request.form.get('criador', '').strip()
            ano = request.form.get('ano', '').strip()
            genero = request.form.get('genero', '').strip()
            temporadas = request.form.get('temporadas', '').strip()
            plataforma = request.form.get('plataforma', '').strip()

            if not all([titulo, criador, ano, genero, temporadas, plataforma]):
                erro = 'Preencha todos os campos.'
            else:
                try:
                    nova_serie = {
                        "titulo": titulo,
                        "criador": criador,
                        "ano": int(ano),
                        "genero": genero,
                        "temporadas": int(temporadas),
                        "plataforma": plataforma
                    }

                    lista_series.append(nova_serie)
                    sucesso = f'Série "{titulo}" cadastrada com sucesso!'

                except ValueError:
                    erro = 'Ano e Temporadas devem ser números válidos.'

        return render_template(
            'cadserie.html',
            lista_series=lista_series,
            erro=erro,
            sucesso=sucesso
        )