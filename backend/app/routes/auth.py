from flask import Blueprint, request, jsonify
from app.models import User
from ..models import db
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from functools import wraps
import datetime
import bcrypt


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.json

    print(data)

    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "email and password required"}), 400
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "email already exists"}), 400
    user = User(email=data["email"], role="user")

    hashed_password = bcrypt.hashpw(data["password"].encode('utf-8'), bcrypt.gensalt())

    user.set_password(hashed_password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User signuped"}), 200


@auth_bp.route("/signin", methods=["POST"])
def signin():
    data = request.json
    
    user = User.query.filter_by(email=data.get("email")).first()
    if not user:
        return jsonify({'error': 'User not found'}), 400
    elif bcrypt.checkpw(data["password"].encode('utf-8'), user.password):
        token = create_access_token(identity=user.email, fresh=True)
        # Log signin activity
        user.last_signin = datetime.datetime.utcnow()
        db.session.commit()
        return jsonify({"access_token": token, "role": user.role}), 200
    return jsonify({"error": "Invalid password"}), 401


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()
    return jsonify({"email": email, "role": user.role if user else None})

# Refresh the token
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    current_user=get_jwt_identity()
    new_token= create_access_token(identity= current_user)
    return jsonify(access_token= new_token), 200


# Admin-required decorator


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        email = get_jwt_identity()
        user = User.query.filter_by(email=email).first()
        if not user or user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)

    return wrapper


# Example admin-only endpoint
@auth_bp.route("/admin/users", methods=["GET"])
@admin_required
def list_users():
    users = User.query.all()
    return jsonify(
        [
            {
                "email": u.email,
                "role": u.role,
                "created_at": (
                    u.created_at.isoformat() if hasattr(u, "created_at") else None
                ),
                "last_signin": (
                    u.last_signin.isoformat()
                    if hasattr(u, "last_signin") and u.last_signin
                    else None
                ),
            }
            for u in users
        ]
    )


# Admin create user endpoint
@auth_bp.route("/admin/create_user", methods=["POST"])
@admin_required
def create_user():
    data = request.json
    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 400
    user = User(email=data["email"], role=data.get("role", "user"))
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User created successfully"})


# Admin update user role endpoint
@auth_bp.route("/admin/users/<email>/role", methods=["PUT"])
@admin_required
def update_user_role(email):
    data = request.json
    new_role = data.get("role")
    if not new_role or new_role not in ["user", "admin"]:
        return jsonify({"error": "Valid role required"}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.role = new_role
    db.session.commit()
    return jsonify({"message": "Role updated successfully"})


# Admin delete user endpoint
@auth_bp.route("/admin/users/<email>", methods=["DELETE"])
@admin_required
def delete_user(email):
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted successfully"})


# Bulk operations
@auth_bp.route("/admin/users/bulk_role", methods=["PUT"])
@admin_required
def bulk_update_roles():
    data = request.json
    emails = data.get("email", [])
    new_role = data.get("role")
    if not new_role or new_role not in ["user", "admin"]:
        return jsonify({"error": "Valid role required"}), 400
    updated_count = 0
    for email in emails:
        user = User.query.filter_by(email=email).first()
        if user:
            user.role = new_role
            updated_count += 1
    db.session.commit()
    return jsonify({"message": f"{updated_count} users updated successfully"})


@auth_bp.route("/admin/users/bulk_delete", methods=["DELETE"])
@admin_required
def bulk_delete_users():
    data = request.json
    emails = data.get("emails", [])
    deleted_count = 0
    for email in emails:
        user = User.query.filter_by(email=email).first()
        if user:
            db.session.delete(user)
            deleted_count += 1
    db.session.commit()
    return jsonify({"message": f"{deleted_count} users deleted successfully"})


# Password reset endpoint (demo: email + new password)
@auth_bp.route("/reset_password", methods=["POST"])
def reset_password():
    data = request.json
    email = data.get("email")
    new_password = data.get("new_password")
    if not email or not new_password:
        return jsonify({"error": "Email and new password required"}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    return jsonify({"message": "Password reset successful"})
