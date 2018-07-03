from distutils.core import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="itask",
    packages=["itask"],
    version="0.1.5",
    description="Interactive shell for taskwarrior",
    author="Michael Hoff",
    author_email="mail@michael-hoff.net",
    url="https://github.com/mhoff/itask",
    entry_points={
        'console_scripts': [
            'itask=itask:main',
        ],
    },
    install_requires=[
        'prompt_toolkit>=1.0.15,<=2.0.3',
    ],
    long_description=long_description,
)
