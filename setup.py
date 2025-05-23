from setuptools import setup, find_packages
import os
import ast

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

# Read requirements from requirements.txt if it exists
requirements = []
if os.path.exists('requirements.txt'):
    with open('requirements.txt', 'r', encoding='utf-8') as req_file:
        requirements = [line.strip() for line in req_file if line.strip() and not line.startswith('#')]


def get_version():
    with open('aini/__init__.py', 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('__version__'):
                return ast.literal_eval(line.split('=')[1].strip())
    raise RuntimeError("Version information not found")


# For backward compatibility
setup(
    name='aini',
    version=get_version(),
    author='Alpha x1',
    author_email='alpha.xone@outlook.com',
    description='Declarative AI components',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/alpha-xone/aini',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'aini': ['**/*.yml', '**/*.yaml', '**/*.json'],
        '': ['requirements.txt'],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
    install_requires=requirements,
)
