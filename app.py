import os
import uuid
from flask import Flask, request, render_template_string, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz

# ==================== CONFIGURATION ====================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ==================== DATABASE ====================
db = SQLAlchemy(app)

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(20), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    upload_date = db.Column(db.DateTime, default=lambda: datetime.now(pytz.UTC))
    downloads = db.Column(db.Integer, default=0)

# Create database
with app.app_context():
    db.create_all()

# ==================== READ HTML FILE ====================
def get_html():
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()

# ==================== ROUTES ====================
@app.route('/')
def index():
    notes = Resource.query.filter_by(type='note').order_by(Resource.upload_date.desc()).all()
    pastpapers = Resource.query.filter_by(type='pastpaper').order_by(Resource.upload_date.desc()).all()
    html_content = get_html()
    return render_template_string(html_content, notes=notes, pastpapers=pastpapers)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))
    
    title = request.form.get('title', '')
    description = request.form.get('description', '')
    resource_type = request.form.get('type', 'note')
    
    if file:
        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
        
        resource = Resource(
            title=title,
            description=description,
            type=resource_type,
            filename=unique_filename,
            original_filename=original_filename
        )
        db.session.add(resource)
        db.session.commit()
    
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete_resource(id):
    resource = Resource.query.get_or_404(id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], resource.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    db.session.delete(resource)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/download/<int:id>')
def download_file(id):
    resource = Resource.query.get_or_404(id)
    resource.downloads += 1
    db.session.commit()
    return send_from_directory(
        app.config['UPLOAD_FOLDER'], 
        resource.filename, 
        as_attachment=True,
        download_name=resource.original_filename
    )

@app.route('/statistics')
def statistics():
    total_notes = Resource.query.filter_by(type='note').count()
    total_papers = Resource.query.filter_by(type='pastpaper').count()
    total_downloads = db.session.query(db.func.sum(Resource.downloads)).scalar() or 0
    
    return jsonify({
        'notes': total_notes,
        'pastpapers': total_papers,
        'downloads': total_downloads
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)