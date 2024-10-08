from config import jsonify, request, jsonify, documents_container, search_client_user
from process_content import generate_embedding
from process_document import get_user_documents, upload_user_document, get_user_documents, delete_user_document, delete_user_document_chunks, get_user_document, get_latest_version, delete_user_document_version, delete_user_document_version_chunks, get_user_document_version, hybrid_search

#***************** Documents *****************
# The documents routes handle the document management functionality

def register_route_document_user(app):
    @app.route('/api/documents', methods=['GET', 'POST'])
    def handle_documents():
        # Log the request method
        ##print(f"Request method: {request.method}")
        
        # Obtain user_id from the authentication context (either POST or GET)
        user_id = request.form.get('user_id') if request.method == 'POST' else request.args.get('user_id')
        ##print(f"User ID: {user_id}")

        if not user_id:
            ##print("Error: Missing user_id")
            return jsonify({'error': 'Missing user_id'}), 400

        if request.method == 'GET':
            # Handle GET request: Retrieve list of documents
            ##print("Handling GET request")
            return get_user_documents(user_id)  # Update to get latest versions
        elif request.method == 'POST':
            # Handle POST request: Upload a new document
            ##print("Handling POST request")
            return upload_user_document(user_id)



    @app.route('/api/documents/<document_id>', methods=['GET', 'DELETE'])
    def handle_specific_document(document_id):
        # Log the request method and document ID
        ##print(f"Request method: {request.method}")
        ##print(f"Document ID: {document_id}")

        # Obtain user_id from authentication context or request
        user_id = request.form.get('user_id') if request.method == 'DELETE' else request.args.get('user_id')
        ##print(f"User ID: {user_id}")

        if not user_id:
            ##print("Error: Missing user_id")
            return jsonify({'error': 'Missing user_id'}), 400

        if request.method == 'GET':
            # Handle GET request: Retrieve a specific document
            ##print(f"Handling GET request for document ID: {document_id}")
            return get_user_document(user_id, document_id)
        
        elif request.method == 'DELETE':
            # Handle DELETE request: Delete all versions of the document
            ##print(f"Handling DELETE request for document ID: {document_id}")
            try:
                # Step 1: Delete document metadata from Cosmos DB
                ##print(f"Deleting document metadata for document ID: {document_id}")
                delete_user_document(user_id, document_id)

                # Step 2: Delete all associated chunks from Azure AI Search
                ##print(f"Deleting document chunks for document ID: {document_id}")
                delete_user_document_chunks(document_id)

                ##print(f"Document ID {document_id} and all versions deleted successfully")
                return jsonify({'message': 'Document and all versions deleted successfully'}), 200

            except Exception as e:
                ##print(f"Error deleting document ID {document_id}: {str(e)}")
                return jsonify({'error': f'Error deleting document: {str(e)}'}), 500


    @app.route('/api/documents/<document_id>/versions', methods=['GET'])
    def get_document_versions(document_id):
        user_id = request.args.get('user_id')

        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400

        try:
            # Query to retrieve all versions of the document for the user
            query = """
                SELECT c.id, c.file_name, c.version, c.upload_date
                FROM c 
                WHERE c.id = @document_id AND c.user_id = @user_id
                ORDER BY c.version DESC
            """
            parameters = [
                {"name": "@document_id", "value": document_id},
                {"name": "@user_id", "value": user_id}
            ]

            versions_results = list(documents_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

            if not versions_results:
                return jsonify({'error': 'No versions found for this document'}), 404

            return jsonify({"versions": versions_results}), 200

        except Exception as e:
            return jsonify({'error': f'Error retrieving document versions: {str(e)}'}), 500

    @app.route('/api/documents/<document_id>/version/<version>', methods=['GET', 'DELETE'])
    def delete_document_version(document_id, version):
        user_id = request.args.get('user_id')

        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400

        if request.method == 'GET':
            # Handle GET request: Retrieve a specific version of the document
            return get_user_document_version(user_id, document_id, version)
        
        elif request.method == 'DELETE':
            try:
                # Step 1: Delete the specific version from Cosmos DB
                delete_user_document_version(user_id, document_id, version)

                # Step 2: Delete associated chunks for that version from Azure AI Search
                delete_user_document_version_chunks(document_id, version)

                return jsonify({'message': 'Document version and its associated chunks deleted successfully'}), 200

            except Exception as e:
                return jsonify({'error': f'Error deleting document version: {str(e)}'}), 500
        
    @app.route('/api/documents/<document_id>/chunks', methods=['GET'])
    def get_document_chunks(document_id):
        ##print(f"Function get_document_chunks called for document_id: {document_id}")

        # Retrieve user_id from query parameters
        user_id = request.args.get('user_id')
        ##print(f"User ID: {user_id}")

        if not user_id:
            ##print("Error: Missing user_id")
            return jsonify({'error': 'Missing user_id'}), 400

        try:
            # Step 1: Get the latest version for the specified document and user
            latest_version = get_latest_version(document_id, user_id)
            ##print(f"Latest version for document_id {document_id} and user_id {user_id}: {latest_version}")

            if latest_version is None:
                ##print("No chunks found for the specified document and user")
                return jsonify({'error': 'No chunks found for the specified document and user'}), 404

            # Step 2: Search for chunks matching document_id, user_id, and latest version
            ##print(f"Searching for chunks with document_id: {document_id}, user_id: {user_id}, version: {latest_version}")
            search_results = search_client_user.search(
                search_text="*",
                filter=f"document_id eq '{document_id}' and user_id eq '{user_id}' and version eq {latest_version}",
                top=100,
                select="id, chunk_text, chunk_id, version"
            )

            # Collect the chunks into a list
            chunks = []
            for result in search_results:
                chunk_info = {
                    "id": result['id'],
                    "chunk_text": result['chunk_text'],
                    "chunk_id": result['chunk_id'],
                    "version": result['version']  # Include version in the response
                }
                ##print(f"Found chunk: {chunk_info}")
                chunks.append(chunk_info)

            ##print(f"Total chunks found: {len(chunks)}")
            return jsonify({"chunks": chunks}), 200

        except Exception as e:
            ##print(f"Error retrieving chunks: {str(e)}")
            return jsonify({'error': f'Error retrieving chunks: {str(e)}'}), 500


    @app.route('/api/documents/<document_id>/version/<version>/chunks', methods=['GET'])
    def get_chunks_of_specific_version(document_id, version):
        user_id = request.args.get('user_id')

        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400

        try:
            # Step 1: Search for chunks that match the document_id, user_id, and specified version
            search_results = search_client_user.search(
                search_text="*",
                filter=f"document_id eq '{document_id}' and user_id eq '{user_id}' and version eq {version}",
                top=100,
                select="id, chunk_text, chunk_id, version"
            )

            # Collect the chunks into a list
            chunks = []
            for result in search_results:
                chunks.append({
                    "id": result['id'],
                    "chunk_text": result['chunk_text'],
                    "chunk_id": result['chunk_id'],
                    "version": result['version']  # Include version in the response
                })

            if not chunks:
                return jsonify({'error': 'No chunks found for the specified document version'}), 404

            return jsonify({"chunks": chunks}), 200

        except Exception as e:
            return jsonify({'error': f'Error retrieving chunks: {str(e)}'}), 500


    @app.route('/api/documents/search', methods=['POST'])
    def search_document_chunks():
        ##print("Function search_document_chunks called")

        # Get data from the request
        data = request.get_json()
        user_id = data.get('user_id')
        search_query = data.get('query')
        top_n = data.get('top_n', 5)  # Default to returning top 5 results if not specified

        ##print(f"user_id: {user_id}, search_query: {search_query}, top_n: {top_n}")

        if not user_id or not search_query:
            ##print("Error: Missing user_id or query")
            return jsonify({'error': 'Missing user_id or query'}), 400

        try:
            ##print(f"Searching for top {top_n} chunks for user_id: {user_id}")
            results = hybrid_search(search_query, user_id, top_n)

            # Step 3: Prepare the response with the top chunks
            top_chunks = []
            ##print(f"Results found are result: {results}")

            for result in results:
                ##print(f"Result: {result}")
                
                chunk_info = {
                    "chunk_id": result["chunk_id"],
                    "chunk_text": result["chunk_text"],
                    "similarity_score": result["@search.score"],  # Similarity score returned by Azure Cognitive Search
                    "metadata": {
                        "file_name": result["file_name"],
                        "user_id": result["user_id"],
                        "chunk_sequence": result["chunk_sequence"],
                        "upload_date": result["upload_date"],
                        "version": result["version"]
                    }
                }
                ##print(f"Found chunk: {chunk_info}")
                top_chunks.append(chunk_info)

            ##print(f"Total chunks found: {len(top_chunks)}")

            # Step 4: Return the top N chunks
            response_data = {
                "query": search_query,
                "top_chunks": top_chunks
            }

            return jsonify(response_data), 200

        except Exception as e:
            ##print(f"Error during search: {str(e)}")
            return jsonify({'error': f'Error during search: {str(e)}'}), 500


