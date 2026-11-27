from flask import Flask
from flask_cors import CORS

from rachacontas.routes.valor import valor_bp

app = Flask("Racha Contas")
CORS(app)
app.register_blueprint(valor_bp)


def main() -> None:
    app.run()


if __name__ == "__main__":
    main()