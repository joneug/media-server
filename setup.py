from setuptools import setup

setup(
    name='media_server',
    version='0.1.0',
    packages=['media_server'],
    entry_points={
        'console_scripts': [
            'media_server = media_server.__main__:main'
        ]
    })
