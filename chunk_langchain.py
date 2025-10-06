#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
import json
from pathlib import Path
from typing import List, Dict, Any

# LangChain imports
from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain.schema import Document

class LangChainDocumentChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 50):
        """
        使用LangChain进行文档分块，针对不同文件类型使用不同的分割器
        
        Args:
            chunk_size: 每个chunk的最大字符数（用于Markdown文件）
            chunk_overlap: chunk之间的重叠字符数（用于Markdown文件）
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 初始化文本分割器（用于txt文件）- 500 tokens, 100 overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2500,  # txt文件使用500个tokens
            chunk_overlap=100,  # txt文件使用100个tokens重叠
            length_function=len,
            separators=[""],
            is_separator_regex=False,
        )
        
        # 初始化Markdown分割器（用于md文件）
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header 1"),
                ("##", "Header 2"),
            ],
            strip_headers=False,
        )
        
        # 用于处理Markdown分割后的进一步分割
        self.markdown_text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
            is_separator_regex=False,
        )
    
    def process_markdown_file(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """
        处理Markdown文件，保留标题上下文
        
        Args:
            file_path: 文件路径
            content: 文件内容
            
        Returns:
            包含chunk信息的列表
        """
        chunks = []
        
        try:
            # 使用Markdown分割器
            md_header_splits = self.markdown_splitter.split_text(content)
            
            for split in md_header_splits:
                # 获取标题信息
                metadata = split.metadata
                text_content = split.page_content
                
                # 构建标题上下文
                header_context = self._build_header_context(metadata)
                
                # 如果内容太长，进一步分割
                if len(text_content) > self.chunk_size:
                    # 使用文本分割器进一步分割
                    sub_chunks = self.markdown_text_splitter.split_text(text_content)
                    
                    for i, sub_chunk in enumerate(sub_chunks):
                        # 为每个子chunk添加标题上下文
                        enhanced_chunk = self._enhance_chunk_with_context(sub_chunk, header_context, i)
                        
                        chunks.append({
                            'text': enhanced_chunk,
                            'metadata': {
                                'file_path': file_path,
                                'file_type': '.md',
                                'splitter_type': 'markdown',
                                'header_context': header_context,
                                'chunk_index': len(chunks),
                                'sub_chunk_index': i,
                                'original_metadata': metadata
                            }
                        })
                else:
                    # 内容不长，直接使用
                    enhanced_chunk = self._enhance_chunk_with_context(text_content, header_context, 0)
                    
                    chunks.append({
                        'text': enhanced_chunk,
                        'metadata': {
                            'file_path': file_path,
                            'file_type': '.md',
                            'splitter_type': 'markdown',
                            'header_context': header_context,
                            'chunk_index': len(chunks),
                            'sub_chunk_index': 0,
                            'original_metadata': metadata
                        }
                    })
        
        except Exception as e:
            print(f"Error processing markdown file {file_path}: {e}")
            # 如果Markdown分割失败，回退到普通文本分割
            text_chunks = self.text_splitter.split_text(content)
            for i, chunk_text in enumerate(text_chunks):
                chunks.append({
                    'text': chunk_text,
                    'metadata': {
                        'file_path': file_path,
                        'file_type': '.md',
                        'splitter_type': 'text_fallback',
                        'header_context': [],
                        'chunk_index': i,
                        'sub_chunk_index': 0,
                        'original_metadata': {}
                    }
                })
        
        return chunks
    
    def _build_header_context(self, metadata: Dict[str, str]) -> List[str]:
        """
        构建标题上下文
        
        Args:
            metadata: 包含标题信息的元数据
            
        Returns:
            标题上下文列表
        """
        context = []
        
        # 按标题级别排序
        header_levels = []
        for key, value in metadata.items():
            if key.startswith('Header '):
                level = int(key.split(' ')[1])
                header_levels.append((level, value))
        
        # 按级别排序
        header_levels.sort(key=lambda x: x[0])
        
        # 构建上下文
        for level, title in header_levels:
            context.append('#' * level + ' ' + title)
        
        return context
    
    def _enhance_chunk_with_context(self, chunk_text: str, header_context: List[str], sub_index: int) -> str:
        """
        为chunk添加上下文信息
        
        Args:
            chunk_text: 原始chunk文本
            header_context: 标题上下文
            sub_index: 子chunk索引
            
        Returns:
            增强后的chunk文本
        """
        if not header_context:
            return chunk_text
        
        # 构建上下文信息
        context_info = "\n".join(header_context)
        
        # 如果是第一个子chunk，添加完整上下文
        if sub_index == 0:
            return f"{context_info}\n\n{chunk_text}"
        else:
            # 对于后续子chunk，只添加最近的标题
            if header_context:
                return f"{header_context[-1]}\n\n{chunk_text}"
        
        return chunk_text
    
    def process_text_file(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """
        处理文本文件
        
        Args:
            file_path: 文件路径
            content: 文件内容
            
        Returns:
            包含chunk信息的列表
        """
        chunks = []
        
        # 使用文本分割器
        text_chunks = self.text_splitter.split_text(content)
        
        for i, chunk_text in enumerate(text_chunks):
            chunks.append({
                'text': chunk_text,
                'metadata': {
                    'file_path': file_path,
                    'file_type': '.txt',
                    'splitter_type': 'text',
                    'header_context': [],
                    'chunk_index': i,
                    'sub_chunk_index': 0,
                    'original_metadata': {}
                }
            })
        
        return chunks
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        处理单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            包含chunk信息的字典
        """
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                return None
        
        # 根据文件类型选择处理方式
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.md':
            chunks_info = self.process_markdown_file(file_path, content)
            splitter_type = "markdown"
        else:
            chunks_info = self.process_text_file(file_path, content)
            splitter_type = "text"
        
        # 提取chunk文本
        chunks = [chunk_info['text'] for chunk_info in chunks_info]
        
        return {
            'file_path': file_path,
            'file_type': file_ext,
            'splitter_type': splitter_type,
            'total_chunks': len(chunks),
            'chunks': chunks,
            'chunks_info': chunks_info
        }
    
    def process_directory(self, input_dir: str, output_dir: str):
        """
        处理整个目录，将chunking结果保存到输出目录
        
        Args:
            input_dir: 输入目录路径
            output_dir: 输出目录路径
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # 创建输出目录
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 遍历所有文件
        processed_count = 0
        total_chunks = 0
        markdown_files = 0
        text_files = 0
        
        for file_path in input_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md']:
                # 获取相对路径
                rel_path = file_path.relative_to(input_path)
                
                # 创建对应的输出目录结构
                output_file_dir = output_path / rel_path.parent
                output_file_dir.mkdir(parents=True, exist_ok=True)
                
                # 处理文件
                result = self.process_file(str(file_path))
                if result is None:
                    continue
                
                # 统计文件类型
                if result['file_type'] == '.md':
                    markdown_files += 1
                else:
                    text_files += 1
                
                # 保存chunk信息到JSON文件
                output_file = output_file_dir / f"{file_path.stem}_chunks.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                # 保存每个chunk为单独的文本文件
                chunks_dir = output_file_dir / f"{file_path.stem}_chunks"
                chunks_dir.mkdir(exist_ok=True)
                
                for i, chunk in enumerate(result['chunks']):
                    chunk_file = chunks_dir / f"chunk_{i+1:03d}.txt"
                    with open(chunk_file, 'w', encoding='utf-8') as f:
                        f.write(chunk)
                
                processed_count += 1
                total_chunks += len(result['chunks'])
                print(f"Processed: {rel_path} -> {len(result['chunks'])} chunks ({result['splitter_type']} splitter)")
        
        print(f"\n=== 处理完成 ===")
        print(f"处理文件数: {processed_count}")
        print(f"  - Markdown文件: {markdown_files}")
        print(f"  - 文本文件: {text_files}")
        print(f"总chunk数: {total_chunks}")
        print(f"平均每文件chunk数: {total_chunks/processed_count if processed_count > 0 else 0:.2f}")

# 创建chunker实例
chunker = LangChainDocumentChunker(chunk_size=1000, chunk_overlap=200)


# In[ ]:


# 执行文档chunking
input_directory = "/Users/racheleven/Desktop/graduate_courses/11-711/anlp-fall2025-hw2/data"
output_directory = "/Users/racheleven/Desktop/graduate_courses/11-711/anlp-fall2025-hw2/data1"

print("开始使用LlamaIndex处理文档chunking...")
print(f"输入目录: {input_directory}")
print(f"输出目录: {output_directory}")
print(f"Chunk大小: {chunker.chunk_size}")
print(f"Chunk重叠: {chunker.chunk_overlap}")
print("-" * 50)

# 处理整个data目录
chunker.process_directory(input_directory, output_directory)

print("-" * 50)
print("文档chunking完成！")


# In[ ]:


# 统计chunking结果
import os
from pathlib import Path

def count_chunks_in_directory(directory):
    """统计目录中的chunk数量"""
    total_files = 0
    total_chunks = 0
    markdown_files = 0
    text_files = 0
    file_stats = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('_chunks.json'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        chunk_count = data.get('total_chunks', 0)
                        file_type = data.get('file_type', '')
                        splitter_type = data.get('splitter_type', '')
                        
                        total_chunks += chunk_count
                        total_files += 1
                        
                        if file_type == '.md':
                            markdown_files += 1
                        else:
                            text_files += 1
                            
                        file_stats.append({
                            'file': data.get('file_path', ''),
                            'chunks': chunk_count,
                            'file_type': file_type,
                            'splitter_type': splitter_type
                        })
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    return total_files, total_chunks, markdown_files, text_files, file_stats

# 统计结果
total_files, total_chunks, markdown_files, text_files, file_stats = count_chunks_in_directory(output_directory)

print(f"\n=== LlamaIndex Chunking 统计结果 ===")
print(f"处理文件总数: {total_files}")
print(f"  - Markdown文件: {markdown_files}")
print(f"  - 文本文件: {text_files}")
print(f"生成chunk总数: {total_chunks}")
print(f"平均每个文件chunk数: {total_chunks/total_files if total_files > 0 else 0:.2f}")

print(f"\n=== 各文件chunk数量 (前10个) ===")
for stat in sorted(file_stats, key=lambda x: x['chunks'], reverse=True)[:10]:
    print(f"{stat['chunks']:3d} chunks: {stat['file']} ({stat['splitter_type']} splitter)")

if len(file_stats) > 10:
    print(f"... 还有 {len(file_stats) - 10} 个文件")

# 显示一些chunk示例
print(f"\n=== Chunk示例 ===")
sample_files = [f for f in file_stats if f['chunks'] > 0][:3]
for sample in sample_files:
    print(f"\n文件: {sample['file']}")
    print(f"分割器类型: {sample['splitter_type']}")
    # 读取对应的chunk文件
    chunk_file = sample['file'].replace('/data/', '/data1/') + '_chunks.json'
    try:
        with open(chunk_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data['chunks']:
                print(f"第一个chunk预览: {data['chunks'][0][:200]}...")
    except Exception as e:
        print(f"无法读取chunk文件: {e}")

# 显示Markdown分割器的优势
print(f"\n=== Markdown分割器优势 ===")
markdown_samples = [f for f in file_stats if f['file_type'] == '.md' and f['chunks'] > 0][:2]
for sample in markdown_samples:
    print(f"\nMarkdown文件: {sample['file']}")
    chunk_file = sample['file'].replace('/data/', '/data1/') + '_chunks.json'
    try:
        with open(chunk_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data['chunks']:
                print(f"Chunk数量: {len(data['chunks'])}")
                print(f"第一个chunk: {data['chunks'][0][:150]}...")
    except Exception as e:
        print(f"无法读取chunk文件: {e}")


# In[ ]:




