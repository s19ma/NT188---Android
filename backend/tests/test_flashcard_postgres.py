"""Integration tests restricted to the dedicated local Docker database."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4
import pytest
from fastapi import HTTPException
from sqlalchemy import select, delete, update, func
from app.db.database import engine, SessionLocal
from app.models.user import User
from app.models.vocabulary import Vocabulary
from app.models.user_vocabulary import UserVocabulary
from app.models.learning_day import LearningDay
from app.schemas.vocabulary import ReviewVocabularyRequest
from app.api.v1.endpoints.vocabulary import get_due_flashcards, review_flashcard


@pytest.fixture
def scenario():
    u = engine.url
    if u.host != '127.0.0.1' or u.port != 5433 or u.database != 'english_video_flashcard_test' or u.username != 'test_user':
        pytest.skip('Dedicated local Docker test database required')
    with SessionLocal() as db:
        user = User(id=uuid4(), email=f'{uuid4().hex}@example.com', password_hash='fixture', email_verified=True)
        db.add(user); db.commit(); uid = user.id
    ids = []
    def make(count, due):
        with SessionLocal() as db:
            cards=[]
            for _ in range(count):
                v=Vocabulary(id=uuid4(),lemma='fixture'+uuid4().hex,language_code='en'); db.add(v); ids.append(v.id)
                card=UserVocabulary(id=uuid4(),user_id=uid,vocabulary_id=v.id,next_review_at=due)
                db.add(card); cards.append(card.id)
            db.flush()
            if due is None: db.execute(update(UserVocabulary).where(UserVocabulary.id.in_(cards)).values(next_review_at=None))
            db.commit(); return cards
    yield uid, make
    with SessionLocal() as db:
        db.execute(delete(User).where(User.id == uid)); db.execute(delete(Vocabulary).where(Vocabulary.id.in_(ids))); db.commit()


@pytest.mark.parametrize('count', [0, 5, 30, 31, 50, 100])
def test_due_queue_limit_order_and_future(scenario, count):
    uid, make=scenario; now=datetime.now(timezone.utc)
    past=now-timedelta(days=2); due=make(count,past); make(2,now+timedelta(days=1))
    with SessionLocal() as db:
        user=db.get(User,uid); rows=get_due_flashcards(due_only=True,limit=100,db=db,current_user=user)
        assert [x.id for x in rows] == sorted(due)[:30]
        assert len(rows)==min(count,30)


def test_null_and_user_isolation(scenario):
    uid, make=scenario; cards=make(1,None)
    with SessionLocal() as db:
        other=User(id=uuid4(),email=f'{uuid4().hex}@example.com',password_hash='fixture',email_verified=True); db.add(other); db.commit()
        try:
            assert [x.id for x in get_due_flashcards(True,30,db,db.get(User,uid))]==cards
            assert get_due_flashcards(True,30,db,other)==[]
        finally:
            db.execute(delete(User).where(User.id == other.id)); db.commit()


def test_retry_payload_conflict_and_future(scenario):
    uid,make=scenario; cid=make(1,datetime.now(timezone.utc)-timedelta(seconds=1))[0]; key=uuid4()
    with SessionLocal() as db:
        user=db.get(User,uid); body=ReviewVocabularyRequest(rating='good',request_id=key)
        first=review_flashcard(cid,body,db,user); second=review_flashcard(cid,body,db,user)
        assert first==second and first['review_count']==1 and first['interval_days']==3
        with pytest.raises(HTTPException) as err: review_flashcard(cid,ReviewVocabularyRequest(rating='hard',request_id=key),db,user)
        assert err.value.status_code==409; db.rollback()
        with pytest.raises(HTTPException) as err: review_flashcard(cid,ReviewVocabularyRequest(rating='good',request_id=uuid4()),db,user)
        assert err.value.status_code==409


def test_legacy_client_without_request_id_cannot_review_early(scenario):
    uid,make=scenario; cid=make(1,datetime.now(timezone.utc)+timedelta(days=1))[0]
    with SessionLocal() as db:
        with pytest.raises(HTTPException) as err:
            review_flashcard(cid,ReviewVocabularyRequest(rating='good'),db,db.get(User,uid))
        assert err.value.status_code==409


def test_legacy_client_without_request_id_can_review_due_card(scenario):
    uid,make=scenario; cid=make(1,datetime.now(timezone.utc)-timedelta(seconds=1))[0]
    with SessionLocal() as db:
        result=review_flashcard(cid,ReviewVocabularyRequest(rating='good'),db,db.get(User,uid))
        assert result.review_count==1


def test_concurrent_replay(scenario):
    uid,make=scenario; cid=make(1,datetime.now(timezone.utc)-timedelta(seconds=1))[0]; key=uuid4()
    def send():
        with SessionLocal() as db:
            return review_flashcard(cid,ReviewVocabularyRequest(rating='again',request_id=key),db,db.get(User,uid))
    with ThreadPoolExecutor(max_workers=2) as pool: a,b=list(pool.map(lambda _:send(),range(2)))
    assert a==b and a['review_count']==1 and a['interval_days']==0


def test_concurrent_distinct_requests_only_one_review(scenario):
    uid,make=scenario; cid=make(1,datetime.now(timezone.utc)-timedelta(seconds=1))[0]
    def send(_):
        with SessionLocal() as db:
            try:
                return review_flashcard(cid,ReviewVocabularyRequest(rating='good',request_id=uuid4()),db,db.get(User,uid))['review_count']
            except HTTPException as error:
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(send,range(2)))
    assert sorted(results)==[1,409]


def test_replay_retains_original_result_after_later_review(scenario):
    uid,make=scenario; cid=make(1,datetime.now(timezone.utc)-timedelta(seconds=1))[0]; key=uuid4()
    with SessionLocal() as db:
        user=db.get(User,uid); body=ReviewVocabularyRequest(rating='again',request_id=key)
        first=review_flashcard(cid,body,db,user)
        db.execute(update(UserVocabulary).where(UserVocabulary.id==cid).values(next_review_at=datetime.now(timezone.utc)-timedelta(seconds=1))); db.commit()
        later=review_flashcard(cid,ReviewVocabularyRequest(rating='good',request_id=uuid4()),db,user)
        replay=review_flashcard(cid,body,db,user)
        assert later['review_count']==2 and replay==first and replay['review_count']==1


def test_rollback_on_commit_failure(scenario):
    uid,make=scenario; cid=make(1,datetime.now(timezone.utc)-timedelta(seconds=1))[0]; key=uuid4()
    with SessionLocal() as db:
        user=db.get(User,uid)
        with patch.object(db,'commit',side_effect=RuntimeError('simulated failure')):
            with pytest.raises(RuntimeError): review_flashcard(cid,ReviewVocabularyRequest(rating='good',request_id=key),db,user)
        db.rollback()
    with SessionLocal() as db:
        card=db.get(UserVocabulary,cid); assert card.review_count==0
        assert db.scalar(select(func.count()).select_from(LearningDay).where(LearningDay.user_id == uid)) == 0
        result=review_flashcard(cid,ReviewVocabularyRequest(rating='good',request_id=key),db,db.get(User,uid))
        assert result['review_count']==1


def test_streak_recorded_once_for_due_reviews_and_not_for_replay_or_early_review(scenario):
    uid, make = scenario
    due = make(2, datetime.now(timezone.utc) - timedelta(seconds=1))
    future = make(1, datetime.now(timezone.utc) + timedelta(days=1))[0]
    key = uuid4()
    with SessionLocal() as db:
        user = db.get(User, uid)
        body = ReviewVocabularyRequest(rating='good', request_id=key)
        review_flashcard(due[0], body, db, user)
        review_flashcard(due[0], body, db, user)
        review_flashcard(due[1], ReviewVocabularyRequest(rating='again', request_id=uuid4()), db, user)
        with pytest.raises(HTTPException) as error:
            review_flashcard(future, ReviewVocabularyRequest(rating='good', request_id=uuid4()), db, user)
        assert error.value.status_code == 409
        db.rollback()
        assert db.scalar(select(func.count()).select_from(LearningDay).where(LearningDay.user_id == uid)) == 0
        db.execute(update(UserVocabulary).where(UserVocabulary.id == due[1]).values(next_review_at=datetime.now(timezone.utc)-timedelta(seconds=1)))
        db.commit()
        review_flashcard(due[1], ReviewVocabularyRequest(rating='good', request_id=uuid4()), db, user)
        assert db.scalar(select(func.count()).select_from(LearningDay).where(LearningDay.user_id == uid)) == 1


def test_daily_goal_caps_30_and_streak_requires_all(scenario):
    uid, make = scenario
    cards = make(31, datetime.now(timezone.utc) - timedelta(days=1))
    with SessionLocal() as db:
        user = db.get(User, uid)
        chosen = [c.id for c in get_due_flashcards(True, 30, db, user)]
        assert len(chosen) == 30
        for index, card in enumerate(chosen):
            review_flashcard(card, ReviewVocabularyRequest(rating='good', request_id=uuid4()), db, user)
            count = db.scalar(select(func.count()).select_from(LearningDay).where(LearningDay.user_id == uid))
            assert count == (1 if index == 29 else 0)
        assert get_due_flashcards(True, 30, db, user) == []
        other = next(c for c in cards if c not in chosen)
        with pytest.raises(HTTPException) as error:
            review_flashcard(other, ReviewVocabularyRequest(rating='good', request_id=uuid4()), db, user)
        assert error.value.status_code == 409


def test_daily_goal_concurrent_first_reviews_keep_single_snapshot(scenario):
    uid, make = scenario
    cards = make(31, datetime.now(timezone.utc) - timedelta(days=1))
    first_two = sorted(cards)[:2]
    def send(cid):
        with SessionLocal() as db:
            return review_flashcard(cid, ReviewVocabularyRequest(rating='good', request_id=uuid4()), db, db.get(User, uid))
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert len(list(pool.map(send, first_two))) == 2
    from app.models.daily_flashcard_goal import DailyFlashcardGoal
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(DailyFlashcardGoal).where(DailyFlashcardGoal.user_id == uid)) == 30
        assert db.scalar(select(func.count()).select_from(LearningDay).where(LearningDay.user_id == uid)) == 0


def test_boundary_time_and_get_does_not_change_schedule(scenario):
    uid,make=scenario; cards=make(2,datetime.now(timezone.utc)-timedelta(days=1))
    with SessionLocal() as db:
        now=db.scalar(select(func.now()))
        db.execute(update(UserVocabulary).where(UserVocabulary.id==cards[0]).values(next_review_at=now))
        db.execute(update(UserVocabulary).where(UserVocabulary.id==cards[1]).values(next_review_at=now+timedelta(seconds=1)))
        rows=get_due_flashcards(True,30,db,db.get(User,uid))
        assert [v.id for v in rows]==[cards[0]]
        assert db.get(UserVocabulary,cards[0]).next_review_at==now


def test_intervals_utc_and_key_conflict_across_cards(scenario):
    uid,make=scenario; cards=make(2,datetime.now(timezone.utc)-timedelta(seconds=1)); key=uuid4()
    with SessionLocal() as db:
        card=db.get(UserVocabulary,cards[0]); card.repetitions=1; card.interval_days=1; db.commit()
        result=review_flashcard(cards[0],ReviewVocabularyRequest(rating='good',request_id=key),db,db.get(User,uid))
        reviewed=datetime.fromisoformat(result['last_reviewed_at'].replace('Z','+00:00'))
        due=datetime.fromisoformat(result['next_review_at'].replace('Z','+00:00'))
        assert result['interval_days']==3 and due-reviewed==timedelta(days=3)
        with pytest.raises(HTTPException) as error:
            review_flashcard(cards[1],ReviewVocabularyRequest(rating='good',request_id=key),db,db.get(User,uid))
        assert error.value.status_code==409
        db.rollback()
        again=review_flashcard(cards[1],ReviewVocabularyRequest(rating='again',request_id=uuid4()),db,db.get(User,uid))
        reviewed=datetime.fromisoformat(again['last_reviewed_at'].replace('Z','+00:00'))
        due=datetime.fromisoformat(again['next_review_at'].replace('Z','+00:00'))
        assert due-reviewed==timedelta(minutes=10)


def test_http_contract_and_replay(scenario):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.deps import get_current_user
    uid,make=scenario; cid=make(1,datetime.now(timezone.utc)-timedelta(seconds=1))[0]
    def current_user():
        with SessionLocal() as db:
            user=db.get(User,uid); db.expunge(user); return user
    app.dependency_overrides[get_current_user]=current_user
    try:
        with TestClient(app) as client:
            assert client.get('/health').status_code==200
            overview=client.get('/api/v1/users/me/flashcards/overview')
            assert overview.status_code==200 and overview.json()['idempotent_review_supported'] is True
            queue=client.get('/api/v1/users/me/flashcards?limit=100')
            assert queue.status_code==200 and queue.json()[0]['id']==str(cid)
            invalid=client.post(f'/api/v1/users/me/flashcards/{cid}/review',json={'rating':'good','request_id':'not-a-uuid'})
            assert invalid.status_code==422
            key=str(uuid4()); body={'rating':'good','request_id':key}
            first=client.post(f'/api/v1/users/me/flashcards/{cid}/review',json=body)
            second=client.post(f'/api/v1/users/me/flashcards/{cid}/review',json=body)
            assert first.status_code==200 and first.json()==second.json()
            assert client.get('/api/v1/users/me/flashcards').json()==[]
    finally:
        app.dependency_overrides.pop(get_current_user,None)


def test_authenticated_vocabulary_and_progress_regression(scenario):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import hash_password
    from app.models.video import Video
    uid,make=scenario; cid=make(1,datetime.now(timezone.utc)-timedelta(days=1))[0]
    other_id=uuid4(); video_id=uuid4()
    with SessionLocal() as db:
        user=db.get(User,uid); user.password_hash=hash_password('fixturepassword123'); email=user.email
        vocab_id=db.get(UserVocabulary,cid).vocabulary_id
        db.add(User(id=other_id,email=f'{uuid4().hex}@example.com',password_hash=hash_password('fixturepassword123'),email_verified=True)); db.commit()
        db.add(Video(id=video_id,title='Fixture video',blob_name='fixture',status='published')); db.commit()
        other_email=db.get(User,other_id).email
    try:
        with TestClient(app) as client:
            assert client.get('/api/v1/users/me/vocabulary').status_code==401
            login=client.post('/api/v1/users/login',data={'username':email,'password':'fixturepassword123'})
            assert login.status_code==200
            headers={'Authorization':'Bearer '+login.json()['access_token']}
            other=client.post('/api/v1/users/login',data={'username':other_email,'password':'fixturepassword123'})
            assert other.status_code==200
            other_headers={'Authorization':'Bearer '+other.json()['access_token']}
            assert client.get('/api/v1/users/me/progress',headers=headers).status_code==200
            progress=client.put(f'/api/v1/users/me/progress/{video_id}',headers=headers,json={'position_ms':12000,'is_completed':False})
            assert progress.status_code==200 and progress.json()['position_ms']==12000
            assert client.get(f'/api/v1/users/me/progress/{video_id}',headers=other_headers).status_code==404
            assert client.get('/api/v1/users/me/vocabulary',headers=headers).status_code==200
            assert client.patch(f'/api/v1/users/me/vocabulary/{cid}/status',headers=other_headers,json={'learning_status':'learning'}).status_code==404
            assert client.patch(f'/api/v1/users/me/vocabulary/{cid}/status',headers=headers,json={'learning_status':'learning'}).status_code==200
            assert client.delete(f'/api/v1/users/me/vocabulary/{cid}',headers=other_headers).status_code==404
            assert client.delete(f'/api/v1/users/me/vocabulary/{cid}',headers=headers).status_code==204
            saved=client.post(f'/api/v1/vocabulary/{vocab_id}/save',headers=headers,json={})
            assert saved.status_code==201
            assert len(client.get('/api/v1/users/me/vocabulary',headers=headers).json())==1
    finally:
        with SessionLocal() as db:
            db.execute(delete(User).where(User.id==other_id)); db.execute(delete(Video).where(Video.id==video_id)); db.commit()
