from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    if len(df) < 10:
        raise ValueError("At least 10 papers are required for the evaluation set")
    rows = df.sort_values("paper_id").to_dict("records")
    types = ["summary", "authors", "date", "categories", "summary",
             "authors", "date", "categories", "summary", "authors"]
    questions = []
    for n, (row, kind) in enumerate(zip(rows[:10], types, strict=True), start=1):
        title = row["title"]
        question, truth = {
            "summary": (f"What is the summary of the paper '{title}'?", first_sentence(row["summary"])),
            "authors": (f"Who authored the paper '{title}'?", row["authors_joined"]),
            "date": (f"When was the paper '{title}' published?", row["published"]),
            "categories": (f"What categories describe the paper '{title}'?", row["categories_joined"]),
        }[kind]
        questions.append({"id": f"eval_{n:03d}", "question_type": kind, "question": question,
                          "ground_truth": truth, "ground_truth_doc_ids": [row["paper_id"]]})
    write_json(output_path, questions)
    return questions
