from app import create_app


# we call the create app function thats in app/_init.py to set up the app with all specified configs
app = create_app()


if __name__ == '__main__':
    print("FlashLearn Backend is starting...")
    app.run(debug=True, port=5000)
    #in production I shall set debug to false for security .