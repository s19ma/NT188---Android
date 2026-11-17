"""Prepare dictionary-backed candidates from published transcripts without writing production."""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from sqlalchemy import create_engine, text
from dotenv import dotenv_values

HOST = 'ep-icy-lab-a16xdltv.ap-southeast-1.aws.neon.tech'
OUTPUT = Path('deploy/video-vocabulary-candidates.json')


def lookup(word):
    url = 'https://api.dictionaryapi.dev/api/v2/entries/en/' + word
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=12)
            if response.status_code == 404:
                return {'lemma': word, 'status': 'not_found'}
            if response.status_code == 429 or response.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list) or not payload:
                return {'lemma': word, 'status': 'invalid'}
            entry = payload[0]
            meanings = entry.get('meanings') or []
            meaning = next((x for x in meanings if x.get('definitions')), {})
            definition = next((x.get('definition') for x in meaning.get('definitions', []) if x.get('definition')), None)
            phonetic = entry.get('phonetic') or next((x.get('text') for x in entry.get('phonetics', []) if x.get('text')), None)
            return {'lemma': word, 'status': 'ok' if definition else 'missing_definition',
                    'phonetic': (phonetic or '')[:150] or None,
                    'part_of_speech': (meaning.get('partOfSpeech') or '')[:50] or None,
                    'definition': definition}
        except (requests.RequestException, ValueError, TypeError):
            time.sleep(2 ** attempt)
    return {'lemma': word, 'status': 'unavailable'}


def main():
    url = dotenv_values('.env')['DIRECT_DATABASE_URL']
    engine = create_engine(url, connect_args={'options': '-c default_transaction_read_only=on'})
    if engine.url.host != HOST or engine.url.database != 'english_video_db':
        raise RuntimeError('Unexpected source database')
    with engine.connect() as db:
        known = set(db.execute(text("select lower(lemma) from vocabulary where language_code='en'")).scalars())
        lines = db.execute(text("select s.content from videos v join transcripts t on t.video_id=v.id join transcript_segments s on s.transcript_id=t.id where v.status='published'")).scalars().all()
    words = sorted(set(re.findall(r'[a-z]+', ' '.join(x or '' for x in lines).lower())) - known)
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for index, item in enumerate(pool.map(lookup, words), 1):
            results.append(item)
            if index % 100 == 0:
                print(f'Checked {index}/{len(words)}', flush=True)
    OUTPUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    for status in sorted({row['status'] for row in results}):
        print(status, sum(row['status'] == status for row in results))
    print('Candidate file:', OUTPUT)


if __name__ == '__main__':
    main()
