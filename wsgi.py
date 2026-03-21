import os
from app import create_app
from app import db
from models import User, Conversation, Message, Document

app = create_app()

if __name__ == '__main__':
    app.run()
