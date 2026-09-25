from __future__ import annotations

from typing import Any

import pandas as pd


def build_test_set(df: pd.DataFrame, output_path: Any) -> list[dict[str, Any]]:
    """Tao bo evaluation set tu cleaned dataframe."""
    import json
    
    if len(df) == 0:
        return []
        
    test_set = []
    
    docs = df.head(10).to_dict('records')
    
    # Generate 10 questions
    types = ["summary", "summary", "summary", "authors", "authors", "authors", "date", "date", "categories", "categories"]
    
    for i, doc in enumerate(docs):
        if i >= len(types):
            break
            
        q_type = types[i]
        
        if q_type == "summary":
            question = f"What is the summary of the paper '{doc['title']}'?"
            ground_truth = doc['summary'].split('.')[0] + "." if '.' in doc['summary'] else doc['summary']
        elif q_type == "authors":
            question = f"Who are the authors of '{doc['title']}'?"
            ground_truth = f"The authors are {doc['authors_joined']}."
        elif q_type == "date":
            question = f"When was '{doc['title']}' published?"
            ground_truth = f"It was published on {doc['published']}."
        else: # categories
            question = f"What categories does '{doc['title']}' belong to?"
            ground_truth = f"It belongs to {doc['categories_joined']}."
            
        test_set.append({
            "id": f"eval_{i:03d}",
            "question_type": q_type,
            "question": question,
            "ground_truth": ground_truth,
            "ground_truth_doc_ids": [doc['paper_id']]
        })
        
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(test_set, f, indent=2, ensure_ascii=False)
        
    return test_set
