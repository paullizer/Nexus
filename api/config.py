import os
import requests
from datetime import datetime
from flask import Flask, redirect, jsonify, render_template, request, send_from_directory, url_for, flash, session
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import openai
from azure.cosmos import CosmosClient, exceptions
import tempfile
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, AnalyzeOutputOption
import markdown
import json

#***************** Environment Variables *****************
# This file supports all configuration for the application; 
# module imports, environment variables, and client initialization

AZURE_OPENAI_API_TYPE = os.environ.get("AZURE_OPENAI_API_TYPE")
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_LLM_MODEL = os.environ.get("AZURE_OPENAI_LLM_MODEL")
AZURE_OPENAI_EMBEDDING_MODEL = os.environ.get("AZURE_OPENAI_EMBEDDING_MODEL")

AZURE_COSMOS_ENDPOINT = os.environ.get("AZURE_COSMOS_ENDPOINT")
AZURE_COSMOS_KEY = os.environ.get("AZURE_COSMOS_KEY")
AZURE_COSMOS_DB_NAME = os.environ.get("AZURE_COSMOS_DB_NAME")
AZURE_COSMOS_CONVERSATIONS_CONTAINER_NAME = os.environ.get('AZURE_COSMOS_CONVERSTATIONS_CONTAINER_NAME')
AZURE_COSMOS_DOCUMENTS_CONTAINER_NAME = os.environ.get('AZURE_COSMOS_DOCUMENTS_CONTAINER_NAME')

AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
AZURE_DOCUMENT_INTELLIGENCE_KEY = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")

#***************** Clients *****************

openai.api_type = AZURE_OPENAI_API_TYPE
openai.api_base = AZURE_OPENAI_ENDPOINT
openai.api_version = AZURE_OPENAI_API_VERSION
openai.api_key = AZURE_OPENAI_KEY

cosmos_client = CosmosClient(AZURE_COSMOS_ENDPOINT, AZURE_COSMOS_KEY)
database = cosmos_client.get_database_client(AZURE_COSMOS_DB_NAME)
conversations_container = database.get_container_client(AZURE_COSMOS_CONVERSATIONS_CONTAINER_NAME)
documents_container = database.get_container_client(AZURE_COSMOS_DOCUMENTS_CONTAINER_NAME)

document_intelligence_client = DocumentIntelligenceClient(
    endpoint=AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
    credential=AzureKeyCredential(AZURE_DOCUMENT_INTELLIGENCE_KEY)
)