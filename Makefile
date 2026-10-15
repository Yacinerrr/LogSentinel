install:   ; pip install -r requirements.txt -r requirements-ml.txt -r requirements-dev.txt -r requirements-dashboard.txt
data:      ; python -m ml.generate_synthetic --n 300 --out data/synthetic.csv
train:     ; python -m ml.train data/synthetic.csv
eval:      ; python -m ml.evaluate data/synthetic.csv
api:       ; uvicorn app.api.main:create_app --factory --reload
dash:      ; streamlit run dashboard/app.py
test:      ; pytest -q
