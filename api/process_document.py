from config import openai, documents_container, jsonify, request, secure_filename, os, tempfile, json, uuid, datetime, timezone, search_client_user, VectorizedQuery
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
    #print("Function upload_user_document called")
    
    # Get the file from the request
    file = request.files.get('file')
    #print(f"File received from request: {file}")

    if not file:
        #print("No file uploaded")
        return jsonify({'error': 'No file uploaded'}), 400

    # Secure the filename and get the file extension
    filename = secure_filename(file.filename)
    #print(f"Secure filename: {filename}")
    file_ext = os.path.splitext(filename)[1].lower()
    #print(f"File extension: {file_ext}")

    # Save the file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        file.save(tmp_file.name)
        temp_file_path = tmp_file.name
    #print(f"Temporary file path: {temp_file_path}")

    extracted_text = ''

    try:
        # Use existing extraction functions
        if file_ext in ['.pdf', '.docx', '.xlsx', '.pptx', '.html',
                        '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.heif']:
            #print("Extracting content using Azure DI")
            extracted_text = extract_content_with_azure_di(temp_file_path)
        elif file_ext == '.txt':
            #print("Extracting text from .txt file")
            extracted_text = extract_text_file(temp_file_path)
        elif file_ext == '.md':
            #print("Extracting text from .md file")
            extracted_text = extract_markdown_file(temp_file_path)
        elif file_ext == '.json':
            #print("Processing JSON file")
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                parsed_json = json.load(f)
                extracted_text = json.dumps(parsed_json)
        else:
            #print("Unsupported file type")
            return jsonify({'error': 'Unsupported file type'}), 400

        # Process the extracted text and store chunks in 'documents' container
        #print(f"Processing and storing extracted text for file: {filename}")
        process_document_and_store_chunks(extracted_text, filename, user_id)

    except Exception as e:
        #print(f"Error processing file: {str(e)}")
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    finally:
        # Ensure the temp file is removed
        #print(f"Removing temporary file: {temp_file_path}")
        os.remove(temp_file_path)

    response_data = {
        'message': 'Document uploaded and processed successfully',
        'file_name': filename
    }

    #print(f"Response data: {response_data}")
    return jsonify(response_data), 200


def process_document_and_store_chunks(extracted_text, file_name, user_id):
    #print("Function process_document_and_store_chunks called")
    document_id = str(uuid.uuid4())  # Unique ID for the document
    #print(f"Generated document ID: {document_id}")
    
    # Chunk the extracted text
    chunks = chunk_text(extracted_text)
    #print(f"Total chunks created: {len(chunks)}")

    # Check if there's an existing version of this document
    existing_document_query = """
        SELECT c.version 
        FROM c 
        WHERE c.file_name = @file_name AND c.user_id = @user_id
    """
    parameters = [{"name": "@file_name", "value": file_name}, {"name": "@user_id", "value": user_id}]
    #print(f"Querying existing document with parameters: {parameters}")
    
    existing_document = list(documents_container.query_items(query=existing_document_query, parameters=parameters, enable_cross_partition_query=True))
    #print(f"Existing document found: {existing_document}")

    # Determine the new version number
    if existing_document:
        version = existing_document[0]['version'] + 1
        #print(f"New version determined: {version} (existing document found)")
    else:
        version = 1
        #print(f"New version determined: {version} (no existing document)")

    # Get the current time in UTC
    current_time = datetime.now(timezone.utc)

    # Format it to the desired string format
    formatted_time = current_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Store document metadata
    document_metadata = {
        "id": document_id,
        "file_name": file_name,
        "user_id": user_id,
        "upload_date": formatted_time,
        "version": version,
        "type": "document_metadata"
    }
    #print(f"Document metadata to be upserted: {document_metadata}")
    documents_container.upsert_item(document_metadata)

    chunk_documents = []
    
    # Process each chunk
    for idx, chunk_text_content in enumerate(chunks):
        chunk_id = f"{document_id}_{idx}"  # Create a unique chunk ID
        #print(f"Processing chunk {idx} with ID: {chunk_id}")

        # Generate embedding
        embedding = generate_embedding(chunk_text_content)
        #print(f"Generated embedding for chunk {idx}")

        # Create chunk document with versioning
        chunk_document = {
            "id": chunk_id,
            "document_id": document_id,
            "chunk_id": str(idx),
            "chunk_text": chunk_text_content,
            "embedding": embedding,
            "file_name": file_name,
            "user_id": user_id,
            "chunk_sequence": idx,
            "upload_date": formatted_time,
            "version": version
        }
        #print(f"Chunk document created for chunk {idx}: {chunk_document}")
        chunk_documents.append(chunk_document)

    # Upload the chunk documents to Azure Cognitive Search
    #print(f"Uploading {len(chunk_documents)} chunk documents to Azure Cognitive Search")
    search_client_user.upload_documents(documents=chunk_documents)
    #print("Chunks uploaded successfully")

