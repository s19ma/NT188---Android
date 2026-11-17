"""Insert reviewed dictionary-backed transcript words without touching saved-word records."""
import hashlib
import json
import re
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text

HOST = 'ep-icy-lab-a16xdltv.ap-southeast-1.aws.neon.tech'
INPUT = Path('deploy/video-vocabulary-candidates.json')


def main():
    raw = INPUT.read_bytes()
    rows = json.loads(raw)
    candidates = [r for r in rows if r.get('status') == 'ok' and r.get('definition')]
    if not candidates or any(not re.fullmatch(r'[a-z]+', r['lemma']) for r in candidates):
        raise RuntimeError('Invalid candidate data')
    if len({r['lemma'] for r in candidates}) != len(candidates):
        raise RuntimeError('Duplicate candidates')
    engine = create_engine(dotenv_values('.env')['DIRECT_DATABASE_URL'])
    if engine.url.host != HOST or engine.url.database != 'english_video_db':
        raise RuntimeError('Unexpected production database')
    with engine.begin() as db:
        db.execute(text("set local lock_timeout='5s'"))
        db.execute(text("set local statement_timeout='60s'"))
        if db.scalar(text('select version_num from alembic_version')) != 'e8a72c14d931':
            raise RuntimeError('Unexpected schema revision')
        lines = db.execute(text("select v.id, s.content from videos v join transcripts t on t.video_id=v.id join transcript_segments s on s.transcript_id=t.id where v.status='published' order by v.id,s.sequence_number")).all()
        words = set(re.findall(r'[a-z]+', ' '.join(line or '' for _, line in lines).lower()))
        if not all(row['lemma'] in words for row in candidates):
            raise RuntimeError('Candidate no longer matches published transcripts')
        available = {row['lemma']: row for row in candidates}
        per_video = {}
        for video_id, line in lines:
            per_video.setdefault(video_id, {})
            for word in re.findall(r'[a-z]+', (line or '').lower()):
                if word in available:
                    per_video[video_id][word] = per_video[video_id].get(word, 0) + 1
        # Interleave transcripts to avoid consuming the quota on a single video.
        queues = [iter(sorted(counts, key=lambda word: (len(word) <= 3, -counts[word], word)))
                  for counts in per_video.values()]
        chosen = set()
        while len(chosen) < 500 and queues:
            next_queues = []
            for queue in queues:
                word = next((word for word in queue if word not in chosen), None)
                if word is not None:
                    chosen.add(word)
                    next_queues.append(queue)
                    if len(chosen) >= 500:
                        break
            queues = next_queues
        candidates = [available[word] for word in sorted(chosen)]
        before = db.scalar(text('select count(*) from vocabulary'))
        stmt = text("""insert into vocabulary (lemma, language_code, phonetic, part_of_speech, definition)
                     select lemma, 'en', phonetic, part_of_speech, definition
                     from jsonb_to_recordset(cast(:records as jsonb))
                     as x(lemma text, phonetic text, part_of_speech text, definition text)
                     on conflict (language_code, lemma) do nothing returning id""")
        inserted = len(db.execute(stmt, {'records': json.dumps(candidates, ensure_ascii=False)}).all())
        after = db.scalar(text('select count(*) from vocabulary'))
        if after - before != inserted:
            raise RuntimeError('Unexpected count change; transaction rolled back')
    print('candidate sha256:', hashlib.sha256(raw).hexdigest().upper())
    print('dictionary-backed candidates:', len(candidates), 'inserted:', inserted, 'total:', after)


if __name__ == '__main__':
    main()
