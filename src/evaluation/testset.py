from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: str | Path) -> list[dict[str, Any]]:
    """Tạo bộ evaluation test set chuẩn hóa gồm 10 câu hỏi qua 4 nhóm nghiệp vụ.

    1. Kiểm tra số lượng document tối thiểu.
    2. Chọn các paper đại diện để tạo câu hỏi.
    3. Tạo 4 loại câu hỏi:
       - summary (3 câu)
       - authors (3 câu)
       - date (2 câu)
       - categories (2 câu)
    4. Mỗi row có schema:
       - id: eval_001..eval_010
       - question_type: summary | authors | date | categories
       - question: câu hỏi tự nhiên
       - ground_truth: đáp án chuẩn
       - ground_truth_doc_ids: [paper_id]
    5. Ghi file JSON vào output_path và return list.
    """
    if len(df) < 5:
        raise ValueError("DataFrame must contain at least 5 records to build evaluation test set.")

    # Select distinct papers for diverse coverage
    papers = df.to_dict(orient="records")
    test_set: list[dict[str, Any]] = []

    # Distribution of 10 questions: 3 summary, 3 authors, 2 date, 2 categories
    configs = [
        ("summary", 0),
        ("summary", 1),
        ("summary", 2),
        ("authors", 3),
        ("authors", 4),
        ("authors", 5),
        ("date", 6),
        ("date", 7),
        ("categories", 8),
        ("categories", 9),
    ]

    for idx, (q_type, paper_idx) in enumerate(configs, start=1):
        paper = papers[paper_idx % len(papers)]
        q_id = f"eval_{idx:03d}"
        title = paper["title"]
        paper_id = paper["paper_id"]

        if q_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(paper.get("summary", "")) or paper.get("summary", "")
        elif q_type == "authors":
            question = f"Who are the authors of the paper '{title}'?"
            ground_truth = paper.get("authors_joined", "")
        elif q_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = paper.get("published", "")
        else:  # categories
            question = f"What are the research categories or subjects of the paper '{title}'?"
            ground_truth = paper.get("categories_joined", "") or paper.get("primary_category", "")

        test_set.append(
            {
                "id": q_id,
                "question_type": q_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    out_p = Path(output_path)
    write_json(out_p, test_set)
    return test_set
