from flask import Flask, render_template, request, jsonify, Response, send_file
import os
import time
import threading
import json
import importlib.util
from rank import RankingPipeline
from config import SAMPLE_CANDIDATES_JSON, CANDIDATES_JSONL, VALIDATE_SCRIPT, DATA_DIR

app = Flask(__name__)

TASKS = {}
RESULTS = {}
CANDIDATE_CACHE = {}


def get_csv_path(task_id):
    return os.path.join(os.path.dirname(__file__), f"submission_{task_id}.csv")


def rank_background_task(task_id, source):
    try:
        TASKS[task_id] = {
            'status': 'running', 'progress': 0, 'stage': 'Initializing',
            'total': 0, 'processed': 0,
        }

        if source == 'sample':
            input_path = SAMPLE_CANDIDATES_JSON
            total = 50
        elif source == 'full':
            input_path = CANDIDATES_JSONL
            total = 100000
        elif source.startswith('custom_'):
            input_path = os.path.join(os.path.dirname(__file__), source)
            if input_path.endswith('.jsonl'):
                with open(input_path, 'r', encoding='utf-8') as f:
                    total = sum(1 for line in f if line.strip())
            else:
                with open(input_path, 'r', encoding='utf-8') as f:
                    total = len(json.load(f))
        else:
            raise ValueError(f"Unknown data source: {source}")

        if not os.path.exists(input_path):
            file_label = "Sample candidates file" if source == 'sample' else "Full candidates database"
            raise FileNotFoundError(
                f"{file_label} not found at {input_path}. "
                f"Place candidates.jsonl in the data/ folder or use Upload Dataset."
            )

        TASKS[task_id]['total'] = total

        def progress_callback(stage, processed, filtered_in):
            pct = min(99, int((processed / max(total, 1)) * 100))
            TASKS[task_id]['progress'] = pct
            TASKS[task_id]['stage'] = f"Filtering & Scoring (kept {filtered_in})"
            TASKS[task_id]['processed'] = processed

        pipeline = RankingPipeline()
        output_path = get_csv_path(task_id)

        TASKS[task_id]['stage'] = 'Starting pipeline...'
        top_n = 100 if total >= 100 else total
        top_results = pipeline.run(input_path, output_path, progress_callback, top_n=top_n)

        TASKS[task_id]['progress'] = 100
        TASKS[task_id]['stage'] = 'Complete'
        TASKS[task_id]['status'] = 'complete'

        candidates_data = []
        for item in top_results:
            c = item['candidate']
            prof = c.get('profile', {})
            verdict = 'Honeypot' if item['honeypot_flag'] else (
                'Disqualified' if item.get('hard_disqualified') else (
                    'Strong Yes' if item['rank'] <= 10 and item['score'] >= 0.65 else
                    'Yes' if item['rank'] <= 25 and item['score'] >= 0.45 else
                    'Maybe' if item['score'] >= 0.25 else 'No'
                )
            )
            candidates_data.append({
                'rank': item['rank'],
                'candidate_id': item['candidate_id'],
                'name': prof.get('anonymized_name', 'Unknown'),
                'title': prof.get('current_title', 'Unknown'),
                'score': item['score'],
                'reasoning': item['reasoning'],
                'verdict': verdict,
                'years_of_experience': prof.get('years_of_experience', 0),
                'location': prof.get('location', ''),
                'country': prof.get('country', ''),
                'skills': [s['name'] for s in c.get('skills', [])],
                'composite_breakdown': item['breakdown'],
                'honeypot_flag': item['honeypot_flag'],
                'hard_disqualified': item.get('hard_disqualified', False),
            })

            CANDIDATE_CACHE[item['candidate_id']] = {
                'candidate_id': item['candidate_id'],
                'career_history': c.get('career_history', []),
                'education': c.get('education', []),
                'skills': c.get('skills', []),
            }

        RESULTS[task_id] = {
            'candidates': candidates_data,
            'stats': {
                'total_processed': total,
                'shortlisted': len(top_results),
                'avg_top10_score': (
                    sum(c['score'] for c in candidates_data[:10]) / 10
                    if len(candidates_data) >= 10 else 0
                ),
                'honeypots_detected': pipeline.honeypots_detected,
                'disqualified_count': pipeline.disqualified_count,
                'soft_penalized_count': pipeline.soft_penalized_count,
            },
        }
    except Exception as e:
        TASKS[task_id] = {'status': 'error', 'message': str(e)}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/rank', methods=['POST'])
