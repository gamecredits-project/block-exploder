from setuptools import setup

setup(
    name='exploder',
    packages=['exploder_api', 'syncer'],
    include_package_data=True,
    install_requires=[
        'gamecredits',
        'tornado',
        'connexion',
        'pymongo'
    ],
    zip_safe=False
)
