Week 10 · Class 5 · Student Capstone


1. Repository structure

- data/          : input CSVs (raw + repaired) + metadata.yml
- outputs/       : pipeline results (generated, committed)
- notebook/      : generated notebook (run make_notebook.py)
- src/           : pipeline modules
- tests/         : pytest tests
- run.py         : CLI entry point for the pipeline
- make_notebook.py : regenerates notebook/notebook.ipynb

2. Run the pipeline

python run.py

3. Run the tests

python -m pytest tests/ -v

4. Generate the notebook

python make_notebook.py

5. Expected outputs

- outputs/cleaned_production.csv
- outputs/data_quality_report.csv
- outputs/daily_production_summary.csv
- outputs/rejected_source_records.csv

6. Submit a PR with your solution using feature/week10-class05-capstone

Dataset: synthetic training data only, not production data.