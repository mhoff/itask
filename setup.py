from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="itask",
    version="0.1.6",
    packages=find_packages(),
    install_requires=[
        'markdown',  # TODO necessary?
        'prompt_toolkit>=1.0.15<=2.0.3',
    ],
    author="Michael Hoff",
    author_email="mail@michael-hoff.net",
    description="Interactive shell for taskwarrior",
    license="GPL-3.0",  # TODO correct formatting?
    keywords="taskwarrior task task-manager interactive shell",
    url="https://github.com/mhoff/itask",
    entry_points={
        'console_scripts': [
            'itask=itask:main',
        ],
    },
    package_data={
        '': ['*.md'],  # TODO proper way to handle READMEs?
    },
    long_description=long_description,
    classifiers=[
        'Development Status :: 4 - Beta'
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)'
        'Topic :: Utilities'
    ],
    project_urls={
        "Bug Tracker": "https://github.com/mhoff/itask/issues",
        # TODO 'Documentation' should point to documentation specific to the module *version*
        "Documentation": "https://github.com/mhoff/itask/blob/master/README.md",
        "Source Code": "https://github.com/mhoff/itask",
    },
)
