from config import jsonify

#***************** Actions *****************
# Routes that handle the actions that can be performed in workflows

def register_route_action_user(app):
    @app.route('/api/action', methods=['POST'])
    def create_action():
        # Your action creation logic here
        return "Action created successfully", 201