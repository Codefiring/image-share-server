# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Image Share Server is a Flask-based local network image sharing service designed for LAN environments. Users are identified by IP address (no authentication system), and the application supports clipboard-based image uploads with various sharing controls.

## Running the Application

```bash
# Quick start (recommended)
./start.sh

# Manual start
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Server runs at `http://0.0.0.0:5000` (accessible on local network).

## Architecture

### Core Design Principles

1. **IP-based User Identity**: No user accounts or authentication. Users are identified solely by their IP address (`get_client_ip()` in app.py handles X-Forwarded-For for proxy scenarios).

2. **Token-based Sharing**: Each uploaded image gets a unique URL-safe token (generated via `secrets.token_urlsafe(16)`). Share URLs follow the pattern `/view/<token>`.

3. **Access Control Model**:
   - **Public images**: Anyone with the link can view
   - **Private images**: Only owner_ip and IPs in the `allowed_ips` comma-separated list can view
   - **One-time links**: Expire after first view (checked via `view_count > 0`)

### Data Flow

**Upload Flow**:
1. Frontend captures clipboard paste event or file selection (static/js/main.js)
2. POST to `/upload` with multipart form data
3. File saved with timestamp prefix: `{timestamp}_{secure_filename}`
4. Database record created with generated share_token
5. Returns share URL to frontend

**View Flow**:
1. GET `/view/<token>`
2. Fetch image record by token
3. Check visibility (private → verify IP in allowed_ips)
4. Check one-time status (if one_time=1 and view_count>0 → 410 Gone)
5. Increment view_count
6. Render image

**Management Flow**:
1. `/manage` queries all images WHERE owner_ip = client_ip
2. Frontend provides buttons for: share, visibility toggle, one-time toggle, delete
3. API endpoints (`/api/images/<id>/*`) verify ownership before mutations

### Database Schema

Single table `images` (SQLite):
- `id`: Primary key
- `filename`: Physical filename in uploads/ directory
- `share_token`: Unique URL-safe token for sharing
- `owner_ip`: IP address of uploader
- `upload_time`: Timestamp
- `visibility`: 'public' or 'private'
- `allowed_ips`: Comma-separated IP whitelist (for private images)
- `one_time`: Boolean (0/1) - if 1, link expires after first view
- `view_count`: Incremented on each view

Database initialized automatically on app startup via `init_db()`.

### File Organization

- **app.py**: All Flask routes and request handling
- **models.py**: Database operations (get_db, init_db, create_image, get_image_by_token)
- **config.py**: Configuration constants (upload folder, file size limits, allowed extensions)
- **templates/**: Jinja2 templates (index.html for upload, manage.html for dashboard, view.html for viewing)
- **static/**: CSS and vanilla JavaScript (no frameworks)
- **uploads/**: Image storage directory (created automatically, gitignored)

## Key Implementation Details

### Filename Handling
Images are saved with timestamp prefixes to avoid collisions:
```python
timestamp = str(int(os.times().elapsed * 1000000))
filename = f"{timestamp}_{filename}"
```

### Authorization Pattern
All mutation endpoints follow this pattern:
```python
client_ip = get_client_ip()
image = conn.execute('SELECT * FROM images WHERE id = ?', (image_id,)).fetchone()
if not image or image['owner_ip'] != client_ip:
    return jsonify({'error': 'Unauthorized'}), 403
```

### Frontend State Management
No JavaScript framework. Pages use inline scripts with direct DOM manipulation and fetch() for API calls. Management page reloads after mutations (`location.reload()`).

## Configuration

Edit `config.py` to change:
- `MAX_CONTENT_LENGTH`: File size limit (default 16MB)
- `ALLOWED_EXTENSIONS`: Supported image formats
- `UPLOAD_FOLDER`: Storage directory
- `DATABASE`: SQLite database filename

## Local Network Deployment

The server binds to `0.0.0.0:5000` to accept connections from any network interface. Users on the same LAN can access via the host's IP address. No HTTPS/TLS configured (assumes trusted local network).

## Limitations & Design Constraints

- No user authentication system (by design for LAN simplicity)
- No image processing/thumbnails (images served as-is)
- SQLite database (single-file, no concurrent write optimization)
- No pagination on management page (all user images loaded at once)
- No tests included in repository
- Debug mode enabled in app.py (change for production)
