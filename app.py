from flask import Flask, render_template, request, jsonify, send_from_directory, abort
import os
from werkzeug.utils import secure_filename
from PIL import Image
import io
import base64
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

    client_ip = get_client_ip()

    # Check visibility
    if image['visibility'] == 'private':
        allowed_ips = image['allowed_ips'].split(',') if image['allowed_ips'] else []
        if client_ip not in allowed_ips and client_ip != image['owner_ip']:
            abort(403)

    # Check one-time access
    if image['one_time'] and image['view_count'] > 0:
        abort(410)

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

    conn.execute(
        'UPDATE images SET visibility = ?, allowed_ips = ? WHERE id = ?',
        (visibility, allowed_ips, image_id)
    )
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/api/images/<int:image_id>/one-time', methods=['PUT'])
def set_one_time(image_id):
    client_ip = get_client_ip()
    data = request.json

    conn = get_db()
    image = conn.execute('SELECT * FROM images WHERE id = ?', (image_id,)).fetchone()

    if not image or image['owner_ip'] != client_ip:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403

    one_time = 1 if data.get('one_time') else 0
    conn.execute('UPDATE images SET one_time = ? WHERE id = ?', (one_time, image_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