def get_user_document(user_id, document_id):
    #print(f"Function get_user_document called for user_id: {user_id}, document_id: {document_id}")

    try:
        # Query to retrieve the latest version of the document
        latest_version_query = """
            SELECT TOP 1 *
            FROM c 
            WHERE c.id = @document_id AND c.user_id = @user_id
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@user_id", "value": user_id}
        ]
        #print(f"Query parameters: {parameters}")

        # Execute the query to fetch the document
        document_results = list(documents_container.query_items(
            query=latest_version_query, 
            parameters=parameters, 
            enable_cross_partition_query=True
        ))

        #print(f"Query executed, document_results: {document_results}")

        if not document_results:
            #print("Document not found or access denied")
            return jsonify({'error': 'Document not found or access denied'}), 404

        #print(f"Returning latest version of document: {document_results[0]}")
        return jsonify(document_results[0]), 200  # Return the latest version of the document

    except Exception as e:
        #print(f"Error retrieving document: {str(e)}")
        return jsonify({'error': f'Error retrieving document: {str(e)}'}), 500


def get_latest_version(document_id, user_id):
    #print(f"Function get_latest_version called for document_id: {document_id}, user_id: {user_id}")

    # Query to retrieve all versions of the document
    query = """
        SELECT c.version
        FROM c 
        WHERE c.id = @document_id AND c.user_id = @user_id
    """
    parameters = [
        {"name": "@document_id", "value": document_id},
        {"name": "@user_id", "value": user_id}
    ]
    #print(f"Query parameters: {parameters}")

    try:
        # Execute the query
        results = list(documents_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
        #print(f"Query results: {results}")

        # Determine the maximum version from the retrieved results
        if results:
            max_version = max(item['version'] for item in results)
            #print(f"Latest version found: {max_version}")
            return max_version
        else:
            #print("No version found for the document.")
            return None

    except Exception as e:
        #print(f"Error retrieving latest version: {str(e)}")
        return None



def get_user_document_version(user_id, document_id, version):
    try:
        # Query to retrieve the specific version of the document
        query = """
            SELECT *
            FROM c 
            WHERE c.id = @document_id AND c.user_id = @user_id AND c.version = @version
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
        WHERE c.id = @document_id AND c.user_id = @user_id
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
        WHERE c.id = @document_id AND c.user_id = @user_id AND c.version = @version
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

def hybrid_search(query, user_id, top_n=3):
    #print(f"Function hybrid_search called with query: '{query}', user_id: '{user_id}', top_n: {top_n}")

    try:
        # Step 1: Generate the query embedding
        #print(f"Generating embedding for the query: '{query}'")
        query_embedding = generate_embedding(query)

        if query_embedding is None:
            #print("Error: Failed to generate embedding for the query")
            return None

        #print(f"Query embedding generated: {query_embedding[:5]}...")  # Print the first few values for debugging

        # Step 2: Create a vectorized query
        vector_query = VectorizedQuery(vector=query_embedding, k_nearest_neighbors=top_n, fields="embedding")
        #print(f"Vectorized query created: {vector_query}")

        # Step 3: Perform the hybrid search
        #print(f"Performing hybrid search for user_id: '{user_id}' with top {top_n} results")
        results = search_client_user.search(
            search_text=query,
            vector_queries=[vector_query],
            filter=f"user_id eq '{user_id}'",
            select=["id", "chunk_text", "chunk_id", "file_name", "user_id", "version", "chunk_sequence", "upload_date"]
        )
        
        return results

    except Exception as e:
        #print(f"Error during hybrid search: {str(e)}")
        return None

