from config import openai, AZURE_OPENAI_LLM_MODEL, Flask, request, jsonify, secure_filename, os, tempfile, json
from conversation import get_conversation_history, list_conversations, update_conversation_thread, delete_conversation_thread, add_system_message_to_conversation
from content_processing import extract_text_file, extract_markdown_file, extract_content_with_azure_di
from documents import get_user_documents, upload_permanent_document, get_user_documents, upload_permanent_document

#***************** Flask App *****************

app = Flask(__name__)
app.config['VERSION'] = '0.21'

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
        return upload_permanent_document(user_id)




#***************** Main *****************

if __name__ == '__main__':
    app.run(debug=True)