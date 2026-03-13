# Image Share Server

A Flask-based local network image sharing service designed for LAN environments. Share images with flexible access control including IP whitelisting, blacklisting, and timer-based expiration. **All uploaded images are encrypted at rest** using a password-based encryption system.

## Features

- **Encrypted Storage**: Images are encrypted before storage using AES-256 encryption
- **Clipboard Upload**: Paste images directly from clipboard
- **Flexible Access Control**:
  - Public sharing (anyone with link)
  - IP Whitelist (allow only specific IPs)
  - IP Blacklist (block specific IPs)
- **IP Groups**: Create reusable groups of IP addresses
- **Timer-based Expiration**: Set links to expire after a specified time
- **Share Link Management**: Enable/disable links without deleting
- **Public Gallery**: View all public images
- **IP Nicknames**: Save friendly names for IP addresses

## Quick Start

```bash
# Start the server with encryption password
./start.sh YOUR_SECURE_PASSWORD

# Or manually
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py --password YOUR_SECURE_PASSWORD
```

**Important**: You must provide the same password every time you start the server, otherwise previously uploaded images cannot be decrypted.

Server runs at `http://0.0.0.0:5000` (accessible on local network).

## Usage

### Upload Images
1. Go to the home page
2. Paste an image from clipboard or select a file
3. Get a shareable link instantly

### Manage Access Control
1. Go to "My Images"
2. Click "Visibility" on any image
3. Choose access mode:
   - **Public**: Anyone with link can view
   - **Private - Allow only selected IPs**: Whitelist mode
   - **Private - Block selected IPs**: Blacklist mode

### Create IP Groups
1. Click "Manage Groups" in the visibility modal
2. Create groups with multiple IPs (comma-separated)
3. Click a group to add all IPs at once

### Set Expiration Timer
1. Click "Set Timer" on any image
2. Enter minutes until expiration
3. Link becomes invalid after time expires

## Architecture

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Authentication**: IP-based (no user accounts)
- **File Storage**: Local filesystem

## Configuration

Edit `config.py` to customize:
- `MAX_CONTENT_LENGTH`: File size limit (default 16MB)
- `ALLOWED_EXTENSIONS`: Supported image formats
- `UPLOAD_FOLDER`: Storage directory
- `DATABASE`: SQLite database filename

## Security Notes

- **Encryption**: All images are encrypted at rest using Fernet (AES-256) with PBKDF2 key derivation
- **Password Protection**: The encryption password is required at server startup and must be kept secure
- **Automatic Decryption**: Images are decrypted transparently when accessed via share links
- Designed for trusted local networks
- No HTTPS/TLS (assumes LAN environment)
- IP-based identification (no passwords)
- Share tokens are URL-safe random strings

## Requirements

- Python 3.7+
- Flask
- Pillow (PIL)
- cryptography
- SQLite3

## License

MIT License
