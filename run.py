from app import create_app, db

app = create_app()

if __name__ == '__main__':
    # This automatically creates your flashlearn_db container and all tables if they don't exist yet
    with app.app_context():
        db.create_all()
    
    print("FlashLearn Backend is running on http://127.0.0.1:5000")
    app.run(debug=True)