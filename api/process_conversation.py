from config import openai, conversations_container, exceptions, datetime

#***************** Functions *****************
# The functions support conversation management

def get_conversation_history(conversation_id, user_id):
    try:
        # Retrieve the conversation document using the conversation_id
        conversation_doc = conversations_container.read_item(
            item=conversation_id,
            partition_key=conversation_id  # Partition key is conversation_id
        )
        
        # Verify that the user_id matches
        if conversation_doc['user_id'] != user_id:
            print(f"Unauthorized access attempt by user {user_id} on conversation {conversation_id}")
            return None  # Or raise an exception
        
        return conversation_doc
    except exceptions.CosmosResourceNotFoundError:
        return None
    except Exception as e:
        print(f"Error retrieving conversation history: {str(e)}")
        return None


def list_conversations(user_id):
    try:
        # Query to fetch all conversations with the last message for the given user_id
        query = """
            SELECT c.id, c.created_at, c.updated_at, 
            ARRAY_SLICE(c.thread, -1)[0] AS last_message
            FROM c WHERE c.user_id = @user_id
        """
        parameters = [
            {"name": "@user_id", "value": user_id}
        ]
        
        # Perform the query on the container
        items = list(conversations_container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        
        return items
    except Exception as e:
        print(f"Error fetching conversations: {str(e)}")
        return []

def update_conversation_thread(conversation_id, user_id, user_message, assistant_reply):
    try:
        # Try to retrieve the conversation document
        conversation_doc = conversations_container.read_item(
            item=conversation_id,
            partition_key=conversation_id
        )
        
        # Verify that the user_id matches
        if conversation_doc['user_id'] != user_id:
            print(f"Unauthorized update attempt by user {user_id} on conversation {conversation_id}")
            raise Exception("Unauthorized access")
        
        # Append the new user message and assistant reply to the conversation thread
        conversation_doc['thread'].append({
            "user_message": user_message,
            "assistant_reply": assistant_reply,
            "timestamp": datetime.utcnow().isoformat()
        })
        conversation_doc['updated_at'] = datetime.utcnow().isoformat()
        
        # Upsert the document in Cosmos DB with the updated thread
        conversations_container.upsert_item(conversation_doc)

    except exceptions.CosmosResourceNotFoundError:
        # If the document doesn't exist, create a new one
        conversation_doc = {
            "id": conversation_id,
            "user_id": user_id,
            "thread": [{
                "user_message": user_message,
                "assistant_reply": assistant_reply,
                "timestamp": datetime.utcnow().isoformat()
            }],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        # Upsert the new document in Cosmos DB
        conversations_container.upsert_item(conversation_doc)

    except Exception as e:
        print(f"Error updating conversation thread: {str(e)}")

def delete_conversation_thread(conversation_id, user_id):
    try:
        # Retrieve the conversation document
        conversation_doc = conversations_container.read_item(
            item=conversation_id,
            partition_key=conversation_id
        )

        # Verify that the user_id matches
        if conversation_doc['user_id'] != user_id:
            print(f"Unauthorized delete attempt by user {user_id} on conversation {conversation_id}")
            raise Exception("Unauthorized access")

        # Delete the conversation document
        conversations_container.delete_item(
            item=conversation_id,
            partition_key=conversation_id
        )

        return True

    except exceptions.CosmosResourceNotFoundError:
        print(f"Conversation {conversation_id} not found")
        return False
    except Exception as e:
        print(f"Error deleting conversation: {str(e)}")
        raise e

def add_system_message_to_conversation(conversation_id, user_id, content):
    try:
        # Retrieve the conversation document
        conversation_doc = conversations_container.read_item(
            item=conversation_id,
            partition_key=conversation_id
        )

        # Verify that the user_id matches
        if conversation_doc['user_id'] != user_id:
            print(f"Unauthorized access attempt by user {user_id} on conversation {conversation_id}")
            raise Exception("Unauthorized access")

        # Append the system message
        conversation_doc['thread'].append({
            "role": "system",
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        conversation_doc['updated_at'] = datetime.utcnow().isoformat()

        # Upsert the document
        conversations_container.upsert_item(conversation_doc)

    except exceptions.CosmosResourceNotFoundError:
        # Conversation doesn't exist
        print(f"Conversation {conversation_id} not found")
        raise Exception("Conversation not found")
    except Exception as e:
        print(f"Error adding system message to conversation: {str(e)}")
        raise e