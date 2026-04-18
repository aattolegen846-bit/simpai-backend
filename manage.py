from flask.cli import FlaskGroup

from app.main import application


cli = FlaskGroup(create_app=lambda: application)


if __name__ == "__main__":
    cli()
