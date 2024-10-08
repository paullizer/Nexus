from config import Flask
from route_chat_user import register_route_chat_user
from route_document_user import register_route_document_user

#***************** Flask App *****************
app = Flask(__name__)
app.config['VERSION'] = '0.66'

#***************** Routes *****************
# Routes that handle the API endpoints for the application

#***************** User *****************
# Routes that handle the user management functionality

#***************** Chat *****************
# Routes that handle the conversational AI functionality
register_route_chat_user(app)

#***************** Documents *****************
# Routes that handle the document management functionality
register_route_document_user(app)

#***************** Main *****************
if __name__ == '__main__':
    app.run(debug=True)