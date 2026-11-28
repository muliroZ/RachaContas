from flask import Flask
from flask_cors import CORS

from rachacontas.routes.fechamento import fechamento_bp
from rachacontas.routes.importacao import importacao_bp
from rachacontas.routes.valor import valor_bp

app = Flask("Racha Contas")
CORS(app)
app.register_blueprint(valor_bp)
app.register_blueprint(fechamento_bp)
app.register_blueprint(importacao_bp)


def main() -> None:
    app.run()


if __name__ == "__main__":
    main()