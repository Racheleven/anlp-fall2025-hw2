# CMU Advanced NLP Assignment 2: End-to-end NLP System Building

Large language models (LLMs) such as Llama2 have been shown effective for question-answering ([Touvron et al., 2023](https://arxiv.org/abs/2307.09288)), however, they are often limited by their knowledge in certain domains. A common technique here is to augment LLM's knowledge with documents that are relevant to the question. In this assignment, you will *develop a retrieval augmented generation system (RAG)* ([Lewis et al., 2021](https://arxiv.org/abs/2005.11401)) that's capable of answering questions about Pittsburgh and CMU, including history, culture, trivia, and upcoming events.

```
Q: Who is Pittsburgh named after? 
A: William Pitt

Q: What famous machine learning venue had its first conference in Pittsburgh in 1980? 
A: ICML

Q: What musical artist is performing at PPG Arena on October 13? 
A: Billie Eilish
```

So far in your machine learning classes, you may have experimented with standardized tasks and datasets that were easily accessible. However, in the real world, NLP practitioners often have to solve a problem from scratch (like this one!). This includes gathering and cleaning data, annotating your data, choosing a model, iterating on the model, and possibly going back to change your data. In this assignment, you'll get to experience this full process.

Please note that you'll be building your own system end-to-end for this assignment, and **there is no starter code**. You must collect your own data and develop a model of your choice on the data. We will be releasing the inputs for the test set a few days before the assignment deadline, and you will run your already-constructed system over this data and submit the results. We also ask you to follow several experimental best practices, and describe the result in your report.

The key checkpoints for this assignment are:

- [ ] [Understand the task specification](#task-retrieval-augmented-generation-rag)
- [ ] [Prepare your raw data](#preparing-raw-data)
- [ ] [Annotate data for model development](#annotating-data)
- [ ] [Develop a retrieval augmented generation system with retrieval components](#developing-your-rag-system)
- [ ] [Generating results](#generating-results)
- [ ] [Write a report](#writing-report)
- [ ] [Submit your work](#submission--grading)

All deliverables are due by **Thursday, October 9th**. This is a group assignment, see the assignment policies for this class.[^1]

## Task: Retrieval Augmented Generation (RAG)

You'll be working on the task of factual question-answering (QA). We will focus specifically on questions about various facts concerning Pittsburgh and CMU. Since existing QA systems might not have the necessary knowledge in this domain, you will need to augment each question with relevant documents. Given an input question, your system will first retrieve documents and use those documents to generate an answer.

## Preparing raw data

### Compiling a knowledge resource

For your test set and the RAG systems, you will first need to compile a knowledge resource of relevant documents. You are free to use any publicly available resource, but we highly recommend including the websites below. Note that we can also ask you questions from relevant subpages (e.g. "about", "schedule", "history", "upcoming events", "vendors", etc.) from these websites:

**General Info and History of Pittsburgh/CMU**
- Wikipedia pages ([Pittsburgh](https://en.wikipedia.org/wiki/Pittsburgh), [History of Pittsburgh](https://en.wikipedia.org/wiki/History_of_Pittsburgh)).
- [City of Pittsburgh webpage](https://www.pittsburghpa.gov/Home)
- [Encyclopedia Brittanica page](https://www.britannica.com/place/Pittsburgh)
- [Visit Pittsburgh webpage](https://www.visitpittsburgh.com): This website also contains subpages that would be useful for other topics (see below), like events, sports, music, food, etc.
- City of Pittsburgh [Tax Regulations](https://pittsburghpa.gov/finance/tax-forms): See the links under the "Regulations" column of the table
- City of Pittsburgh [2025 Operating Budget]([https://apps.pittsburghpa.gov/redtail/images/23255_2024_Operating_Budget.pdf](https://www.pittsburghpa.gov/files/assets/city/v/4/omb/documents/operating-budgets/2025-operating-budget.pdf))
- [About CMU & CMU History](https://www.cmu.edu/about/)

**Events in Pittsburgh and CMU** (We will only ask about annual/recurring events and events happening after October 9th until the end of 2025.)
- [Pittsburgh events calendar](https://pittsburgh.events): Navigate to month-specific pages for easier scraping
- [Downtown Pittsburgh events calendar](https://downtownpittsburgh.com/events/)
- [Pittsburgh City Paper events](https://www.pghcitypaper.com/pittsburgh/EventSearch?v=d)
- [CMU events calendar](https://events.cmu.edu) and [campus events page](https://www.cmu.edu/engage/alumni/events/campus/index.html)

**Music and Culture** (Note that many of these pages also contain upcoming events, also see Wikipedia pages for each.)
- Pittsburgh [Symphony](https://www.pittsburghsymphony.org), [Opera](https://pittsburghopera.org), and [Cultural Trust](https://trustarts.org)
- Pittsburgh Museums ([Carnegie Museums](https://carnegiemuseums.org), [Heinz History Center](https://www.heinzhistorycenter.org)), [The Frick](https://www.thefrickpittsburgh.org), and [more](https://en.wikipedia.org/wiki/List_of_museums_in_Pittsburgh))

**Food-related events**
- [Food Festivals](https://www.visitpittsburgh.com/events-festivals/food-festivals/)
- [Picklesburgh](https://www.picklesburgh.com/)
- [Pittsburgh Taco Fest](https://www.pghtacofest.com/)
- [Pittsburgh Restaurant Week](https://pittsburghrestaurantweek.com/)
- [Little Italy Days](https://littleitalydays.com)
- [Banana Split Fest](https://bananasplitfest.com)

**Sports** (Note that many of these pages also contain upcoming events, also see Wikipedia pages for each. Don't worry about scraping news/scores/recent stats from these sites.)
- General info ([Visit Pittsburgh](https://www.visitpittsburgh.com/things-to-do/pittsburgh-sports-teams/))
- Pittsburgh [Pirates](https://www.mlb.com/pirates), [Steelers](https://www.steelers.com), and [Penguins](https://www.nhl.com/penguins/)

### Collecting raw data

Your knowledge resource might include a mix of HTML pages, PDFs, and plain text documents. You will need to clean this data and convert it into a file format that facilitates your model development. Here are some tools that you could use:

- To process HTML pages, you can use [beautifulsoup4](https://pypi.org/project/beautifulsoup4/).
- To parse PDF documents into plain text, you can use [pypdf](https://github.com/py-pdf/pypdf) or [pdfplumber](https://github.com/jsvine/pdfplumber).

By the end of this step, you will have a collection of documents that will serve as the knowledge resource for your RAG system.

## Annotating data

Next, you will want to annotate question-answer pairs for two purposes: testing/analysis and optionally, training. Use the documents you compiled in the previous step to identify candidate questions for annotation. You will then use the same set of documents to identify answers for your questions.

### Test data

The testing (and analysis) data will be the data that you use to make sure that your system is working properly. In order to do so, you will want to manually annotate enough data so that you can get an accurate estimate of how your system is doing, and if any improvements to your system are having a positive impact. Some guidelines on this:

- **Manual annotation**: We expect you to manually annotate questions and answers for the test set. The aim of this task is to help you get a good understanding of what the data looks like and how to create a test set that helps give you a holistic understanding of how your system is performing, even on edge cases. You cannot use any models to help augment or create this test set.
- **Domain Relevance**: Your test data should be similar to the data that you will finally be tested on (questions about Pittsburgh and CMU). Use the knowledge resources mentioned above to curate your test set. 
- **Diversity**: Your test data should cover a wide range of questions Pittsburgh and CMU.
- **Size**: Your test data should be large enough to distinguish between good and bad models. If you want some guidelines about this, see the lecture on experimental design and human annotation.[^2]. We expect a test set size of at least 150 samples.
- **Quality**: Your test data should be of high quality. We recommend that you annotate it yourself and validate your annotations within your team.

To help you get started, here are some example questions:

- Questions that could be answered by just prompting a LLM
  - When was Carnegie Mellon University founded?
- Questions that can be better answered by augmenting LLM with relevant documents
  - What is the name of the annual pickle festival held in Pittsburgh?
- Questions that are likely answered only through augmentation
  - When was the Pittsburgh Soul Food Festival established?
- Questions that are sensitive to temporal signals
  - Who is performing at X venue on Y date?

See [Vu et al., 2023](https://arxiv.org/abs/2310.03214) for ideas about questions to prompt LLMs. For questions with multiple valid answers, you can include multiple reference answers per line in `reference_answers.json` (separated by a semicolon `;`). As long as your system generates one of the valid answers, it will be considered correct.

This test set you have constructed will constitute `data/test/questions.txt` and `data/test/reference_answers.json` in your submission. The evaluation for your answers will not be case sensitive, in line with the SQuAD paper.

### Training data

This is an optional aspect of this assignment, should you choose to train a model. The choice of training data is a bit more flexible, and depends on your implementation. If you are fine-tuning a model, you could possibly:

- Annotate it yourself manually through the same method as the test set.
- Do some sort of automatic annotation and/or data augmentation. You cannot use closed-source models (such as GPT 5, Claude etc.) for this process.
- Use existing datasets for transfer learning.

If you are using a LLM in a few-shot learning setting, you could possibly:

- Annotate examples for the task using the same method as the test set.
- Use existing datasets to identify examples for in-context learning.

This training set you have constructed will constitute `data/train/questions.txt` and `data/train/reference_answers.json` in your submission.

### Estimating your data quality

An important component of every data annotation effort is to estimate its quality. A standard approach is to measure inter-annotator agreement (IAA). To measure this, at least two members of your team should annotate a random subset of your test set. Compute [IAA](https://s3.amazonaws.com/resources.basistech.com/hltcon-presentations/2018/Zach_Yocum_Measuring_Inter-Annotator_Agreement_HLTCon2018.pdf) on this subset and report your findings. You should annotate at least 30% of your test set to measure IAA.

### Data Format for Annotated Data

Below we detail the format in which data should be structured when submitting your annotated data, for both test and training sets (if you have trained a model)

- **Input** (`questions.txt`): A text file containing one question per line.
- **Output from RAG system** (`system_output_test.json`): A json file containing system generated answers on your test set. Each pair contains a question number as the key and a single answer string generated by your system as the value for the corresponding question from `questions.txt`. 
- **Reference gold annotated answers** (`reference_answers.json`): A json file containing reference answers. Each pair contains a question number as the key and one or more reference answer strings as the value for the corresponding question from `questions.txt`.

Read our [model and data policy](#model-and-data-policy) for this assignment.

## Developing your RAG system

Unlike assignment 1, there is no starter code for this assignment. You are free to use open source libraries and models. However, keep in mind the specific constraints outlined across different sections in this assignment, and make sure you provide due credit for any resources used in your report. See our [model policy](#model-and-data-policy).

### Implementation Requirements

For your RAG system, you will need the following three components:

1. **Document & query embedder** (can use existing models)
2. **Document retriever** (implement sparse, dense and hybrid retrieval)
3. **Document reader** (aka. question-answering system) (can use existing models)

For the core retrieval components listed below, you **MUST** implement the retrieval logic directly using libraries such as sentence-transformers, scikit-learn, numpy etc. You cannot use high-level RAG frameworks like LangChain, LlamaIndex, or similar tools that abstract away the retrieval implementation:

**Document Chunking**: Large documents need to be broken down into smaller, manageable pieces (chunks) for effective retrieval, since embedding models have token limits and retrieving overly large text segments can dilute relevance and overwhelm the generation model. Implement document chunking strategies that split documents into appropriately-sized segments while preserving semantic coherence. You may want to implement and try out different approaches (e.g., fixed-size with overlap, sentence-aware chunking, paragraph-based chunking etc.), since chunking strategy can have a significant impact on downstream retrieval and generation performance. Consider edge cases like very short documents, very long paragraphs, and documents with special formatting.

**Hybrid Retrieval**: Implement a system that combines dense (vector-based) and sparse (keyword-based) retrieval:

- **Dense Retrieval**: Use embedding models to create vector representations of documents and queries. We recommend starting with sentence-transformers models like `all-MiniLM-L6-v2` for efficiency, though you can experiment with other models (For guidance on selecting high-performing embedding models, refer to the [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)) to improve performance. Use FAISS (https://github.com/facebookresearch/faiss) for efficient vector storage and similarity search. You'll need to implement the pipeline for embedding documents, building the FAISS index, and retrieving similar documents for queries.
- **Sparse Retrieval**: Integrate BM25 into your pipeline. You can use existing BM25 implementations, limited to [bm25s](https://github.com/xhluca/bm25s) or [rank-bm25](https://pypi.org/project/rank-bm25/), or build your own implementation if you wish to do so.
- **Combination Strategy**: Implement at least one established method for combining dense and sparse retrieval results. Common approaches include score normalization and weighted averaging, rank-based fusion methods (like Reciprocal Rank Fusion), using one method to filter or re-rank results from the other, or other ensemble techniques found in the literature. Experiment with different combination strategies to see which works best for your dataset.

To get started with the overall RAG architecture, you can reference:

- 11711 lecture notes
- [ACL 2023 tutorial on retrieval-augmented LMs](https://acl2023-retrieval-lm.github.io)
- [llama-recipes](https://github.com/facebookresearch/llama-recipes/tree/main/demo_apps/RAG_Chatbot_example) for an example RAG chatbot with Llama2
- [Ollama](https://github.com/ollama/ollama) or [llama.cpp](https://github.com/ggerganov/llama.cpp) to run LLMs locally on your machine

All the code for your data preprocessing, model development and evaluation will be a part of your GitHub repository (see submission for details).

## Generating results

Finally, you will run your systems on our test set (questions only) and submit your results to us. This test set will be released the day before the assignment is due (Wednesday, October 8th).

### Unseen test set

This test set will be curated by the course staff and will evaluate your system's ability to respond to a variety of questions about Pittsburgh and CMU. Because the goal of this assignment is not to perform hyperparameter optimization on this private test set, we ask you to not overfit to this test set. You are allowed to submit up to three output files (`system_outputs/system_output_{1,2,3}.json`). We will use the best performing file for grading.

The json file should be in the following format:
```json
{
    "1": "Answer 1",
    "2": "Answer 2; Answer 3",
    ...
}
```

Please make sure you follow this format. Points will be deducted for misformatted outputs.

### Release Policy for Late Days

If you plan to take a late day, you MUST let the TAs know via a Piazza post how many late days you plan to take and the date you plan to submit. A day before that day, a different test set will be released to you. For every day your group takes to submit after the communicated date, you will be penalized 10% of the overall grade. This is done to ensure fairness between groups using late days.

### Evaluation metrics

Your submissions will be evaluated on standard metrics, answer recall, exact match and F1. See section 6.1 of the original SQuAD paper for details. These metrics are token-based and measure the overlap between your system answer and the reference answer(s). Therefore, we recommend keeping your system generated responses as concise as possible. We will also grade your responses using a LLM.

## Writing report

We ask you to write a report detailing various aspects about your end-to-end system development (see the grading criteria below).

There will be a 7 page limit for the report, and we require you to use the [ACL template](https://github.com/acl-org/acl-style-files).

Make sure you cite all your sources (open-source models, libraries, papers, blogs etc.,) in your report.

## Submission & Grading

### Submission

Submit all deliverables on Canvas. Your submission checklist is below:

- [ ] Your report.
- [ ] A link to your GitHub repository containing your code.[^3]
- [ ] A file listing contributions of each team member,
  - [ ] data annotation contributions from each team member (e.g. teammate A: instances 1-X; teammate B: instances X-Y, teammate C: instances Y-Z).
  - [ ] data collection (scraping, processing) and modeling contributions from each team member (e.g. teammate A: writing scripts to ..., implementing ...; teammate B:...; teammate C:...;)
- [ ] Testing and (optionally) training data you annotated for this assignment.
- [ ] Your system outputs on our test set.

Your submission should be a zip file with the following structure (assuming the lowercase Andrew ID is ANDREWID). Make one submission per team.

```
ANDREWID/
├── report.pdf
├── github_url.txt
├── contributions.md
├── data/
│   ├── test/
│   │   ├── questions.txt
│   │   ├── reference_answers.json
│   │   ├── system_output_test.json
│   ├── train/
│   │   ├── questions.txt
│   │   ├── reference_answers.json
├── system_outputs/
│   ├── system_output_1.json
│   ├── system_output_2.json (optional)
│   ├── system_output_3.json (optional)
└── README.md
```

### Grading

The following points (max. 100 points) are derived from the results and your report. See course grading policy.[^4]

- **Submit data** (15 points): submit testing/training data of your creation.
- **Submit code** (15 points): submit your code for preprocessing and model development in the form of a GitHub repo. We may not necessarily run your code, but we will look at it. So please ensure that it contains up-to-date code with a README file outlining the steps to run it.
- **Results** (30 points): points based on your system's performance on our private test set. 20 points based on your performance using our metrics[^5], plus up to 10 points based on level of performance relative to other submissions from the class.
- **Report**: below points are awarded based on your report.
  - **Data creation** (10 points): clearly describe how you created your data. Please include the following details:
    - How did you compile your knowledge resource, and how did you decide which documents to include?
    - How did you extract raw data? What tools did you use?
    - What data was annotated for testing and training (what kind and how much)?
    - How did you decide what kind and how much data to annotate?
    - What sort of annotation interface did you use?
    - How did you estimate the quality of your annotations? (IAA)
    - For training data that you did not annotate, did you use any extra data and in what way?
  - **Model details** (10 points): clearly describe your model(s). Please include the following details:
    - What kind of methods (including baselines) did you try? Explain at least two variations (more is welcome). This can include variations of models, which data it was trained on, training strategy, embedding models, retrievers, re-rankers, etc.
    - What was your justification for trying these methods?
  - **Results** (10 points): report raw numbers from your experiments. Please include the following details:
    - What was the result of each model that you tried on the testing data that you created?
    - Are the results statistically significant?
  - **Analysis** (10 points): perform quantitative/qualitative analysis and present your findings:
    - Perform a comparison of the outputs on a more fine-grained level than just holistic accuracy numbers, and report the results. For instance, how did your models perform across various types of questions?
    - Report your results across at least two variations you tried, including variations of models, which data it was trained on, training strategy, embedding models, retrievers, re-rankers, etc.
    - Perform an analysis that evaluates the effectiveness of retrieve-and-augment strategy vs closed-book use of your models.
    - Evaluate your hybrid retrieval approach by comparing dense-only, sparse-only, and hybrid retrieval performance. Which fusion strategies work best for different types of questions?
    - Show examples of outputs from at least two of the systems you created. Ideally, these examples could be representative of the quantitative differences that you found above.

## Model and Data Policy

To make the assignment accessible to everyone:

- You are only allowed to use models that are also accessible through [HuggingFace](https://huggingface.co/models). This means you may not use closed models like OpenAI models, but you can opt to use a hosting service for an open model (such as the Hugging Face or Together APIs). **The model must have been released before January 1, 2025, and its size must not exceed 32B parameters**.
- You are only allowed to include publicly available data in your knowledge resource, test data and training data.
- You are welcome to use any open-source library to assist your data annotation and model training. For data annotation, you can use tools like Label Studio, Doccano, or similar annotation platforms to create your question-answer pairs efficiently. For model development, you can use standard ML libraries like scikit-learn, PyTorch, or HuggingFace Transformers for any model training, fine-tuning, or evaluation tasks. Make sure you check the license and provide due credit for all tools used.

If you have any questions about whether a model or data is allowed, please ask on Piazza.

## FAQ

**Q: "There are lots of links and subpages in the webpages, what is exactly the scope for this assignment?"**  
A: The scope includes the links on the readme and their descendant pages that are specifically relevant to the topics we have listed (e.g. history, events, music, food, sports). In addition, you may also include some PDFs that can be reached from those websites, even if they are not technically descendant pages. Use your best judgment to determine whether a webpage is relevant—a good heuristic is whether we can ask questions about factual content included in those pages.

**Q: "Is manual scraping prohibited?"**  
A: Manual scraping is not prohibited. To what extent you would perform the task manually is up to you.

**Q: "What libraries can I use for web scraping and document processing?"**  
A: You can use standard libraries like Selenium, Beautiful Soup, requests, pdfminer, pypdf, pdfplumber, and similar tools for data collection and preprocessing, as long as you provide proper credit in your report. These are considered basic utilities rather than high-level RAG frameworks.

**Q: "What is the date range I should consider for event-based questions?"**  
A: For any date-based questions specifically about events, we will only be asking questions about events happening from October 9th, 2025 to December 31st, 2025 (both days included). We will only ask questions about events occurring within this timeframe, including annual/recurring events.

**Q: "Can I use any closed-source models (OpenAI, Claude, etc.)?"**  
A: No. You cannot use any closed-source models for any part of the assignment, including embeddings, retrieval, or generation. All models must be open-weight and available through HuggingFace or similar open platforms.

**Q: "Can I use LangChain or related frameworks for this assignment?"**  
A: No, you cannot use LangChain or other RAG frameworks (such as LlamaIndex or similar libraries) that abstract away the core retrieval implementation. The purpose of this assignment is to learn the underlying mechanics of retrieval systems by implementing and integrating them yourself.

**Q: "What counts as 'manual implementation' for chunking and retrieval?"**  
A: You need to write the core logic yourself. For chunking: implement the splitting logic, overlap handling, and boundary detection. For hybrid retrieval: implement the integration pipeline, and result processing. You can use libraries as suggested in sections above (e.g., NLTK for tokenization, NumPy for math operations, FAISS for vector operations, existing BM25 implementations like bm25s or rank-bm25) but not complete retrieval frameworks like LangChain retrievers or high-level RAG pipeline frameworks.

**Q: "How do I show that my results are statistically significant?"**  
A: You can use statistical tests to determine whether performance differences between methods are statistically significant. Examples include paired t-tests (for continuous metrics like F1 scores) and McNemar's tests (for binary classification accuracy). You can run these tests on multiple metrics, or argue in your writeup that one metric is the best proxy for final system performance. If differences between methods are not statistically significant, interpret what this means for your system (e.g., a new feature may not actually improve performance despite appearing better).

**Q: "If I use late days, will I be evaluated on the same test set as those who do not use late days?"**  
A: No. We will be releasing different test sets for each of the 5 late days, ensuring fairness for everyone in the class.

## Acknowledgements

This assignment was based on the Spring 2024 version of this assignment by Graham Neubig and TAs.

## References

- Lewis et al., 2021. [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401).
- Touvron et al., 2023. [Llama 2: Open Foundation and Fine-Tuned Chat Models](https://arxiv.org/abs/2307.09288).
- Vu et al., 2023. [FreshLLMs: Refreshing Large Language Models with Search Engine Augmentation](https://arxiv.org/abs/2310.03214).


[^1]: See the [assignment policies]([http://www.phontron.com/class/anlp2024/assignments/#assignment-policies](https://cmu-l3.github.io/anlp-fall2025/#assignments)) for this class, including submission information, late day policy and more.

[^2]: See the previous [lecture notes](http://www.phontron.com/class/anlp2024/lectures/#experimental-design-and-human-annotation-feb-13) on experimental design and human annotation for guidance on annotation, size of test/train data, and general experimental design. This lecture will also take place on the day of the release of this assignment, and you can refer to those [notes](https://cmu-l3.github.io/anlp-fall2025/#schedule) too.

[^3]: Create a private GitHub repo and give access to the TAs in charge of this assignment by the deadline. See piazza announcement post for our GitHub usernames.

[^4]: Grading policy: https://cmu-l3.github.io/anlp-fall2025/#details

[^5]: In general, if your system is generating answers that are relevant to the question, it would be considered non-trivial. This could be achieved with a basic RAG system.
