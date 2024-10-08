from config import openai, document_intelligence_client, AZURE_OPENAI_EMBEDDING_MODEL, AnalyzeResult, AnalyzeOutputOption

#***************** Functions *****************
# The functions support content processing

def extract_text_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def extract_markdown_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def extract_content_with_azure_di(file_path):
    with open(file_path, "rb") as f:
        poller = document_intelligence_client.begin_analyze_document(
            model_id="prebuilt-layout",
            analyze_request=f,
            output=[AnalyzeOutputOption.FIGURES],
            content_type="application/octet-stream"
        )
    result: AnalyzeResult = poller.result()
    operation_id = poller.details["operation_id"]

    extracted_text = ""

    if result.paragraphs:
        paragraphs = sorted(result.paragraphs, key=lambda p: p.spans[0].offset)
        for paragraph in paragraphs:
            extracted_text += paragraph.content + "\n\n"
    else:
        for page in result.pages:
            for line in page.lines:
                extracted_text += line.content + "\n"
            extracted_text += "\n"

    if result.figures:
        figures_info = []
        for figure in result.figures:
            if figure.id:
                response = document_intelligence_client.get_analyze_result_figure(
                    model_id=result.model_id,
                    result_id=operation_id,
                    figure_id=figure.id
                )
                figure_filename = f"{figure.id}.png"
                with open(figure_filename, "wb") as writer:
                    writer.writelines(response)
                figures_info.append(figure_filename)

    return extracted_text

def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def generate_embedding(text):
    #print("Function generate_embedding called")
    #print(f"Text input for embedding: {text[:100]}...")  # Print the first 100 characters of the text to avoid excessive output

    try:
        # Make the call to OpenAI for embedding generation
        response = openai.Embedding.create(
            input=text,
            engine=AZURE_OPENAI_EMBEDDING_MODEL
        )
        #print("OpenAI API call successful")

        # Extract embedding from the response
        embedding = response['data'][0]['embedding']
        #print(f"Embedding generated successfully: Length {len(embedding)}")
        return embedding

    except Exception as e:
        #print(f"Error in generating embedding: {str(e)}")
        return None

