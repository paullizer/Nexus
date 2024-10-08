from config import openai, documents_container, jsonify, request, secure_filename, os, tempfile, json, uuid, datetime, timezone, search_client_user, search_client_group
from process_content import extract_text_file, extract_markdown_file, extract_content_with_azure_di, chunk_text, generate_embedding

#***************** Functions *****************
# The functions support document management

def get_user_documents(user_id):
    try:
        # Query to get the latest version of each document for the user
        query = """
            SELECT TOP 100 c.id, c.file_name, c.user_id, c.upload_date, c.version
            FROM c
            WHERE c.user_id = @user_id
            ORDER BY c.upload_date DESC
        """
        parameters = [{"name": "@user_id", "value": user_id}]
        documents = list(documents_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

        # Process to get the latest version of each document
        latest_documents = {}
        for document in documents:
            doc_id = document['id']
            if doc_id not in latest_documents or document['version'] > latest_documents[doc_id]['version']:
                latest_documents[doc_id] = document

        return jsonify({"documents": list(latest_documents.values())}), 200

    except Exception as e:
        return jsonify({'error': f'Error retrieving documents: {str(e)}'}), 500

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
    document_id = str(uuid.uuid4())  # Unique ID for the document
    chunks = chunk_text(extracted_text)  # Chunk the text

    # Check existing version for this document
    existing_document_query = """
        SELECT c.version 
        FROM c 
        WHERE c.file_name = @file_name AND c.user_id = @user_id
    """
    parameters = [{"name": "@file_name", "value": file_name}, {"name": "@user_id", "value": user_id}]
    existing_document = list(documents_container.query_items(query=existing_document_query, parameters=parameters, enable_cross_partition_query=True))

    # Determine the new version number
    version = existing_document[0]['version'] + 1 if existing_document else 1

    # Store document metadata
    document_metadata = {
        "id": document_id,
        "file_name": file_name,
        "user_id": user_id,
        "upload_date": datetime.now(timezone.utc).isoformat() + 'Z',
        "version": version,  # Add version information
        "type": "document_metadata"
    }
    documents_container.upsert_item(document_metadata)

    # Process each chunk
    for idx, chunk_text_content in enumerate(chunks):
        chunk_id = f"{document_id}_{idx}"  # Create a unique chunk ID
        embedding = generate_embedding(chunk_text_content)  # Generate embedding

        # Create chunk document with versioning
        chunk_document = {
            "id": chunk_id,
            "document_id": document_id,
            "chunk_id": str(idx),  # Ensure chunk_id is a string
            "chunk_text": chunk_text_content,
            "embedding": embedding,
            "file_name": file_name,
            "user_id": user_id,
            "chunk_sequence": idx,  # Convert to string if needed
            "upload_date": datetime.now(timezone.utc).isoformat() + 'Z',
            "version": version  # Add version information to the chunk
        }

        # Store the chunk document in 'documents' container
        documents_container.upsert_item(chunk_document)

def get_user_document(user_id, document_id):
    try:
        # Retrieve the latest version of the document
        latest_version_query = """
            SELECT TOP 1 *
            FROM c 
            WHERE c.document_id = @document_id AND c.user_id = @user_id
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@user_id", "value": user_id}
        ]
        document_results = list(documents_container.query_items(query=latest_version_query, parameters=parameters, enable_cross_partition_query=True))

        if not document_results:
            return jsonify({'error': 'Document not found or access denied'}), 404

        return jsonify(document_results[0]), 200  # Return the latest version of the document

    except Exception as e:
        return jsonify({'error': f'Error retrieving document: {str(e)}'}), 500

def get_latest_version(document_id, user_id):
    query = """
        SELECT MAX(c.version) as max_version
        FROM c 
        WHERE c.document_id = @document_id AND c.user_id = @user_id
    """
    parameters = [
        {"name": "@document_id", "value": document_id},
        {"name": "@user_id", "value": user_id}
    ]
    results = list(documents_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
    return results[0]['max_version'] if results and 'max_version' in results[0] else None

def get_user_document_version(user_id, document_id, version):
    try:
        # Query to retrieve the specific version of the document
        query = """
            SELECT *
            FROM c 
            WHERE c.document_id = @document_id AND c.user_id = @user_id AND c.version = @version
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@user_id", "value": user_id},
            {"name": "@version", "value": version}
        ]
        
        document_results = list(documents_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

        if not document_results:
            return jsonify({'error': 'Document version not found'}), 404

        return jsonify(document_results[0]), 200  # Return the specific version of the document

    except Exception as e:
        return jsonify({'error': f'Error retrieving document version: {str(e)}'}), 500

   
def delete_user_document(user_id, document_id):
    # Query to find all versions of the document by user_id
    query = """
        SELECT c.id 
        FROM c 
        WHERE c.document_id = @document_id AND c.user_id = @user_id
    """
    parameters = [
        {"name": "@document_id", "value": document_id},
        {"name": "@user_id", "value": user_id}
    ]
    documents = list(documents_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    # Delete each document version
    for doc in documents:
        documents_container.delete_item(doc['id'], partition_key=doc['user_id'])

def delete_user_document_chunks(document_id):
    # Use Azure AI Search to delete all chunks related to the document
    search_client_user.delete_documents(
        actions=[
            {"@search.action": "delete", "id": chunk['id']} for chunk in 
            search_client_user.search(
                search_text="*",
                filter=f"document_id eq '{document_id}'",
                select="id"  # Only select the ID for deletion
            )
        ]
    )

def delete_user_document_version(user_id, document_id, version):
    # Query to find the specific version of the document
    query = """
        SELECT c.id 
        FROM c 
        WHERE c.document_id = @document_id AND c.user_id = @user_id AND c.version = @version
    """
    parameters = [
        {"name": "@document_id", "value": document_id},
        {"name": "@user_id", "value": user_id},
        {"name": "@version", "value": version}
    ]
    documents = list(documents_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    # Delete the specific document version
    for doc in documents:
        documents_container.delete_item(doc['id'], partition_key=doc['user_id'])

def delete_user_document_version_chunks(document_id, version):
    # Use Azure AI Search to delete chunks for the specific document version
    search_client_user.delete_documents(
        actions=[
            {"@search.action": "delete", "id": chunk['id']} for chunk in 
            search_client_user.search(
                search_text="*",
                filter=f"document_id eq '{document_id}' and version eq {version}",
                select="id"  # Only select the ID for deletion
            )
        ]
    )
