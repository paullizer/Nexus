# Nexus: AI-Powered Enterprise Workflow and Document Generation

**Nexus** is an AI-powered platform designed to streamline enterprise operations by providing intelligent workflows, document generation, and advanced search capabilities. The application leverages the power of **Cosmos DB** with vector search for personalized Retrieval-Augmented Generation (RAG) and **Azure AI Search** for group-based tasks. 

Key Features:
- **RAG for Individuals & Groups**: Seamless integration with Cosmos DB for personalized document and data retrieval and Azure AI Search for team-based intelligence.
- **AI-Powered Pipelines**: Build repeatable workflows using AI to summarize, generate, or process documents by analyzing previous formats, structures, and disparate data sources.
- **Advanced Chat Capabilities**: Chat directly with AI models, including options for RAG-enhanced conversations or accessing live internet data.
- **Secure History & Logging**: Maintain detailed logs and history for analysis, security auditing, and optimization of top results.
- **Private & Group Pipelines**: Customize workflows for individual or team-based operations, ensuring adaptable and scalable solutions.

Nexus empowers enterprises to enhance productivity, ensure efficient information retrieval, and automate content creation while keeping data secure and auditable. Whether you're managing documents, summarizing data, or building complex workflows, **Nexus** provides the tools to streamline your processes with cutting-edge AI capabilities.


# Plans
Create APIs for user capabilities first

- [x] Create openapi yaml file to track API rollout [openapi.yaml](..\artifacts\openapi.yaml)
- [x] private chat with model (including conversation history)
- [x] private chat with model add file to chat
- [x] private chat with model add internet search to chat
- [x] private RAG (upload file, chunk file, embed chunk)
- [x] private chat with internet
- [ ] private pipeline
- [ ] share conversation
- [ ] share pipeline

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
- provide repeatable pipelines (workflows) using AI to perform one or more tasks using rag or just in time input from user; tasks like summarize or generate a document using the format and structure of previous documents plus disparate data sources
    - need to think through this more, pipelines can be shared but is access to pipeline shared or the code to create a pipeline shared?
    - pipeline can be private
        - cannot share access to pipeline
        - can share a copy of the pipeline (JSON?)
        - can import other pipeline copies
    - pipeline can be group (public or private with permissions)
        - if add group RAG then permissions of pipeline cannot exceed RAG permissions and only that group RAG can be used in the pipeline
        - if public RAG is used then other public RAG can be used
        - can share a copy of the pipeline (JSON?)
        - can import other pipeline copies
    - pipeline can use specific files or entire private or group source
    - pipeline can have one task or many tasks
    - pipeline next task can include previous task output or not
    - pipeline can be a single task
- provide history, logging for security or for analysis on top requests



