from config import workflows_container, jsonify
from process_actions import execute_action

#***************** Functions *****************
# The functions support workflow processing

def get_workflow_by_id(workflow_id, user_id):
    try:
        # Query the Cosmos DB container for the specific workflow
        workflow = workflows_container.read_item(item=workflow_id, partition_key=user_id)
        return workflow
    except Exception as e:
        print(f"Error retrieving workflow with ID {workflow_id}: {str(e)}")
        return None

def execute_workflow(workflow_id, user_id):
    workflow = get_workflow_by_id(workflow_id, user_id)
    
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404

    # Loop through actions and execute them
    for action in workflow['actions']:
        action_id = action['action_id']
        parameters = action.get('parameters', {})  # Retrieve the action parameters
        
        # Execute the action with its parameters
        execute_action(action_id, parameters)
