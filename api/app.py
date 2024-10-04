from config import openai, AZURE_OPENAI_LLM_MODEL, Flask, redirect, jsonify, render_template, request, send_from_directory, url_for, flash, session, jsonify, secure_filename, os, tempfile, json, uuid
from process_conversation import get_conversation_history, list_conversations, update_conversation_thread, delete_conversation_thread, add_system_message_to_conversation
from process_content import extract_text_file, extract_markdown_file, extract_content_with_azure_di
from process_document import get_user_documents, upload_user_document, get_user_documents, delete_user_document, get_user_document
from process_internet import get_bing_search_results, extract_snippets_from_results

#***************** Flask App *****************

app = Flask(__name__)
app.config['VERSION'] = '0.29'

#***************** Routes *****************

#***************** Chat *****************
@app.route('/api/chat/conversations', methods=['GET'])
def get_conversations():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400
    
    # Fetch the list of conversations for the user
    conversation_list = list_conversations(user_id)
    
    if conversation_list:
        return jsonify(conversation_list), 200
    else:
        return jsonify({'error': 'No conversations found'}), 404

@app.route('/api/chat/conversation/<conversation_id>', methods=['GET', 'DELETE'])
def handle_conversation(conversation_id):
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400

    if request.method == 'GET':
        # Fetch the conversation from Cosmos DB
        conversation_history = get_conversation_history(conversation_id, user_id)
        if conversation_history:
            return jsonify(conversation_history), 200
        else:
            return jsonify({'error': 'Conversation not found or access denied'}), 404

    elif request.method == 'DELETE':
        try:
            success = delete_conversation_thread(conversation_id, user_id)
            if success:
                return jsonify({'message': 'Conversation deleted successfully'}), 200
            else:
                return jsonify({'error': 'Conversation not found or access denied'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_id = data.get('user_id')
    message = data.get('message')
    conversation_id = data.get('conversation_id')  # Frontend can supply this

    if not user_id or not message:
        return jsonify({'error': 'Missing user_id or message'}), 400

    if not conversation_id:
        return jsonify({'error': 'Missing conversation_id'}), 400

    # Retrieve conversation history (thread)
    conversation_history = get_conversation_history(conversation_id, user_id)

    # Prepare messages for OpenAI API
    messages = []
    if conversation_history:
        for entry in conversation_history['thread']:
            if entry.get('role') == 'system':
                messages.append({
                    "role": "system",
                    "content": entry['content']
                })
            else:
                messages.append({
                    "role": "user",
                    "content": entry['user_message']
                })
                messages.append({
                    "role": "assistant",
                    "content": entry['assistant_reply']
                })

    
    # Add the new user message
    messages.append({
        "role": "user",
        "content": message
    })

    # Call the OpenAI API
    try:
        response = openai.ChatCompletion.create(
            engine=AZURE_OPENAI_LLM_MODEL,
            messages=messages
        )
        reply = response['choices'][0]['message']['content']

        # Update the conversation thread in Cosmos DB using upsert
        update_conversation_thread(conversation_id, user_id, message, reply)

        return jsonify({'reply': reply, 'conversation_id': conversation_id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/file', methods=['POST'])
def chat_file():
    user_id = request.form.get('user_id')
    conversation_id = request.form.get('conversation_id')
    file = request.files.get('file')

    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400

    if not file:
        return jsonify({'error': 'No file uploaded'}), 400
    
    if not conversation_id:
        return jsonify({'error': 'Missing conversation_id'}), 400

    # Retrieve the conversation document
    conversation_history = get_conversation_history(conversation_id, user_id)
    if conversation_history is None:
        return jsonify({'error': 'Conversation not found or access denied'}), 403

    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1].lower()

    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        file.save(tmp_file.name)
        temp_file_path = tmp_file.name

    extracted_text = ''
    parsed_json = None

    try:
        if file_ext in ['.pdf', '.docx', '.xlsx', '.pptx', '.html', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.heif']:
            extracted_text = extract_content_with_azure_di(temp_file_path)
        elif file_ext == '.txt':
            extracted_text = extract_text_file(temp_file_path)
        elif file_ext == '.md':
            extracted_text = extract_markdown_file(temp_file_path)
        elif file_ext == '.json':
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                parsed_json = json.load(f)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400

        if not parsed_json and extracted_text:
            try:
                parsed_json = json.loads(extracted_text)
            except json.JSONDecodeError:
                parsed_json = None

    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    finally:
        os.remove(temp_file_path)

    # Add the extracted content to the conversation
    try:
        add_system_message_to_conversation(conversation_id, user_id, extracted_text)
    except Exception as e:
        return jsonify({'error': f'Error adding file content to conversation: {str(e)}'}), 500

    response_data = {
        'message': 'File content added to the conversation successfully'
    }
    if parsed_json:
        response_data['extracted_json'] = parsed_json
    else:
        response_data['extracted_text'] = extracted_text

    return jsonify(response_data), 200

@app.route('/api/chat/internet', methods=['POST'])
def internet_search():
    data = request.get_json()
    user_id = data.get('user_id')
    question = data.get('question')
    conversation_id = data.get('conversation_id')  # Frontend can supply this

    if not question:
        return jsonify({'error': 'Missing question'}), 400

    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400
    
    if not conversation_id:
        return jsonify({'error': 'Missing conversation_id'}), 400

    # Fetch search results from Bing Search API
    search_results = get_bing_search_results(question)
    if search_results is None:
        return jsonify({'error': 'Failed to fetch search results'}), 500
    
    # Extract snippets and URLs from search results
    snippets_with_urls = extract_snippets_from_results(search_results)
    if not snippets_with_urls:
        return jsonify({'error': 'No relevant information found'}), 404
    
    # Format combined_search as a JSON object
    combined_search = {
        "question": question,
        "search_results": [
            {
                "snippet": result['snippet'],
                "url": result['url']
            } for result in snippets_with_urls
        ]
    }
    
    try:
        add_system_message_to_conversation(conversation_id, user_id, json.dumps(combined_search))
    except Exception as e:
        return jsonify({'error': f'Error adding search content to conversation: {str(e)}'}), 500

    # Return both the search results added to conversation history and the OpenAI-generated answer
    response_data = {
        'message': 'Internet search results added to the conversation history successfully',
        'search_results': combined_search
    }

    return jsonify(response_data), 200


#***************** Documents *****************

@app.route('/api/documents', methods=['GET', 'POST'])
def handle_documents():
    # Obtain user_id from authentication context
    user_id = request.form.get('user_id') if request.method == 'POST' else request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400

    if request.method == 'GET':
        # Handle GET request: Retrieve list of documents
        return get_user_documents(user_id)
    elif request.method == 'POST':
        # Handle POST request: Upload a new document
        return upload_user_document(user_id)


@app.route('/api/documents/<document_id>', methods=['GET', 'DELETE'])
def handle_specific_document(document_id):
    # Obtain user_id from authentication context or request
    user_id = request.form.get('user_id') if request.method == 'DELETE' else request.args.get('user_id')

    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400

    if request.method == 'GET':
        # Handle GET request: Retrieve a specific document
        return get_user_document(user_id, document_id)
    
    elif request.method == 'DELETE':
        # Handle DELETE request: Delete a specific document
        return delete_user_document(user_id, document_id)



#***************** Main *****************

if __name__ == '__main__':
    app.run(debug=True)