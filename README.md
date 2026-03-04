# Image Share Server

A local network image sharing service with clipboard upload support.

## Features

- 📋 Upload images via clipboard (Ctrl+V)
- 🔗 Generate shareable links
- 🌐 IP-based user identification
- 🎛️ Image management (delete, visibility control)
- ⏱️ One-time share links
- 🔒 Private sharing with IP whitelist

## Quick Start

### Option 1: Using the startup script (Recommended)
```bash
./start.sh
```

### Option 2: Manual setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

The server will start at `http://0.0.0.0:5000`

## Usage

1. **Upload**: Open the website, copy an image, press Ctrl+V
2. **Share**: Copy the generated link and share with others
3. **Manage**: Visit `/manage` to control your uploaded images
4. **View**: Anyone with the link can view the image (unless set to private)

## Features Details

### Upload
- Paste images directly from clipboard
- Or click to select files
- Supports: PNG, JPG, JPEG, GIF, BMP, WEBP

### Image Controls
- **Share**: Generate and copy share link
- **Visibility**: Toggle between public/private, set allowed IPs for private images
- **One-time**: Make link expire after first view
- **Delete**: Remove image permanently

### Security
- Users identified by IP address
- Only owners can manage their images
- Private images require IP whitelist
- One-time links auto-expire

## Project Structure

```
image-share-server/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── models.py           # Database models and functions
├── requirements.txt    # Python dependencies
├── start.sh           # Startup script
├── static/
│   ├── css/style.css  # Styling
│   └── js/main.js     # Frontend logic
├── templates/
│   ├── index.html     # Upload page
│   ├── manage.html    # Management page
│   └── view.html      # Image view page
└── uploads/           # Uploaded images (auto-created)
```

## Network Access

The server binds to `0.0.0.0:5000`, making it accessible to all devices on your local network. Find your server's IP address and share it with others:

```bash
# Linux/Mac
ip addr show | grep inet

# Or use hostname
hostname -I
```

Others can access at: `http://YOUR_IP:5000`
