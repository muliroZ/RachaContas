from flask import Flask
from flask_cors import CORS

app = Flask("Racha Contas")
CORS(app)


def main() -> None:
    app.run()


if __name__ == "__main__":
    main()
