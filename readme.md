# CMU Advanced NLP Assignment 2: End-to-end NLP System Building

Work done by Gefei Gu, Yi Lu and Yi Dai. We build an end-to-end retrieval-augmented generation system for factual question answering about Pittsburgh and Carnegie Mellon University. 

The core implementation of our rag system is in `simple_rag.py`, where we implement a rag class with sparse/dense/hybrid search method. 

`eval_on_private.py` is how we evaluate our system on the dataset we built, `eval_on_unseen.py`is how to infer on the unseen test set and `eval_wo_rag.py` is how we evaluate our system without using rag.

`run.sh` is a bash script we run the experiment on a slurm cluster. 
