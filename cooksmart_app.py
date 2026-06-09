from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import json
import pymysql
import os
pymysql.install_as_MySQLdb()

app = Flask(__name__)
CORS(app)

# ✅ Reads from Railway environment variable
db_url = os.environ.get('DATABASE_URL', '')
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'cooksmart_secret_key'

db = SQLAlchemy(app)


# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name       = db.Column(db.String(255), nullable=False)
    email      = db.Column(db.String(255), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActiveSession(db.Model):
    __tablename__ = 'active_sessions'
    id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email    = db.Column(db.String(255), nullable=False)
    login_at = db.Column(db.DateTime, default=datetime.utcnow)

class Recipe(db.Model):
    __tablename__ = 'recipes'
    id                   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id              = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title                = db.Column(db.String(255), nullable=False)
    description          = db.Column(db.Text, nullable=True)
    ingredients          = db.Column(db.Text, nullable=False)
    steps                = db.Column(db.Text, nullable=False)
    cooking_time_minutes = db.Column(db.Integer, default=30)
    servings             = db.Column(db.Integer, default=2)
    spice_level          = db.Column(db.String(50),  default='Medium')
    cuisine              = db.Column(db.String(100), default='International')
    diet_type            = db.Column(db.String(50),  nullable=True)
    match_type           = db.Column(db.String(20),  default='full')
    match_percentage     = db.Column(db.Integer, default=100)
    image_emoji          = db.Column(db.String(10),  nullable=True)
    calories             = db.Column(db.Integer, default=0)
    protein              = db.Column(db.Numeric(6, 2), default=0.00)
    carbs                = db.Column(db.Numeric(6, 2), default=0.00)
    fat                  = db.Column(db.Numeric(6, 2), default=0.00)
    fiber                = db.Column(db.Numeric(6, 2), default=0.00)
    is_favorite          = db.Column(db.Boolean, default=False)
    created_at           = db.Column(db.DateTime, default=datetime.utcnow)

class MealPlan(db.Model):
    __tablename__ = 'meal_plans'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_date  = db.Column(db.Date, nullable=False)
    meal_type  = db.Column(db.String(20), nullable=False)
    meal_name  = db.Column(db.String(255), nullable=False)
    recipe_id  = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Feedback(db.Model):
    __tablename__ = 'feedback'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating     = db.Column(db.Integer, nullable=True)
    category   = db.Column(db.String(50), default='General')
    message    = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ScanHistory(db.Model):
    __tablename__ = 'scan_history'
    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    scanned_at  = db.Column(db.DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def recipe_to_dict(r):
    return {
        'id':                   r.id,
        'title':                r.title,
        'description':          r.description,
        'ingredients':          json.loads(r.ingredients) if r.ingredients else [],
        'steps':                json.loads(r.steps) if r.steps else [],
        'cooking_time_minutes': r.cooking_time_minutes,
        'servings':             r.servings,
        'spice_level':          r.spice_level,
        'cuisine':              r.cuisine,
        'diet_type':            r.diet_type,
        'match_type':           r.match_type,
        'match_percentage':     r.match_percentage,
        'image_emoji':          r.image_emoji,
        'nutrition': {
            'calories': r.calories,
            'protein':  float(r.protein),
            'carbs':    float(r.carbs),
            'fat':      float(r.fat),
            'fiber':    float(r.fiber),
        },
        'is_favorite': r.is_favorite,
        'created_at':  r.created_at.strftime('%d %b %Y') if r.created_at else None,
    }


# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────

@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        required = ['name', 'email', 'password', 'confirm_password']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        if data['password'] != data['confirm_password']:
            return jsonify({'error': 'Passwords do not match'}), 400
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 409
        new_user = User(
            name=data['name'],
            email=data['email'],
            password=generate_password_hash(data['password'])
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'Account created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Email and password required'}), 400
        user = User.query.filter_by(email=data['email']).first()
        if not user or not check_password_hash(user.password, data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401
        session = ActiveSession(email=user.email)
        db.session.add(session)
        db.session.commit()
        return jsonify({
            'message': 'Login successful',
            'user': {'id': user.id, 'name': user.name, 'email': user.email}
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/get_current_user', methods=['GET'])
def get_current_user():
    try:
        last = ActiveSession.query.order_by(ActiveSession.id.desc()).first()
        if not last:
            return jsonify({'error': 'No active user found'}), 404
        user = User.query.filter_by(email=last.email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'id': user.id, 'name': user.name, 'email': user.email}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/logout', methods=['POST'])
def logout():
    try:
        data = request.get_json()
        if data and 'email' in data:
            ActiveSession.query.filter_by(email=data['email']).delete()
            db.session.commit()
        return jsonify({'message': 'Logged out successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# RECIPES
# ─────────────────────────────────────────

@app.route('/recipes/<int:user_id>', methods=['GET'])
def get_recipes(user_id):
    try:
        fav_only = request.args.get('favorite', 'false').lower() == 'true'
        q = Recipe.query.filter_by(user_id=user_id)
        if fav_only:
            q = q.filter_by(is_favorite=True)
        recipes = q.order_by(Recipe.created_at.desc()).all()
        return jsonify([recipe_to_dict(r) for r in recipes]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/recipes', methods=['POST'])
def save_recipe():
    try:
        data     = request.get_json()
        required = ['user_id', 'title', 'ingredients', 'steps']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        nutrition = data.get('nutrition', {})
        recipe = Recipe(
            user_id              = data['user_id'],
            title                = data['title'],
            description          = data.get('description', ''),
            ingredients          = json.dumps(data['ingredients']),
            steps                = json.dumps(data['steps']),
            cooking_time_minutes = data.get('cooking_time_minutes', 30),
            servings             = data.get('servings', 2),
            spice_level          = data.get('spice_level', 'Medium'),
            cuisine              = data.get('cuisine', 'International'),
            diet_type            = data.get('diet_type'),
            match_type           = data.get('match_type', 'full'),
            match_percentage     = data.get('match_percentage', 100),
            image_emoji          = data.get('image_emoji'),
            calories             = nutrition.get('calories', 0),
            protein              = nutrition.get('protein', 0.0),
            carbs                = nutrition.get('carbs', 0.0),
            fat                  = nutrition.get('fat', 0.0),
            fiber                = nutrition.get('fiber', 0.0),
            is_favorite          = data.get('is_favorite', False),
        )
        db.session.add(recipe)
        db.session.commit()
        return jsonify({'message': 'Recipe saved', 'id': recipe.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/recipes/<int:recipe_id>/favorite', methods=['POST'])
def toggle_favorite(recipe_id):
    try:
        recipe = Recipe.query.get(recipe_id)
        if not recipe:
            return jsonify({'error': 'Recipe not found'}), 404
        recipe.is_favorite = not recipe.is_favorite
        db.session.commit()
        return jsonify({'message': 'Favorite updated', 'is_favorite': recipe.is_favorite}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/recipes/<int:recipe_id>', methods=['DELETE'])
def delete_recipe(recipe_id):
    try:
        recipe = Recipe.query.get(recipe_id)
        if not recipe:
            return jsonify({'error': 'Recipe not found'}), 404
        db.session.delete(recipe)
        db.session.commit()
        return jsonify({'message': 'Recipe deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# MEAL PLANNER
# ─────────────────────────────────────────

@app.route('/meal_plan/<int:user_id>', methods=['GET'])
def get_meal_plan(user_id):
    try:
        plan_date_str = request.args.get('date', date.today().isoformat())
        plan_date     = date.fromisoformat(plan_date_str)
        entries       = MealPlan.query.filter_by(user_id=user_id, plan_date=plan_date).all()
        result = {}
        for e in entries:
            result[e.meal_type] = {'id': e.id, 'meal_name': e.meal_name, 'recipe_id': e.recipe_id}
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/meal_plan/range/<int:user_id>', methods=['GET'])
def get_meal_plan_range(user_id):
    try:
        start   = date.fromisoformat(request.args.get('start', date.today().isoformat()))
        end     = date.fromisoformat(request.args.get('end',   date.today().isoformat()))
        entries = MealPlan.query.filter(
            MealPlan.user_id   == user_id,
            MealPlan.plan_date >= start,
            MealPlan.plan_date <= end
        ).all()
        result = {}
        for e in entries:
            key = e.plan_date.isoformat()
            if key not in result:
                result[key] = {}
            result[key][e.meal_type] = {'id': e.id, 'meal_name': e.meal_name, 'recipe_id': e.recipe_id}
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/meal_plan', methods=['POST'])
def save_meal_plan():
    try:
        data     = request.get_json()
        required = ['user_id', 'plan_date', 'meal_type', 'meal_name']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        plan_date = date.fromisoformat(data['plan_date'])
        existing  = MealPlan.query.filter_by(
            user_id=data['user_id'], plan_date=plan_date, meal_type=data['meal_type']
        ).first()
        if existing:
            existing.meal_name = data['meal_name']
            existing.recipe_id = data.get('recipe_id')
        else:
            entry = MealPlan(
                user_id=data['user_id'], plan_date=plan_date,
                meal_type=data['meal_type'], meal_name=data['meal_name'],
                recipe_id=data.get('recipe_id'),
            )
            db.session.add(entry)
        db.session.commit()
        return jsonify({'message': 'Meal plan saved'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/meal_plan/<int:entry_id>', methods=['DELETE'])
def delete_meal_plan(entry_id):
    try:
        entry = MealPlan.query.get(entry_id)
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404
        db.session.delete(entry)
        db.session.commit()
        return jsonify({'message': 'Meal plan entry deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# SCAN HISTORY
# ─────────────────────────────────────────

@app.route('/scan_history/<int:user_id>', methods=['GET'])
def get_scan_history(user_id):
    try:
        scans = ScanHistory.query.filter_by(user_id=user_id)\
            .order_by(ScanHistory.scanned_at.desc()).limit(10).all()
        return jsonify([{
            'id':          s.id,
            'ingredients': json.loads(s.ingredients) if s.ingredients else [],
            'scanned_at':  s.scanned_at.strftime('%d %b %Y, %I:%M %p'),
        } for s in scans]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/scan_history', methods=['POST'])
def save_scan():
    try:
        data = request.get_json()
        if not data or 'user_id' not in data or 'ingredients' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        scan = ScanHistory(user_id=data['user_id'], ingredients=json.dumps(data['ingredients']))
        db.session.add(scan)
        db.session.commit()
        return jsonify({'message': 'Scan saved', 'id': scan.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/scan_history/<int:scan_id>', methods=['DELETE'])
def delete_scan(scan_id):
    try:
        scan = ScanHistory.query.get(scan_id)
        if not scan:
            return jsonify({'error': 'Scan not found'}), 404
        db.session.delete(scan)
        db.session.commit()
        return jsonify({'message': 'Scan deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# FEEDBACK
# ─────────────────────────────────────────

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    try:
        data = request.get_json()
        if not data or 'user_id' not in data:
            return jsonify({'error': 'user_id is required'}), 400
        fb = Feedback(
            user_id=data['user_id'], rating=data.get('rating'),
            category=data.get('category', 'General'), message=data.get('message', '')
        )
        db.session.add(fb)
        db.session.commit()
        return jsonify({'message': 'Feedback submitted. Thank you!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/feedback/<int:user_id>', methods=['GET'])
def get_feedback(user_id):
    try:
        feedbacks = Feedback.query.filter_by(user_id=user_id)\
            .order_by(Feedback.created_at.desc()).all()
        return jsonify([{
            'id': f.id, 'rating': f.rating, 'category': f.category,
            'message': f.message, 'created_at': f.created_at.strftime('%d %b %Y'),
        } for f in feedbacks]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────

@app.route('/profile/<int:user_id>', methods=['GET'])
def get_profile(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        fav_count    = Recipe.query.filter_by(user_id=user_id, is_favorite=True).count()
        total_saved  = Recipe.query.filter_by(user_id=user_id).count()
        planned_days = db.session.execute(db.text(
            "SELECT COUNT(DISTINCT plan_date) FROM meal_plans WHERE user_id = :uid"
        ), {'uid': user_id}).scalar()
        return jsonify({
            'id': user.id, 'name': user.name, 'email': user.email,
            'created_at': user.created_at.strftime('%d %b %Y') if user.created_at else None,
            'stats': {
                'favorites': fav_count, 'recipes_saved': total_saved,
                'planned_days': planned_days or 0,
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/profile/<int:user_id>', methods=['PUT'])
def update_profile(user_id):
    try:
        data = request.get_json()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        user.name = data.get('name', user.name)
        if 'password' in data and data['password']:
            user.password = generate_password_hash(data['password'])
        db.session.commit()
        return jsonify({'message': 'Profile updated'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────

@app.route('/dashboard/<int:user_id>', methods=['GET'])
def get_dashboard(user_id):
    try:
        today          = date.today()
        fav_count      = Recipe.query.filter_by(user_id=user_id, is_favorite=True).count()
        total_recipes  = Recipe.query.filter_by(user_id=user_id).count()
        todays_meals_raw = MealPlan.query.filter_by(user_id=user_id, plan_date=today).all()
        todays_meals   = {e.meal_type: e.meal_name for e in todays_meals_raw}
        recent_scans   = ScanHistory.query.filter_by(user_id=user_id)\
            .order_by(ScanHistory.scanned_at.desc()).limit(3).all()
        recent_favs    = Recipe.query.filter_by(user_id=user_id, is_favorite=True)\
            .order_by(Recipe.created_at.desc()).limit(4).all()
        month_str      = today.strftime('%Y-%m')
        planned_this_month = db.session.execute(db.text("""
            SELECT COUNT(DISTINCT plan_date) FROM meal_plans
            WHERE user_id = :uid AND DATE_FORMAT(plan_date, '%Y-%m') = :month
        """), {'uid': user_id, 'month': month_str}).scalar()
        return jsonify({
            'stats': {
                'favorites': fav_count, 'total_recipes': total_recipes,
                'planned_this_month': planned_this_month or 0,
            },
            'todays_meals': todays_meals,
            'recent_scans': [{
                'id': s.id,
                'ingredients': json.loads(s.ingredients) if s.ingredients else [],
                'scanned_at': s.scanned_at.strftime('%d %b %Y'),
            } for s in recent_scans],
            'recent_favorites': [recipe_to_dict(r) for r in recent_favs],
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
