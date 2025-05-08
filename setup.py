from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name='ainit',
    version='0.1.0a',
    author='Alpha X1',
    author_email='alpha.xone@outlook.com',
    description='Make class instantiation easy with auto-imports',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/alpha-xone/xinit',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
    install_requires=[
        'rich',
        'pyyaml',
    ],
)
