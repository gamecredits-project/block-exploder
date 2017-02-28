import subprocess


def get_version():
    p = subprocess.Popen(["git", "describe"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    if err:
        raise Exception(err)

    return out


class Config(object):
    """
    Global configuration object
    """

    # Debug mode should never be used in production
    # because it allows the execution of arbitrary code
    DEBUG = False

    TESTING = False

    CSRF_ENABLED = True

    PRODUCTION = True

    # Randomly generated UUID
    SECRET_KEY = '{{ app_secret_key }}'

    # SQLAlchemy setup
    SQLALCHEMY_DATABASE_URI = \
        'postgresql://{{ postgres_user }}:{{ postgres_pass }}@localhost:5432/{{ postgres_db }}'

    # We log everything to this directory
    LOGS_DIR = '{{ ansible_env.HOME }}/logs'

    # I set this to suppress some boring
    # deprecation warning :)
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    SESSION_EXPIRATION = 5  # in minutes

    NOTIFY_MAX_ATTEMPTS = 10
    NOTIFY_INTERVAL = 60

    # Gamecredits wallet settings
    GAME_RPC_USER = '{{ client_rpc_user }}'
    GAME_RPC_PASS = '{{ client_rpc_password }}'
    GAME_RPC_PORT = '{{ client_rpc_port }}'
    GAME_CONFIRMATIONS = {{ game_confirmations }}  # number of confirmations needed to confirm transaction
    MIN_GAME_AMOUNT = {{ min_game_amount }}
    MAX_GAME_AMOUNT = {{ max_game_amount }}

    # Celery config
    # We use Redis both as a broker and result backend
    CELERY_BROKER_URL = 'redis://localhost:6379'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379'

    SECURITY_PASSWORD_HASH = 'bcrypt'
    SECURITY_PASSWORD_SALT = '{{ security_password_salt }}'
    SECURITY_TRACKABLE = True

    SENTRY_DSN = '{{ sentry_dsn_key }}'
    SENTRY_CONFIG = {
        'release': '{{ app_version }}'
    }


class TestingConfig(Config):
    """
    Configuration for testing
    """
    # We set this so url_for return absolute urls in tests
    SERVER_NAME = 'localhost'
    PREFFERED_URL_SCHEME = 'https'

    # Turn on debug mode for testing
    DEBUG = True

    # Testing mode disables the error catching during request
    # handling so that you get better error reports
    TESTING = True

    # This is for unit testing Celery, this way celery runs tasks
    # synchronously without a broker
    CELERY_ALWAYS_EAGER = True

    NOTIFY_INTERVAL = 1
