import sqlite3
from flask import Flask
from contextlib import closing


# routes! and functions! ~!
def connect_db(app):
    return sqlite3.connect(app.config['DATABASE'])


def init_db():
    app = Flask(__name__)
    app.config.from_object('db.dbconfig')

    with closing(connect_db(app)) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def init_db_app(app):
    with closing(connect_db(app)) as db:
        with app.open_resource('db/schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def connect_stand_alone():
    app = Flask(__name__)
    app.config.from_object('db.dbconfig')
    return connect_db(app)


class db_resource(object):

    def __init__(self, app):
        self.app = app

    def __enter__(self):
        self.db = sqlite3.connect(self.app.config["DATABASE"], isolation_level="DEFERRED")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.db.close()
