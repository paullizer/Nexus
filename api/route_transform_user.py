from config import request, jsonify, uuid, datetime, workflows_container, timezone, transforms_container
from process_workflows import execute_workflow

#***************** Transform *****************
# Routes that handle the transformation of data using workflows

def register_route_transform_user(app):
    @app.route('/api/workflows', methods=['GET', 'POST'])
    def create_workflow():
        if request.method == 'GET':
            try:
                # Get all workflows for the user
                user_id = request.args.get('user_id')

                if not user_id:
                    return jsonify({'error': 'Missing user_id'}), 400

                # Query Cosmos DB for all workflows associated with the user
                query = "SELECT * FROM c WHERE c.user_id = @user_id"
                parameters = [{"name": "@user_id", "value": user_id}]

                workflows = list(workflows_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))

                # Return the list of workflows
                return jsonify({"workflows": workflows}), 200

            except Exception as e:
                return jsonify({'error': f'Error retrieving workflows: {str(e)}'}), 500
        elif request.method == 'POST':    
            try:
                # Get the request data
                data = request.get_json()
                user_id = data.get('user_id')
                name = data.get('name')
                description = data.get('description', '')

                if not user_id:
                    return jsonify({'error': 'Missing user_id'}), 400
                
                if not name:
                    return jsonify({'error': 'Missing name'}), 400
                
                if len(name) < 3:
                    return jsonify({'error': 'Name is too short, minimum length is 3 characters'}), 400
                elif len(name) > 50:
                    return jsonify({'error': 'Name is too long, maximum length is 50 characters'}), 400
                
                # Generate a unique ID for the workflow
                workflow_id = str(uuid.uuid4())

                # Get the current time in UTC
                current_time = datetime.now(timezone.utc)

                # Format it to the desired string format
                formatted_time = current_time.strftime('%Y-%m-%dT%H:%M:%SZ')

                # Create the workflow object
                workflow = {
                    'id': workflow_id,
                    'user_id': user_id,
                    'name': name,
                    'description': description,
                    'actions': [],  # Empty list of actions initially
                    'created_at': formatted_time,
                    'updated_at': formatted_time
                }

                # Store the workflow in Cosmos DB
                workflows_container.upsert_item(workflow)

                # Return the created workflow
                return jsonify(workflow), 201

            except Exception as e:
                return jsonify({'error': f'Error creating workflow: {str(e)}'}), 500
            
    @app.route('/api/workflows/<workflow_id>', methods=['GET', 'PUT', 'DELETE'])
    def handle_specific_workflow(workflow_id):
        user_id = request.args.get('user_id')

        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400

        if request.method == 'GET':
            try:
                # Retrieve the specific workflow
                query = "SELECT * FROM c WHERE c.id = @workflow_id AND c.user_id = @user_id"
                parameters = [
                    {"name": "@workflow_id", "value": workflow_id},
                    {"name": "@user_id", "value": user_id}
                ]

                workflow = list(workflows_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))

                if workflow:
                    return jsonify(workflow[0]), 200
                else:
                    return jsonify({'error': 'Workflow not found'}), 404

            except Exception as e:
                return jsonify({'error': f'Error retrieving workflow: {str(e)}'}), 500

        elif request.method == 'PUT':
            try:
                # Get the workflow data to be updated
                data = request.get_json()
                updated_name = data.get('name')
                updated_description = data.get('description', '')

                if not updated_name or updated_description:
                    return jsonify({'error': 'Must include at least updated name or description or both.'}), 400

                # Retrieve the current workflow to update
                query = "SELECT * FROM c WHERE c.id = @workflow_id AND c.user_id = @user_id"
                parameters = [
                    {"name": "@workflow_id", "value": workflow_id},
                    {"name": "@user_id", "value": user_id}
                ]
                workflow = list(workflows_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))

                if not workflow:
                    return jsonify({'error': 'Workflow not found'}), 404

                # Update the workflow object
                workflow[0]['name'] = updated_name
                workflow[0]['description'] = updated_description
                workflow[0]['updated_at'] = datetime.now().isoformat()

                # Save the updated workflow back to Cosmos DB
                workflows_container.upsert_item(workflow[0])

                return jsonify(workflow[0]), 200

            except Exception as e:
                return jsonify({'error': f'Error updating workflow: {str(e)}'}), 500

        elif request.method == 'DELETE':
            try:
                # Delete the specific workflow from Cosmos DB
                workflows_container.delete_item(item=workflow_id, partition_key=user_id)

                return jsonify({'message': 'Workflow deleted successfully'}), 200

            except Exception as e:
                return jsonify({'error': f'Error deleting workflow: {str(e)}'}), 500

    @app.route('/api/workflows/<workflow_id>/execute', methods=['POST'])
    def execute_workflow_api(workflow_id):
        user_id = request.form.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        result = execute_workflow(workflow_id, user_id)
        
        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), 404
        else:
            return jsonify({'message': 'Workflow executed successfully', 'result': result}), 200


    @app.route('/api/workflows/<workflow_id>/executions/<id>', methods=['GET'])
    def get_execution_status(workflow_id, id):
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        try:
            # Query the "transforms" container for the execution status
            query = "SELECT * FROM c WHERE c.id = @id AND c.workflow_id = @workflow_id AND c.user_id = @user_id"
            parameters = [
                {"name": "@id", "value": id},
                {"name": "@workflow_id", "value": workflow_id},
                {"name": "@user_id", "value": user_id}
            ]
            execution = list(transforms_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
            
            if not execution:
                return jsonify({'error': 'Execution not found'}), 404

            # Return the status of the execution
            return jsonify({'status': execution[0].get('status')}), 200

        except Exception as e:
            return jsonify({'error': f'Error retrieving execution status: {str(e)}'}), 500

    @app.route('/api/workflows/<workflow_id>/executions/<id>/result', methods=['GET'])
    def get_execution_result(workflow_id, id):
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        try:
            # Query the "transforms" container for the execution result
            query = "SELECT * FROM c WHERE c.id = @id AND c.workflow_id = @workflow_id AND c.user_id = @user_id"
            parameters = [
                {"name": "@id", "value": id},
                {"name": "@workflow_id", "value": workflow_id},
                {"name": "@user_id", "value": user_id}
            ]
            execution = list(transforms_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
            
            if not execution:
                return jsonify({'error': 'Execution not found'}), 404

            # Return the result of the execution
            return jsonify({'result': execution[0].get('final_output')}), 200

        except Exception as e:
            return jsonify({'error': f'Error retrieving execution result: {str(e)}'}), 500

    @app.route('/api/workflows/<workflow_id>/actions', methods=['POST'])
    def add_actions_with_parameters_to_workflow(workflow_id):
        # Extract user_id and action details from the request
        user_id = request.form.get('user_id')
        data = request.get_json()
        actions = data.get('actions')

        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400

        if not actions or not isinstance(actions, list):
            return jsonify({'error': 'Invalid actions list'}), 400

        try:
            # Fetch the workflow by workflow_id
            workflow = workflows_container.read_item(item=workflow_id, partition_key=user_id)
            
            # Ensure the actions field exists in the workflow
            if 'actions' not in workflow:
                workflow['actions'] = []

            # Add new actions with parameters to the workflow
            for action in actions:
                if 'action_id' not in action:
                    return jsonify({'error': 'Missing action_id in one of the actions'}), 400

                workflow['actions'].append({
                    "action_id": action['action_id'],
                    "parameters": action.get('parameters', {})  # Default to an empty object if no parameters provided
                })
            
            # Update the workflow in the database
            workflows_container.upsert_item(workflow)
            
            return jsonify({'message': 'Actions added with parameters successfully'}), 200
        
        except Exception as e:
            return jsonify({'error': f'Error adding actions to workflow: {str(e)}'}), 500
