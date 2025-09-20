from setuptools import setup, find_packages

setup(
    name='gutenai',
    version='0.1.0',
    author='Your Name',
    author_email='your.email@example.com',
    description='A Python application for working with EPUB files and integrating with OpenAI API.',
    packages=find_packages(),
    install_requires=[
        # List your dependencies here
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)