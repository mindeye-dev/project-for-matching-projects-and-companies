from flask import Blueprint, request, jsonify
from app.models import User
from app import db
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from functools import wraps
import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    user = User(username=data['username'], role='user')
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User registered'})

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()
    if user and user.check_password(data.get('password')):
        token = create_access_token(identity=user.username)
        # Log login activity
        user.last_login = datetime.datetime.utcnow()
        db.session.commit()
        return jsonify({'access_token': token, 'role': user.role})
    return jsonify({'error': 'Invalid credentials'}), 401

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    return jsonify({'username': username, 'role': user.role if user else None})

# Admin-required decorator

def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        username = get_jwt_identity()
        user = User.query.filter_by(username=username).first()
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return fn(*args, **kwargs)
    return wrapper

# Example admin-only endpoint
@auth_bp.route('/admin/users', methods=['GET'])
@admin_required
def list_users():
    users = User.query.all()
    return jsonify([{
        'username': u.username, 
        'role': u.role,
        'created_at': u.created_at.isoformat() if hasattr(u, 'created_at') else None,
        'last_login': u.last_login.isoformat() if hasattr(u, 'last_login') and u.last_login else None
    } for u in users])

# Admin create user endpoint
@auth_bp.route('/admin/create_user', methods=['POST'])
@admin_required
def create_user():
    data = request.json
    if not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    user = User(username=data['username'], role=data.get('role', 'user'))
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User created successfully'})

# Admin update user role endpoint
@auth_bp.route('/admin/users/<username>/role', methods=['PUT'])
@admin_required
def update_user_role(username):
    data = request.json
    new_role = data.get('role')
    if not new_role or new_role not in ['user', 'admin']:
        return jsonify({'error': 'Valid role required'}), 400
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    user.role = new_role
    db.session.commit()
    return jsonify({'message': 'Role updated successfully'})

# Admin delete user endpoint
@auth_bp.route('/admin/users/<username>', methods=['DELETE'])
@admin_required
def delete_user(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully'})

# Bulk operations
@auth_bp.route('/admin/users/bulk_role', methods=['PUT'])
@admin_required
def bulk_update_roles():
    data = request.json
    usernames = data.get('usernames', [])
    new_role = data.get('role')
    if not new_role or new_role not in ['user', 'admin']:
        return jsonify({'error': 'Valid role required'}), 400
    updated_count = 0
    for username in usernames:
        user = User.query.filter_by(username=username).first()
        if user:
            user.role = new_role
            updated_count += 1
    db.session.commit()
    return jsonify({'message': f'{updated_count} users updated successfully'})

@auth_bp.route('/admin/users/bulk_delete', methods=['DELETE'])
@admin_required
def bulk_delete_users():
    data = request.json
    usernames = data.get('usernames', [])
    deleted_count = 0
    for username in usernames:
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.delete(user)
            deleted_count += 1
    db.session.commit()
    return jsonify({'message': f'{deleted_count} users deleted successfully'})

# Password reset endpoint (demo: username + new password)
@auth_bp.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.json
    username = data.get('username')
    new_password = data.get('new_password')
    if not username or not new_password:
        return jsonify({'error': 'Username and new password required'}), 400
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    return jsonify({'message': 'Password reset successful'}) 