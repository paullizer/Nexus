from config import jsonify, request, jsonify, documents_container, search_client_user
from process_content import generate_embedding
from process_document import get_user_documents, upload_user_document, get_user_documents, delete_user_document, delete_user_document_chunks, get_user_document, get_latest_version, delete_user_document_version, delete_user_document_version_chunks, get_user_document_version

#***************** Documents *****************
# The documents routes handle the document management functionality

def register_route_document_user(app):
    @app.route('/api/documents', methods=['GET', 'POST'])
    def handle_documents():
        # Obtain user_id from authentication context
        user_id = request.form.get('user_id') if request.method == 'POST' else request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400

        if request.method == 'GET':
            # Handle GET request: Retrieve list of documents
            return get_user_documents(user_id)  # Update to get latest versions
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
            # Delete all versions of the document
            try:
                # Step 1: Delete document metadata from Cosmos DB
                delete_user_document(user_id, document_id)

                # Step 2: Delete all associated chunks from Azure AI Search
                delete_user_document_chunks(document_id)

                return jsonify({'message': 'Document and all versions deleted successfully'}), 200

            except Exception as e:
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
                WHERE c.document_id = @document_id AND c.user_id = @user_id
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
        user_id = request.args.get('user_id')

        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400

        try:
            # Step 1: Get the latest version for the specified document and user
            latest_version = get_latest_version(document_id, user_id)

            if latest_version is None:
                return jsonify({'error': 'No chunks found for the specified document and user'}), 404

            # Step 2: Search for chunks that match the document_id, user_id, and latest version
            search_results = search_client_user.search(
                search_text="*",
                filter=f"document_id eq '{document_id}' and user_id eq '{user_id}' and version eq {latest_version}",
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

            return jsonify({"chunks": chunks}), 200

        except Exception as e:
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
        data = request.get_json()
        user_id = data.get('user_id')
        search_query = data.get('query')
        top_n = data.get('top_n', 5)  # Default to returning top 5 results if not specified

        if not user_id or not search_query:
            return jsonify({'error': 'Missing user_id or query'}), 400

        try:
            # Step 1: Get the embedding for the search query using the same embedding model
            query_embedding = generate_embedding(search_query)

            if query_embedding is None:
                return jsonify({'error': 'Failed to generate embedding for the query'}), 500

            # Step 2: Query Azure Cognitive Search for the top N chunks
            results = search_client_user.search(
                search_text="",  # No need for a textual search if we're doing embedding-based search
                vector=query_embedding,
                vector_fields="embedding",  # The field where we store chunk embeddings
                top=top_n,
                filter=f"user_id eq '{user_id}'"  # Filter by user_id to ensure users only see their own chunks
            )

            # Step 3: Prepare the response with top chunks
            top_chunks = []
            for result in results:
                top_chunks.append({
                    "chunk_id": result["chunk_id"],
                    "chunk_text": result["chunk_text"],
                    "similarity_score": result["@search.score"],  # Similarity score returned by Azure Cognitive Search
                    "metadata": {
                        "file_name": result["file_name"],
                        "user_id": result["user_id"],
                        "chunk_sequence": result["chunk_sequence"],
                        "upload_date": result["upload_date"]
                    }
                })

            # Step 4: Return the top N chunks
            response_data = {
                "query": search_query,
                "top_chunks": top_chunks
            }

            return jsonify(response_data), 200

        except Exception as e:
            return jsonify({'error': f'Error during search: {str(e)}'}), 500