def start_ranking():
    data = request.json
    source = data.get('source', 'sample')
    task_id = str(int(time.time()))

    thread = threading.Thread(target=rank_background_task, args=(task_id, source))
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id})


@app.route('/api/progress/<task_id>')
def progress(task_id):
    def generate():
        while True:
            if task_id in TASKS:
                task = TASKS[task_id]
                yield f"data: {json.dumps(task)}\n\n"
                if task['status'] in ['complete', 'error']:
                    break
            else:
                yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
                break
            time.sleep(0.5)
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/results/<task_id>')
def get_results(task_id):
    if task_id in RESULTS:
        return jsonify(RESULTS[task_id])
    return jsonify({'error': 'Results not found'}), 404


@app.route('/api/jd-analysis')
def get_jd_analysis():
    jd_data = {
        'role': 'Senior AI Engineer — Founding Team at Redrob AI',
        'details': {
            'location': 'Pune/Noida India (Hybrid), open to relocation',
            'experience': '5-9 years (flexible)',
            'company': 'Redrob AI (Series A, AI-native talent intelligence platform)',
        },
        'must_haves': [
            'Production embeddings-based retrieval (sentence-transformers, OpenAI, BGE, E5)',
            'Vector databases / hybrid search (Pinecone, Weaviate, Qdrant, Milvus, FAISS, Elasticsearch, OpenSearch)',
            'Strong Python coding expertise',
            'Evaluation frameworks for ranking (NDCG, MRR, MAP, A/B testing)',
        ],
        'nice_to_haves': [
            'LLM fine-tuning (LoRA, QLoRA, PEFT)',
            'Learning-to-rank models (XGBoost, neural)',
            'HR-tech / recruiting tech / marketplace exposure',
            'Distributed systems / large-scale inference',
            'Active open-source contributions',
        ],
        'disqualifiers': [
            'Pure academic/research profile without production shipping',
            'Recent LangChain/OpenAI wrappers (<12 months experience)',
            'No production code written in the last 18 months',
            'Entire career at consulting service companies (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini)',
            'CV/Speech/Robotics expertise without NLP/IR',
            'Frequent job-hoppers switching every 1.5 years',
            'Non-technical title with keyword-stuffed AI skills (honeypot pattern)',
        ],
    }
    return jsonify(jd_data)


@app.route('/api/download/<task_id>')
def download_csv(task_id):
    csv_path = get_csv_path(task_id)
    if os.path.exists(csv_path):
        return send_file(
            csv_path, as_attachment=True,
            download_name=f"submission_{task_id}.csv", mimetype='text/csv',
        )
    return jsonify({'error': 'CSV file not found'}), 404


@app.route('/api/validate/<task_id>')
def validate_csv(task_id):
    csv_path = get_csv_path(task_id)
    if not os.path.exists(csv_path):
        return jsonify({'status': 'error', 'message': 'CSV file not found'}), 404

    try:
        if not os.path.exists(VALIDATE_SCRIPT):
            return jsonify({'status': 'error', 'message': 'Validation script not found'}), 500

        spec = importlib.util.spec_from_file_location("validate_submission", VALIDATE_SCRIPT)
        val_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(val_mod)

        errors = val_mod.validate_submission(csv_path)
        if errors:
            return jsonify({'status': 'invalid', 'errors': errors})
        return jsonify({'status': 'valid', 'errors': []})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/candidate/<candidate_id>')
def get_candidate(candidate_id):
    if candidate_id in CANDIDATE_CACHE:
        return jsonify(CANDIDATE_CACHE[candidate_id])
    return jsonify({'error': 'Candidate not found'}), 404


@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No file selected for uploading'}), 400

    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ('.json', '.jsonl'):
        return jsonify({'message': 'Only .json and .jsonl files are supported'}), 400

    from werkzeug.utils import secure_filename
    sec_name = secure_filename(filename)
    unique_filename = f"custom_{int(time.time())}_{sec_name}"
    upload_path = os.path.join(os.path.dirname(__file__), unique_filename)

    try:
        file.save(upload_path)
        return jsonify({'filename': unique_filename})
    except Exception as e:
        return jsonify({'message': f'Failed to save file: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
