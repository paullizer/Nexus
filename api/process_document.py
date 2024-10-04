from config import openai, documents_container, jsonify, request, secure_filename, os, tempfile, json, uuid, datetime
from process_conversation import get_conversation_history, list_conversations, update_conversation_thread, delete_conversation_thread, add_system_message_to_conversation
from process_content import extract_text_file, extract_markdown_file, extract_content_with_azure_di, chunk_text, generate_embedding

#***************** Functions *****************
# The functions support document management

def get_user_documents(user_id):
    try:
        # Query to fetch all documents for the given user_id
        query = """
            SELECT c.id, c.file_name, c.upload_date
            FROM c WHERE c.user_id = @user_id AND c.type = 'document_metadata'
        """
        parameters = [
            {"name": "@user_id", "value": user_id}
        ]

        # Perform the query on the container
        items = list(documents_container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))

        return jsonify(items), 200
    except Exception as e:
        print(f"Error fetching documents: {str(e)}")
        return jsonify({'error': 'Error fetching documents'}), 500

def upload_user_document(user_id):
    file = request.files.get('file')

    if not file:
        return jsonify({'error': 'No file uploaded'}), 400

    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1].lower()

    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        file.save(tmp_file.name)
        temp_file_path = tmp_file.name

    extracted_text = ''

    try:
        # Use existing extraction functions
        if file_ext in ['.pdf', '.docx', '.xlsx', '.pptx', '.html',
                        '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.heif']:
            extracted_text = extract_content_with_azure_di(temp_file_path)
        elif file_ext == '.txt':
            extracted_text = extract_text_file(temp_file_path)
        elif file_ext == '.md':
            extracted_text = extract_markdown_file(temp_file_path)
        elif file_ext == '.json':
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                parsed_json = json.load(f)
                extracted_text = json.dumps(parsed_json)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400

        # Process the extracted text and store chunks in 'documents' container
        process_document_and_store_chunks(extracted_text, filename, user_id)

    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    finally:
        os.remove(temp_file_path)

    response_data = {
        'message': 'Document uploaded and processed successfully',
        'file_name': filename
    }

    return jsonify(response_data), 200

def process_document_and_store_chunks(extracted_text, file_name, user_id):
    # Generate a unique ID for the document
    document_id = str(uuid.uuid4())

    # Chunk text
    chunks = chunk_text(extracted_text)

    # Store document metadata (optional)
    document_metadata = {
        "id": document_id,
        "file_name": file_name,
        "user_id": user_id,
        "upload_date": datetime.utcnow().isoformat(),
        "type": "document_metadata"
        # Additional metadata if needed
    }
    documents_container.upsert_item(document_metadata)

    # Process each chunk
    for idx, chunk_text_content in enumerate(chunks):
        chunk_id = f"{document_id}_{idx}"
        embedding = generate_embedding(chunk_text_content)

        # Create chunk document
        chunk_document = {
            "id": chunk_id,
            "document_id": document_id,
            "chunk_id": idx,
            "chunk_text": chunk_text_content,
            "embedding": embedding,
            "metadata": {
                "file_name": file_name,
                "user_id": user_id,
                "chunk_sequence": idx,
                "upload_date": datetime.utcnow().isoformat()
            }
        }

        # Store the chunk document in 'documents' container
        documents_container.upsert_item(chunk_document)

def get_user_document(user_id, document_id):
    try:
        # Retrieve the document from Cosmos DB
        document = documents_container.read_item(item=document_id, partition_key=document_id)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404

        # Check if the document belongs to the user
        if document['user_id'] != user_id:
            return jsonify({'error': 'Unauthorized access'}), 403

        return jsonify(document), 200
    except Exception as e:
        return jsonify({'error': f'Error retrieving document: {str(e)}'}), 500


def delete_user_document(user_id, document_id):
    try:
        # Retrieve the document from Cosmos DB
        document = documents_container.read_item(item=document_id, partition_key=document_id)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404

        # Check if the document belongs to the user
        if document['user_id'] != user_id:
            return jsonify({'error': 'Unauthorized access'}), 403

        # Delete the document from Cosmos DB
        documents_container.delete_item(item=document_id, partition_key=document_id)

        return jsonify({'message': 'Document deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Error deleting document: {str(e)}'}), 500
