from config import Flask
from route_chat_user import register_route_chat_user
from route_document_user import register_route_document_user
from route_transform_user import register_route_transform_user
from route_action_user import register_route_action_user

#***************** Flask App *****************
app = Flask(__name__)
app.config['VERSION'] = '0.75'

#***************** Routes *****************
# Routes that handle the API endpoints for the application

#***************** User *****************
# Routes that handle the user management functionality

#***************** Chat *****************
# Routes that handle the conversational AI functionality
register_route_chat_user(app)

#***************** Document *****************
# Routes that handle the document management functionality
register_route_document_user(app)

#***************** Transform *****************
# Routes that handle the transformation of data using workflows
register_route_transform_user(app)

#***************** Actions *****************
# Routes that handle the actions that can be performed in workflows
register_route_action_user(app)

#***************** Main *****************
if __name__ == '__main__':
    app.run(debug=True)