
# ./Dockerfile
FROM python:3.9-slim as base

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base as rag
# RAG-specific installations if needed
# COPY RAG/extra_requirements.txt .
# RUN pip install -r extra_requirements.txt

FROM base as data
# Data service-specific installations

FROM base as llm
# LLM inference-specific installations