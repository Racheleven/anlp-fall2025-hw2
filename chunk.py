#!/usr/bin/env python
# coding: utf-8

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any


class NaiveDocumentChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200,
                 strategy: str = "naive", txt_strategy: str = "paragraph"):
        """
        Args:
            chunk_size: Maximum number of characters in each chunk.
            chunk_overlap: Number of overlapping characters between consecutive chunks.
            strategy: Chunking strategy for Markdown and general processing ("naive", "markdown", "paragraph", "sentence", "hybrid")
            txt_strategy: Strategy for .txt files in hybrid mode ("naive" or "paragraph")
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy.lower()
        self.txt_strategy = txt_strategy.lower()


    def _split_text_naive(self, text: str) -> List[str]:
        """
        Naive fixed-length text splitting with overlap.
        """
        chunks = []
        start = 0
        n = len(text)
        while start < n:
            end = min(start + self.chunk_size, n)
            chunk = text[start:end]
            chunks.append(chunk.strip())
            start += self.chunk_size - self.chunk_overlap
        return chunks

    def _split_markdown_by_headers(self, content: str) -> List[Dict[str, Any]]:
        """
        Split Markdown content based on only level-1 (#) and level-2 (##) headers.
        Lower-level headers (### and below) are kept within the same section.
        """
        pattern = re.compile(r'^(#{1,2})\s+(.*)', re.MULTILINE)
        matches = list(pattern.finditer(content))

        if not matches:
            return [{'headers': [], 'text': content}]

        sections = []
        for i, match in enumerate(matches):
            header_level = len(match.group(1))
            header_text = match.group(2).strip()
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section_text = content[start_pos:end_pos].strip()

            sections.append({
                'headers': [(header_level, header_text)],
                'text': section_text
            })

        return sections


    def _split_by_paragraph(self, text: str) -> List[str]:
        """
        Split text into paragraphs by blank lines, with optional overlap.
        If chunk_overlap > 0, the end of the previous paragraph will be appended
        to the next chunk to maintain continuity.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return []

        
        if self.chunk_overlap <= 0:
            return paragraphs

        chunks = []
        prev_tail = ""
        for i, paragraph in enumerate(paragraphs):
            if prev_tail:
                combined = prev_tail + "\n\n" + paragraph
            else:
                combined = paragraph

            chunks.append(combined.strip())

            prev_tail = paragraph[-self.chunk_overlap:] if len(paragraph) > self.chunk_overlap else paragraph

        return chunks


    def _split_by_sentence(self, text: str) -> List[str]:
        """Split text into sentences by punctuation marks."""
        sentences = re.split(r'(?<=[。！？!?.])\s*', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def _build_header_context(self, headers: List[tuple]) -> List[str]:
        """
        Convert header tuples [(1, 'Title'), (2, 'Subsection')] 
        into Markdown-style headers like ['# Title', '## Subsection'].
        """
        return [("#" * lvl + " " + text) for lvl, text in headers]

    def process_markdown_file(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """
        Process a Markdown file by splitting based on headers, 
        then further splitting large sections into smaller fixed-size chunks.
        """
        chunks = []
        sections = self._split_markdown_by_headers(content)

        for section in sections:
            header_context = self._build_header_context(section["headers"])
            text = section["text"]

            if len(text) > self.chunk_size:
                sub_chunks = self._split_text_naive(text)
                for i, sub_chunk in enumerate(sub_chunks):
                    chunk_text = (
                        "\n".join(header_context) + "\n\n" + sub_chunk
                        if header_context
                        else sub_chunk
                    )
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {
                            "file_path": file_path,
                            "file_type": ".md",
                            "splitter_type": "markdown",
                            "header_context": header_context,
                            "chunk_index": len(chunks),
                            "sub_chunk_index": i,
                        },
                    })
            else:
                chunk_text = (
                    "\n".join(header_context) + "\n\n" + text
                    if header_context
                    else text
                )
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "file_path": file_path,
                        "file_type": ".md",
                        "splitter_type": "markdown",
                        "header_context": header_context,
                        "chunk_index": len(chunks),
                        "sub_chunk_index": 0,
                    },
                })
        return chunks

    def process_text_file(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """
        Process a plain text file using fixed-length splitting.
        """
        chunks = []
        text_chunks = self._split_text_naive(content)

        for i, chunk_text in enumerate(text_chunks):
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "file_path": file_path,
                    "file_type": ".txt",
                    "splitter_type": "text",
                    "header_context": [],
                    "chunk_index": i,
                    "sub_chunk_index": 0,
                },
            })
        return chunks
    def process_file(self, file_path: str) -> Dict[str, Any]:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="latin-1") as f:
                    content = f.read()

            ext = Path(file_path).suffix.lower()

            # Markdown hybrid
            if self.strategy in ["markdown", "hybrid"] and ext == ".md":
                chunks_info = self.process_markdown_file(file_path, content)
                splitter_type = "hybrid" if self.strategy == "hybrid" else "markdown"

            # TXT in hybrid mode or paragraph mode
            elif ext == ".txt" and (self.strategy == "paragraph" or self.strategy == "hybrid"):
                if self.strategy == "paragraph" or self.txt_strategy == "paragraph":
                    # paragraph-based
                    paragraph_chunks = self._split_by_paragraph(content)
                    chunks_info = [
                        {
                            "text": chunk_text,
                            "metadata": {
                                "file_path": file_path,
                                "file_type": ext,
                                "splitter_type": "paragraph",
                                "chunk_index": i,
                                "overlap_size": self.chunk_overlap
                            },
                        }
                        for i, chunk_text in enumerate(paragraph_chunks)
                    ]
                else:
                    # naive fixed-length
                    naive_chunks = self._split_text_naive(content)
                    chunks_info = [
                        {
                            "text": chunk_text,
                            "metadata": {
                                "file_path": file_path,
                                "file_type": ext,
                                "splitter_type": "naive",
                                "chunk_index": i,
                                "sub_chunk_index": 0,
                            },
                        }
                        for i, chunk_text in enumerate(naive_chunks)
                    ]
                splitter_type = f"txt_{self.txt_strategy}"

            # sentence mode
            elif self.strategy == "sentence":
                sentences = self._split_by_sentence(content)
                chunks_info = [
                    {"text": s, "metadata": {"file_path": file_path, "file_type": ext, "splitter_type": "sentence"}}
                    for s in sentences
                ]
                splitter_type = "sentence"

            # fallback naive
            else:
                naive_chunks = self._split_text_naive(content)
                chunks_info = [
                    {
                        "text": chunk_text,
                        "metadata": {
                            "file_path": file_path,
                            "file_type": ext,
                            "splitter_type": "naive",
                            "chunk_index": i,
                            "sub_chunk_index": 0,
                        },
                    }
                    for i, chunk_text in enumerate(naive_chunks)
                ]
                splitter_type = "naive"

            return {
                "file_path": file_path,
                "file_type": ext,
                "splitter_type": splitter_type,
                "total_chunks": len(chunks_info),
                "chunks": [c["text"] for c in chunks_info],
                "chunks_info": chunks_info,
            }
    
    def save_to_json(self, result: Dict[str, Any], output_dir: str):
        """
        Save the chunking result for a single file as a JSON file.
        All JSONs from the same chunk strategy are saved in a subfolder named after the strategy.
        Args:
            result: Output from process_file()
            output_dir: Base directory to save JSON files.
        """
        strategy_folder = Path(output_dir) / self.strategy
        strategy_folder.mkdir(parents=True, exist_ok=True)

        file_name = Path(result["file_path"]).stem + "_chunks.json"
        output_path = strategy_folder / file_name

        slim_result = {
            "file_path": result["file_path"],
            "chunks": result["chunks"]
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(slim_result, f, ensure_ascii=False, indent=2)

        print(f"✅ [{self.strategy}] Saved JSON file: {output_path}")


    def process_directory(self, input_dir: str, output_dir: str):
        """
        Process all files in a directory and save their chunked results.
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        total_files, total_chunks = 0, 0

        for file_path in input_path.rglob("*"):
            if not file_path.is_file() or file_path.suffix.lower() not in [".txt", ".md"]:
                continue

            result = self.process_file(str(file_path))
            if not result:
                continue

            # Save as JSON
            self.save_to_json(result, output_path)

            total_files += 1
            total_chunks += len(result["chunks"])
            print(f"Processed {file_path.name} -> {len(result['chunks'])} chunks")

        print("\n=== Processing Complete ===")
        print(f"Total files processed: {total_files}")
        print(f"Total chunks generated: {total_chunks}")
        print(f"Average chunks per file: {total_chunks / total_files if total_files else 0:.2f}")


if __name__ == "__main__": 
    input_dir = r"D:\code_VScode_Python\11711\anlp-fall2025-hw2\anlp-fall2025-hw2\data\all_output"
    output_dir = r"D:\code_VScode_Python\11711\anlp-fall2025-hw2\data\crawl_chunks"

    chunker = NaiveDocumentChunker(chunk_size=1000, chunk_overlap=200,strategy="paragraph")
    print(f"Starting naive chunking for: {input_dir}")
    chunker.process_directory(input_dir, output_dir)
    print("✅ Chunking completed.")
