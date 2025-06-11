from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os

# The LaTeX text
latex_text = """
    \documentclass{article}
    
    \begin{document}
    
    \maketitle
    
    \section{Introduction}
    Large language models (LLMs) are a type of machine learning model that can be trained on vast amounts of text data to generate human-like language. In recent years, LLMs have made significant advances in a variety of natural language processing tasks, including language translation, text generation, and sentiment analysis.
    
    \subsection{History of LLMs}
    The earliest LLMs were developed in the 1980s and 1990s, but they were limited by the amount of data that could be processed and the computational power available at the time. In the past decade, however, advances in hardware and software have made it possible to train LLMs on massive datasets, leading to significant improvements in performance.
    
    \subsection{Applications of LLMs}
    LLMs have many applications in industry, including chatbots, content creation, and virtual assistants. They can also be used in academia for research in linguistics, psychology, and computational linguistics.
    
    \end{document}
"""

# Create a text splitter with specific chunk size and overlap
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,  # Number of characters per chunk
    chunk_overlap=50,  # Number of characters to overlap between chunks
    length_function=len,
    separators=["\n\n", "\n", " ", ""]  # Split on these separators in order
)

# Split the text
chunks = text_splitter.split_text(latex_text)

# Create embeddings and vector store
embeddings = OpenAIEmbeddings()
vectordb = FAISS.from_texts(chunks, embeddings)

# Create retriever with search_kwargs to get top 2 results
retriever = vectordb.as_retriever(
    search_kwargs={"k": 2}  # This will return top 2 results
)

# Example query
query = "email policy"

# Retrieve top 2 results
docs = retriever.invoke(query)

# Print the results
print("\nTop 2 Results for query:", query)
print("-" * 50)
for i, doc in enumerate(docs, 1):
    print(f"\nResult {i}:")
    print("-" * 30)
    print(doc.page_content)
    print("-" * 30) 