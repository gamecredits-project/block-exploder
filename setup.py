from setuptools import setup

setup(
    name='exploder',
    packages=['exploder', 'blocker'],
    include_package_data=True,
    install_requires=[
        'setuptools',
        'flask',
        'appdirs',
        'backports.shutil-get-terminal-size',
        'cffi',
        'click',
        'cryptography',
        'decorator',
        'enum34',
        'Flask-Script',
        'idna',
        'ipaddress',
        'ipython',
        'ipython-genutils',
        'itsdangerous',
        'Jinja2',
        'MarkupSafe',
        'meld3',
        'packaging',
        'python-bitcoinrpc',
        'pymongo',
        'humanize',
        'gunicorn'
    ],
)
