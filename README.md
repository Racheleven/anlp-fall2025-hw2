# CMU Advanced NLP — Assignment 2: End-to-End NLP System Building

**Group Members:** Gefei Gu, Yi Lu, and Yi Dai  

We build an **end-to-end Retrieval-Augmented Generation (RAG) system** for factual question answering about **Pittsburgh** and **Carnegie Mellon University**.

## Project Overview
Our pipeline consists of data collection, document chunking, retrieval, generation, and evaluation. The system integrates both **sparse** and **dense** retrieval methods and supports **hybrid search** for improved performance.

## Data
- Raw scraped documents are stored in `/data/`.  
- Preprocessed and chunked documents are in `/crawl_chunks/`.  
- We provide five chunking strategies:  
  **hybrid**, **markdown**, **naive**, **paragraph**, and **sentence**.  
  Detailed descriptions of these strategies are available in our paper.  
  The implementation can be found in `chunk.py`.

## System Implementation
- The core RAG implementation is in **`simple_rag.py`**, which defines the main RAG class and supports **sparse**, **dense**, and **hybrid** retrieval.  
- Evaluation scripts:  
  - `eval_on_private.py`: evaluate the system on our internal test set.  
  - `eval_on_unseen.py`: run inference on the unseen test set.  
  - `eval_wo_rag.py`: evaluate performance without using RAG (baseline).

## Experiment Setup
- **`run.sh`** contains the bash commands used to run all experiments on a **Slurm cluster**.
