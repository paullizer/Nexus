# Nexus

**Nexus** is an AI-powered platform designed to streamline enterprise operations by providing intelligent workflows, document generation, and advanced search capabilities. The application leverages the power of **Cosmos DB** with vector search for personalized Retrieval-Augmented Generation (RAG) and **Azure AI Search** for group-based actions. 

Key Features:
- **RAG for Individuals & Groups**: Seamless integration with Cosmos DB for personalized document and data retrieval and Azure AI Search for team-based intelligence.
- **AI-Powered transform workflows**: Build repeatable workflows using AI to summarize, generate, or process documents by analyzing previous formats, structures, and disparate data sources.
- **Advanced Chat Capabilities**: Chat directly with AI models, including options for RAG-enhanced conversations or accessing live internet data.
- **Secure History & Logging**: Maintain detailed logs and history for analysis, security auditing, and optimization of top results.
- **Private & Group transform workflows**: Customize workflows for individual or team-based operations, ensuring adaptable and scalable solutions.

Nexus empowers enterprises to enhance productivity, ensure efficient information retrieval, and automate content creation while keeping data secure and auditable. Whether you're managing documents, summarizing data, or building complex workflows, **Nexus** provides the tools to streamline your processes with cutting-edge AI capabilities.


# Plans
Create APIs for user capabilities first

- [x] Create openapi yaml file to track API rollout [openapi.yaml](/artifacts/openapi.yaml)
- [x] private chat with model (including conversation history)
- [x] private chat with model, add file to chat
- [x] private chat with model, add internet search to chat
- [x] private chat with model , add one or more specific public websites to search to chat
- [x] private RAG (upload file, chunk file, embed chunk)
- [x] private chat with internet
- [ ] private transform with prompt
  - [x] list, create, update, and delete workflow
  - [x] execute workflow
  - [ ] get execution status
  - [ ] get execution result

- [ ] private transform with file to action
- [ ] private transform with internet search to action
- [ ] private transform with all of a specific document's chunks from AI search to action
- [ ] private transform with search user index to get X number of top chunks from AI search to action
- [ ] share conversation
- [ ] share workflow
- [ ] share action

Create APIs for group capabilities second

- [ ] group RAG (upload file, chunk file, embed chunk)
- [ ] manage user permissions to group (admin or user)
- [ ] manage access to group (public or private)
- [ ] manage access to private group
- [ ] using permissions to group, chat with group's RAG
- [ ] using permissions to group, transform with all of a specific document's chunks from AI search to action
  - [ ] users can add files from groups at their transform screen, this will be used to update APIs to reflect this access (if necessary, it may not require changes at the API layer and are just managed at the front end)
- [ ] using permissions to group, transform with search user index to get X number of top chunks from AI search to action
  - [ ] users can add files from groups at their transform screen, this will be used to update APIs to reflect this access (if necessary, it may not require changes at the API layer and are just managed at the front end)

Create front end for user capabilities

- [ ] more to come, writing down ideas.
- [ ] example workflows
- [ ] example actions

## Goals


- provide chat with the model
    - can share private conversation with anyone
    - can share group conversation with others in group (if public then anyone)
- provide inline chat rag for an individual
    - upload file to chat (when selecting file should have option for more than one source, but the only source now is local computer)
        - supports txt files, markdown files, word files (docx), and pdfs
        - only collects words from the files (for now)
    - when file is selected, file content at the chat level and added to conversation
    - file is not saved anywhere, only its contents are pulled out of the file and added to the chat
- provide many file rag for individuals aka private (cosmos db + vector)
    - can select individual file
    - can ask generically across all files
    - can delete existing file
    - cannot share file
    - cannot share entire source
- provide many file rag for groups (azure ai search)
    - can ask generally across all files owned by the group
    - can control access to the group rag (public or private with permissions)
    - can control who is a user (read only, cannot add new files) and who is a admin (can read and add new files and delete existing files)
    - cannot share individual file
- provide repeatable transform workflows (workflows) using AI to perform one or more actions using rag or just in time input from user; actions like summarize or generate a document using the format and structure of previous documents plus disparate data sources
    - need to think through this more, transform workflows can be shared but is access to transform workflow shared or the code to create a transform workflow shared?
    - transform workflow can be private
        - cannot share access to transform workflow
        - can share a copy of the transform workflow (JSON?)
        - can import other transform workflow copies
    - transform workflow can be group (public or private with permissions)
        - if add group RAG then permissions of transform workflow cannot exceed RAG permissions and only that group RAG can be used in the transform workflow
        - if public RAG is used then other public RAG can be used
        - can share a copy of the transform workflow (JSON?)
        - can import other transform workflow copies
    - transform workflow can use specific user documents
    - transform workflow can have one action or many actions
    - transform workflow next action can include previous action output or not
    - transform workflow can be a single action
- provide history, logging for security or for analysis on top requests



