#!/bin/bash
#SBATCH -p preempt      
#SBATCH -N 1             
#SBATCH -t 02:00:00      
#SBATCH -J rag     
#SBATCH -o /home/gefeig/code/jobs/anlp/rag_%j.out   
#SBATCH --gres=gpu:1     
#SBATCH --cpus-per-task=8 

export PYTHONUNBUFFERED=1
CONDA_BASE=$(conda info --base)
cd /home/gefeig/code/11711/anlp-fall2025-hw2
source $CONDA_BASE/etc/profile.d/conda.sh
export HF_HOME='/tmp/gefeig'
conda activate evalscope
export WANDB_API_KEY="4c3c56ba5dfc397f04206e6dd72d74ca65795a0b"
echo "start"
# 
vllm serve Qwen/Qwen2.5-7B-Instruct  --tensor-parallel-size 1 --gpu-memory-utilization 0.9 --trust_remote_code --port 8000 &
sleep 280

# python eval_on_unseen.py
python eval_on_private.py --strategy hybrid \
--json_dir /home/gefeig/code/11711/anlp-fall2025-hw2/crawl_chunks/hybrid \
--llm_model Qwen/Qwen2.5-7B-Instruct

# python eval_on_private.py --strategy sparse \
# --json_dir /home/gefeig/code/11711/anlp-fall2025-hw2/crawl_chunks/hybrid \
# --llm_model Qwen/Qwen2.5-7B-Instruct

# python eval_on_private.py --strategy dense \
# --json_dir /home/gefeig/code/11711/anlp-fall2025-hw2/crawl_chunks/hybrid \
# --llm_model Qwen/Qwen2.5-7B-Instruct


# python /home/gefeig/code/11711/anlp-fall2025-hw2/simple_rag.py --strategy sparse \
# --json_dir /home/gefeig/code/11711/anlp-fall2025-hw2/crawl_chunks/naive \
# --llm_model Qwen/Qwen2.5-7B-Instruct

