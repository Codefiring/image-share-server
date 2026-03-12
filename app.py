from flask import Flask, render_template, request, jsonify, send_from_directory, abort
import os
from werkzeug.utils import secure_filename
from PIL import Image
import io
import base64
import secrets
from datetime import datetime, timedelta
from config import Config
from models import init_db, create_image, get_image_by_token, get_db

app = Flask(__name__)
app.config.from_object(Config)

# Create upload folder if it doesn't exist
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

# Initialize database
init_db()

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/manage')
def manage():
    client_ip = get_client_ip()
    conn = get_db()
    images = conn.execute(
        'SELECT * FROM images WHERE owner_ip = ? ORDER BY upload_time DESC',
        (client_ip,)
    ).fetchall()
    conn.close()
    return render_template('manage.html', images=images)

@app.route('/gallery')
def gallery():
    conn = get_db()
    images = conn.execute(
        'SELECT * FROM images WHERE visibility = ? AND active = 1 ORDER BY upload_time DESC',
        ('public',)
    ).fetchall()
    conn.close()
    return render_template('gallery.html', images=images)

@app.route('/upload', methods=['POST'])
def upload():
    client_ip = get_client_ip()

    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = str(int(os.times().elapsed * 1000000))
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)

        share_token = create_image(filename, client_ip)
        return jsonify({
            'success': True,
            'share_token': share_token,
            'share_url': request.host_url + 'view/' + share_token
        })

    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/view/<token>')
def view_image(token):
    image = get_image_by_token(token)
    if not image:
        abort(404)

    # Check if share link is active
    if not image['active']:
        abort(403)

    # Check if link has expired
    if image['expires_at']:
        expires_at = datetime.fromisoformat(image['expires_at'])
        if datetime.now() > expires_at:
            abort(410)

    client_ip = get_client_ip()

    # Check visibility - owner always has access
    if client_ip != image['owner_ip']:
        if image['visibility'] == 'whitelist' or image['visibility'] == 'private':
            # Only allowed IPs can view (private is legacy, treated as whitelist)
            allowed_ips = [ip.strip() for ip in image['allowed_ips'].split(',') if ip.strip()] if image['allowed_ips'] else []
            if client_ip not in allowed_ips:
                abort(403)
        elif image['visibility'] == 'blacklist':
            # Everyone except blocked IPs can view
            blocked_ips = [ip.strip() for ip in image['blocked_ips'].split(',') if ip.strip()] if image['blocked_ips'] else []
            if client_ip in blocked_ips:
                abort(403)
        # else: visibility == 'public', allow access

    # Update view count
    conn = get_db()
    conn.execute('UPDATE images SET view_count = view_count + 1 WHERE id = ?', (image['id'],))
    conn.commit()
    conn.close()

    return render_template('view.html', image=image)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)

@app.route('/api/images/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    client_ip = get_client_ip()
    conn = get_db()
    image = conn.execute('SELECT * FROM images WHERE id = ?', (image_id,)).fetchone()

    if not image or image['owner_ip'] != client_ip:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403

    # Delete file
    filepath = os.path.join(Config.UPLOAD_FOLDER, image['filename'])
    if os.path.exists(filepath):
        os.remove(filepath)

    # Delete from database
    conn.execute('DELETE FROM images WHERE id = ?', (image_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/api/images/<int:image_id>/visibility', methods=['PUT'])
def update_visibility(image_id):
    client_ip = get_client_ip()
    data = request.json

    conn = get_db()
    image = conn.execute('SELECT * FROM images WHERE id = ?', (image_id,)).fetchone()

    if not image or image['owner_ip'] != client_ip:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403

    visibility = data.get('visibility', 'public')
    allowed_ips = data.get('allowed_ips', '')
    blocked_ips = data.get('blocked_ips', '')

    # Validate visibility value
    if visibility not in ['public', 'whitelist', 'blacklist', 'private']:
        conn.close()
        return jsonify({'error': 'Invalid visibility value'}), 400

    # Generate new share token when settings change
    new_token = secrets.token_urlsafe(16)

    conn.execute(
        'UPDATE images SET visibility = ?, allowed_ips = ?, blocked_ips = ?, share_token = ? WHERE id = ?',
        (visibility, allowed_ips, blocked_ips, new_token, image_id)
    )
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'new_token': new_token})

@app.route('/api/images/<int:image_id>/expiration', methods=['PUT'])
def set_expiration(image_id):
    client_ip = get_client_ip()
    data = request.json

    conn = get_db()
    image = conn.execute('SELECT * FROM images WHERE id = ?', (image_id,)).fetchone()

    if not image or image['owner_ip'] != client_ip:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403

    minutes = data.get('minutes', 0)
    expires_at = None
    if minutes > 0:
        expires_at = datetime.now() + timedelta(minutes=minutes)

    # Generate new share token when settings change
    new_token = secrets.token_urlsafe(16)

    conn.execute('UPDATE images SET expires_at = ?, share_token = ? WHERE id = ?', (expires_at, new_token, image_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'new_token': new_token})

@app.route('/api/images/<int:image_id>/toggle-active', methods=['PUT'])
def toggle_active(image_id):
    client_ip = get_client_ip()
    data = request.json

    conn = get_db()
    image = conn.execute('SELECT * FROM images WHERE id = ?', (image_id,)).fetchone()

    if not image or image['owner_ip'] != client_ip:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403

    active = 1 if data.get('active') else 0
    conn.execute('UPDATE images SET active = ? WHERE id = ?', (active, image_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/api/ip-nicknames', methods=['GET'])
def get_ip_nicknames():
    client_ip = get_client_ip()
    conn = get_db()
    nicknames = conn.execute(
        'SELECT * FROM ip_nicknames WHERE owner_ip = ? ORDER BY nickname',
        (client_ip,)
    ).fetchall()
    conn.close()
    return jsonify([dict(n) for n in nicknames])

@app.route('/api/ip-nicknames', methods=['POST'])
def create_ip_nickname():
    client_ip = get_client_ip()
    data = request.json
    ip_address = data.get('ip_address', '').strip()
    nickname = data.get('nickname', '').strip()

    if not ip_address or not nickname:
        return jsonify({'error': 'IP address and nickname are required'}), 400

    conn = get_db()
    try:
        conn.execute(
            'INSERT INTO ip_nicknames (owner_ip, ip_address, nickname) VALUES (?, ?, ?)',
            (client_ip, ip_address, nickname)
        )
        conn.commit()
        nickname_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.close()
        return jsonify({'success': True, 'id': nickname_id})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Nickname for this IP already exists'}), 400

@app.route('/api/ip-nicknames/<int:nickname_id>', methods=['PUT'])
def update_ip_nickname(nickname_id):
    client_ip = get_client_ip()
    data = request.json

    conn = get_db()
    nickname = conn.execute('SELECT * FROM ip_nicknames WHERE id = ?', (nickname_id,)).fetchone()

    if not nickname or nickname['owner_ip'] != client_ip:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403

    new_nickname = data.get('nickname', '').strip()
    if not new_nickname:
        conn.close()
        return jsonify({'error': 'Nickname is required'}), 400

    conn.execute('UPDATE ip_nicknames SET nickname = ? WHERE id = ?', (new_nickname, nickname_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/api/ip-nicknames/<int:nickname_id>', methods=['DELETE'])
def delete_ip_nickname(nickname_id):
    client_ip = get_client_ip()
    conn = get_db()
    nickname = conn.execute('SELECT * FROM ip_nicknames WHERE id = ?', (nickname_id,)).fetchone()

    if not nickname or nickname['owner_ip'] != client_ip:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403

    conn.execute('DELETE FROM ip_nicknames WHERE id = ?', (nickname_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/api/ip-groups', methods=['GET'])
def get_ip_groups():
    client_ip = get_client_ip()
    conn = get_db()
    groups = conn.execute(
        'SELECT * FROM ip_groups WHERE owner_ip = ? ORDER BY group_name',
        (client_ip,)
    ).fetchall()
    conn.close()
    return jsonify([dict(g) for g in groups])

@app.route('/api/ip-groups', methods=['POST'])
def create_ip_group():
    client_ip = get_client_ip()
    data = request.json
    group_name = data.get('group_name', '').strip()
    ip_addresses = data.get('ip_addresses', '').strip()

    if not group_name or not ip_addresses:
        return jsonify({'error': 'Group name and IP addresses are required'}), 400

    conn = get_db()
    try:
        conn.execute(
            'INSERT INTO ip_groups (owner_ip, group_name, ip_addresses) VALUES (?, ?, ?)',
            (client_ip, group_name, ip_addresses)
        )
        conn.commit()
        group_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.close()
        return jsonify({'success': True, 'id': group_id})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Group with this name already exists'}), 400

@app.route('/api/ip-groups/<int:group_id>', methods=['PUT'])
def update_ip_group(group_id):
    client_ip = get_client_ip()
    data = request.json

    conn = get_db()
    group = conn.execute('SELECT * FROM ip_groups WHERE id = ?', (group_id,)).fetchone()

    if not group or group['owner_ip'] != client_ip:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403

    group_name = data.get('group_name', '').strip()
    ip_addresses = data.get('ip_addresses', '').strip()

    if not group_name or not ip_addresses:
        conn.close()
        return jsonify({'error': 'Group name and IP addresses are required'}), 400

    conn.execute(
        'UPDATE ip_groups SET group_name = ?, ip_addresses = ? WHERE id = ?',
        (group_name, ip_addresses, group_id)
    )
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/api/ip-groups/<int:group_id>', methods=['DELETE'])
def delete_ip_group(group_id):
    client_ip = get_client_ip()
    conn = get_db()
    group = conn.execute('SELECT * FROM ip_groups WHERE id = ?', (group_id,)).fetchone()

    if not group or group['owner_ip'] != client_ip:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403

    conn.execute('DELETE FROM ip_groups WHERE id = ?', (group_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/api/images/<int:image_id>/expiration', methods=['GET'])
def get_expiration(image_id):
    client_ip = get_client_ip()
    conn = get_db()
    image = conn.execute('SELECT expires_at FROM images WHERE id = ?', (image_id,)).fetchone()

    if not image or conn.execute('SELECT owner_ip FROM images WHERE id = ?', (image_id,)).fetchone()['owner_ip'] != client_ip:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403

    conn.close()
    return jsonify({'expires_at': image['expires_at']})

@app.route('/api/images/<int:image_id>/allowed-ips', methods=['GET'])
def get_image_allowed_ips(image_id):
    client_ip = get_client_ip()
    conn = get_db()
    image = conn.execute('SELECT * FROM images WHERE id = ?', (image_id,)).fetchone()

    if not image or image['owner_ip'] != client_ip:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403

    allowed_ips = image['allowed_ips'].split(',') if image['allowed_ips'] else []

    # Get nicknames for allowed IPs
    allowed_ip_list = []
    for ip in allowed_ips:
        ip = ip.strip()
        if ip:
            nickname_row = conn.execute(
                'SELECT nickname FROM ip_nicknames WHERE owner_ip = ? AND ip_address = ?',
                (client_ip, ip)
            ).fetchone()
            allowed_ip_list.append({
                'ip': ip,
                'nickname': nickname_row['nickname'] if nickname_row else None
            })

    # Process blocked IPs
    blocked_ips = image['blocked_ips'].split(',') if image['blocked_ips'] else []
    blocked_ip_list = []
    for ip in blocked_ips:
        ip = ip.strip()
        if ip:
            nickname_row = conn.execute(
                'SELECT nickname FROM ip_nicknames WHERE owner_ip = ? AND ip_address = ?',
                (client_ip, ip)
            ).fetchone()
            blocked_ip_list.append({
                'ip': ip,
                'nickname': nickname_row['nickname'] if nickname_row else None
            })

    conn.close()
    return jsonify({
        'visibility': image['visibility'],
        'allowed_ips': allowed_ip_list,
        'blocked_ips': blocked_ip_list
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
