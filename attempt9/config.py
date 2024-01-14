class Config(object):
    SECRET_KEY = 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///containers.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STRIPE_PUBLIC_KEY = 'pk_test_51OOrdBJxVhVlFzT6OiXm7CHTdha9KbmWYIBbH6rVE3lu0oE1niiL9ICECqEjDrxj91Jjf0hSJ930YMUSAwvUzUSJ00Q6Xb1t1f'
    STRIPE_SECRET_KEY = 'sk_test_51OOrdBJxVhVlFzT6R5aUvfjWylPxQL9hStgb7wl3ilvzcozq43IhaDgQ9AQaV2nqJX1Dr8wTIz8KOJmWj4EyILJl00U6T4T3iu'
    STRIPE_WEBHOOK_SECRET = 'whsec_a11df43f0859ebda9e32248536b3562e547760102bd8a41636fee195401c31cd'

# Add other configuration classes if needed for different environments