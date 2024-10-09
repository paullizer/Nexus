from config import actions_container, jsonify

#***************** Functions *****************
# The functions support action processing

def execute_action(action_id, parameters):
    try:
        # Retrieve the action details from the Cosmos DB 'actions' container
        action = actions_container.read_item(item=action_id, partition_key=action_id)

        action_type = action.get('type')
        action_parameters = action.get('parameters', {})
        action_parameters.update(parameters)  # Override or add any parameters passed for this workflow
        
        # Switch based on action type and execute the action
        if action_type == 'generate_summary':
            return jsonify({"action":"generate_summary"}),"200"
        elif action_type == 'document_analysis':
            return jsonify({"action":"document_analysis"}),"200"
        elif action_type == 'custom_prompt':
            return jsonify({"action":"custom_prompt"}),"200"
        else:
            raise Exception(f"Unknown action type: {action_type}")
    
    except Exception as e:
        print(f"Error executing action {action_id}: {str(e)}")
        return {'error': str(e)}
