from setuptools import setup

setup(
    name='exploder',
    version='0.0.1',
    packages=['exploder_api', 'syncer'],
    install_requires=[
        'gamecredits',
        'tornado',
        'connexion',
        'pymongo'
    ],
    package_data={'exploder_api': ['*.yaml']},
    include_package_data=True,
    zip_safe=False
)
