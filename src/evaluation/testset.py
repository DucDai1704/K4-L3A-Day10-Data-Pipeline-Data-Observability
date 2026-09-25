from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build evaluation test set from cleaned dataframe.

    Creates 10 questions across 4 types: summary, authors, date, categories.
    Each question targets a specific paper with known ground truth.
    """
    if len(df) < 3:
        raise ValueError(f"Need at least 3 documents to build test set, got {len(df)}")

    test_items: list[dict[str, Any]] = []
    counter = 1

    # We'll pick papers round-robin and generate different question types
    question_types = ["summary", "authors", "date", "categories"]

    for idx, row in df.iterrows():
        if counter > 10:
            break

        q_type = question_types[(counter - 1) % len(question_types)]
        paper_id = row["paper_id"]
        title = row["title"]

        if q_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(row["summary"])
        elif q_type == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = row["authors_joined"]
        elif q_type == "date":
            question = f"When was the paper '{title}' published on?"
            ground_truth = row["published"]
        else:  # categories
            question = f"What categories does the paper '{title}' belong to?"
            ground_truth = row["categories_joined"]

        test_items.append(
            {
                "id": f"eval_{counter:03d}",
                "question_type": q_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        counter += 1

    write_json(output_path, test_items)
    return test_items
