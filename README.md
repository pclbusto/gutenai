# gutenai/gutenai/README.md

# GutenAI

GutenAI is a Python application designed to interact with EPUB files and provide various functionalities such as text extraction from images and integration with the OpenAI API.

## Project Structure

```
gutenai/
├── gutenai/
│   ├── __init__.py         # Package initialization
│   ├── main.py              # Main entry point of the application
│   ├── utils/               # Utility functions
│   │   └── __init__.py      # Package initialization
├── tests/                   # Unit tests for the application
│   ├── __init__.py          # Package initialization
│   └── test_main.py         # Tests for the main application
├── requirements.txt         # Python package dependencies
├── setup.py                 # Setup script for packaging
└── README.md                # Project documentation
```

## Features

- Load, read, and save EPUB files.
- Extract text from images using OCR.
- Interact with the OpenAI API for advanced text processing.

## Installation

To install the required dependencies, run:

```
pip install -r requirements.txt
```

## Usage

To start the application, run:

```
python -m gutenai.main
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or features.