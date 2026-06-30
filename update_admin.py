
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    admin = User.query.filter_by(role='admin').first()
    if admin:
        admin.email = "jareelboi@gmail.com"
        admin.name = "Jareel Boi"
        admin.password_hash = generate_password_hash("PGBWMA11")
        db.session.commit()
        print("Admin updated successfully.")
    else:
        print("No admin found.")