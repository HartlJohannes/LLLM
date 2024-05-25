import ollama
import weaviate
import weaviate.classes as wvc
from weaviate.classes.config import Property, DataType
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pymupdf
from pathlib import Path

THIS_DIR = Path(__file__).parent

# Initialize the ollama client
ollama_client = ollama.Client("https://7e28-188-241-30-201.ngrok-free.app/api")

# Initialize the weaviate client
client = weaviate.connect_to_embedded()

# collection
collection_name = "docs"

if client.collections.exists(collection_name):
    client.collections.delete(collection_name)

collection = client.collections.create(
    collection_name,
    properties=[
        Property(name="text", data_type=DataType.TEXT),
    ],
)


def chunk_doc(doc: str, max_len: int = 512) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_len,
        chunk_overlap=0,
        length_function=len,
        is_separator_regex=False,
    )
    return splitter.split_text(doc)


def ingest_chunks(chunks: list[str]):
    # store each document in a vector embedding database
    with collection.batch.dynamic() as batch:
        for i, d in enumerate(chunks):
            response = ollama_client.embeddings(model="all-minilm", prompt=d)
            embedding = response["embedding"]
            batch.add_object(
                properties={"text": d},
                vector=embedding,
            )
    collection.query.fetch_objects(limit=1, include_vector=True)


def query_docs(prompt: str) -> list[str]:
    response = ollama_client.embeddings(model="all-minilm", prompt=prompt)
    results = collection.query.near_vector(near_vector=response["embedding"], limit=5)
    return [result.properties['text'] for result in results.objects]


def process_pdf(doc: pymupdf.Document):
    """
    Extract text from a PDF document (also from images)

    :param doc: PDF document
    """
    for page in doc:
        #print(page.get_text())
        pass

    text = '\n\n'.join([page.get_text() for page in doc])
    ingest_chunks(chunk_doc(text))
    return text


async def ingest(file):
    """
    Ingest data from the database

    :param file: file to ingest
    """
    filepath = f'{THIS_DIR}/pdfs/{file.filename}'
    # save pdf
    with open(filepath, 'wb+') as f:
        f.write(await file.read())

    doc = pymupdf.open(filepath)
    process_pdf(doc)
