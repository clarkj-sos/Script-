# Getting Started with YouTube MCP Server

This guide will help you get up and running with the Remote Desktop Control Server application.

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.9 or higher
- pip (Python package manager)
- git

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/clarkj-sos/Script-.git
cd Script-
```

### 2. Create a Virtual Environment (Recommended)

It's recommended to use a virtual environment to manage dependencies:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

Install all required Python packages:

```bash
pip install -r requirements.txt
```

This will install the following key dependencies:
- Flask: Web framework
- Flask-SocketIO: WebSocket support for real-time communication
- mss: Screen capture library
- Pillow: Image processing
- cryptography: TLS certificate generation

## Running the Application

### Starting the Server

To start the Remote Desktop Control Server:

```bash
python server.py
```

The server will:
1. Generate a self-signed TLS certificate (if one doesn't exist)
2. Generate a random access password (if not set via environment variable)
3. Start listening on https://localhost:6100

Example output:
```
[*] Generating self-signed TLS certificate...
[+] Certificate saved to cert.pem
[+] Key saved to key.pem

[+] Remote Desktop Control Server
[+] URL: https://localhost:6100
[+] Password: <generated-password>
[+] Screen FPS: 30
[+] JPEG Quality: 85
```

### Setting a Custom Password

To use a custom password instead of a generated one, set the `RDC_PASSWORD` environment variable:

```bash
export RDC_PASSWORD="your-secure-password"
python server.py
```

## Configuration

You can customize the server behavior by editing `config.py`:

- **HOST**: Server host address (default: localhost)
- **PORT**: Server port (default: 6100)
- **SCREEN_FPS**: Screen capture frames per second (default: 30)
- **JPEG_QUALITY**: JPEG compression quality 1-100 (default: 85)
- **CERT_FILE**: Path to TLS certificate (default: cert.pem)
- **KEY_FILE**: Path to TLS key (default: key.pem)
- **UPLOAD_DIR**: Directory for uploaded files (default: uploads)

## Testing

The project includes tests that run via pytest. To run tests:

```bash
python -m pytest
```

You can also run linting checks:

```bash
python -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

## Project Structure

```
Script-/
├── server.py              # Main application entry point
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── app/                   # Main application package
│   ├── __init__.py        # App factory
│   ├── auth.py            # Authentication module
│   ├── routes/            # Route handlers
│   ├── services/          # Business logic services
│   ├── sockets/           # WebSocket handlers
│   ├── static/            # CSS and JavaScript files
│   └── templates/         # HTML templates
├── .github/
│   └── workflows/         # GitHub Actions CI/CD
└── GETTING-STARTED.md     # This file
```

## Troubleshooting

### ImportError for dependencies
Make sure you've activated the virtual environment and installed requirements:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Certificate generation errors
The application automatically generates a self-signed certificate on first run. If you encounter permission errors, ensure you have write access to the repository directory.

### Connection refused
Make sure the server is running and listening on the correct host and port (default: https://localhost:6100).

## Development

To contribute to the project:

1. Create a new branch for your feature
2. Make your changes and test thoroughly
3. Ensure all tests pass: `python -m pytest`
4. Ensure code passes linting: `python -m flake8`
5. Submit a pull request

## License

See the LICENSE file for details.

## Support

For issues and questions, please create an issue on the GitHub repository.
