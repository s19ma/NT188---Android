package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.view.View;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.lifecycle.ViewModelProvider;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class FlashcardActivity extends AppCompatActivity {
    private View card, btnDeleteCard, btnAgain, btnHard, btnGood, btnEasy;
    private TextView word, sub, hint, counter;
    private TextView hardInterval, goodInterval, easyInterval;
    private ProgressBar progress;
    private boolean front = true, loading, ratingInFlight, cardsLoaded, studyDeckMode;
    private int index, reviewed;
    private TextToSpeech tts;
    private List<FlashcardRepository.FlashcardItem> cards;
    private FlashcardReviewModel model;
    private boolean checkingIdentity;
    private boolean restoreFromSystem;
    private final Runnable reviewChanged = this::onReviewChanged;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.layout_6_flashcard_n_t_p);
        model = new ViewModelProvider(this).get(FlashcardReviewModel.class);
        studyDeckMode = getIntent().hasExtra("practice_filter");
        cards = model.cards;
        if (model.loaded) { cardsLoaded = true; reviewed = model.reviewed; index = model.cardIndex; front = model.front; }
        restoreFromSystem = !cardsLoaded && state != null && state.getBoolean("cards_loaded");
        card = findViewById(R.id.card_flashcard); word = findViewById(R.id.tv_flashcard_word);
        sub = findViewById(R.id.tv_flashcard_sub); hint = findViewById(R.id.tv_flashcard_hint);
        counter = findViewById(R.id.tv_flashcard_counter); progress = findViewById(R.id.progress_flashcard);
        btnDeleteCard = findViewById(R.id.btn_delete_card); btnAgain = findViewById(R.id.btn_again);
        btnHard = findViewById(R.id.btn_hard); btnGood = findViewById(R.id.btn_good); btnEasy = findViewById(R.id.btn_easy);
        hardInterval = findViewById(R.id.tv_hard_interval); goodInterval = findViewById(R.id.tv_good_interval); easyInterval = findViewById(R.id.tv_easy_interval);
        if (btnDeleteCard != null) btnDeleteCard.setVisibility(View.GONE);
        if (studyDeckMode) {
            if (btnAgain != null) btnAgain.setVisibility(View.GONE);
            if (btnHard != null) btnHard.setVisibility(View.GONE);
            if (btnEasy != null) btnEasy.setVisibility(View.GONE);
            TextView label = findViewById(R.id.tv_good_label);
            if (label != null) label.setText("Tiếp theo");
            if (goodInterval != null) goodInterval.setVisibility(View.GONE);
        }
        tts = new TextToSpeech(this, result -> { if (result == TextToSpeech.SUCCESS) tts.setLanguage(Locale.US); });
        if (card != null) card.setOnClickListener(v -> { if (!cards.isEmpty()) { front = !front; model.front = front; if (!studyDeckMode) model.persist(); updateUi(); } });
        View btnSpeak = findViewById(R.id.btn_speak);
        if (btnSpeak != null) btnSpeak.setOnClickListener(v -> speakCurrentCard());
        if (btnAgain != null) btnAgain.setOnClickListener(v -> submitRating("again"));
        if (btnHard != null) btnHard.setOnClickListener(v -> submitRating("hard"));
        if (btnGood != null) btnGood.setOnClickListener(v -> submitRating("good"));
        if (btnEasy != null) btnEasy.setOnClickListener(v -> submitRating("easy"));
        bindNavigation();
        loading = true; updateUi();
    }

    @Override protected void onSaveInstanceState(Bundle state) {
        super.onSaveInstanceState(state);
        if (cardsLoaded) {
            state.putBoolean("cards_loaded", true);
        }
    }

    @Override protected void onResume() {
        super.onResume();
        model.observe(reviewChanged);
        if (BackendApi.token == null) BackendApi.token = SessionManager.load(this);
        if (BackendApi.token == null) { startActivity(new Intent(this, LoginActivity.class)); finish(); return; }
        if (checkingIdentity) return;
        checkingIdentity = true; loading = true; updateUi();
        final String token = BackendApi.token;
        BackendApi.run(this, () -> (org.json.JSONObject) BackendApi.send("/users/me", "GET", null, null, token), user -> {
            checkingIdentity = false;
            String owner = user.optString("id", "");
            if (owner.isEmpty() || !token.equals(BackendApi.token)) { loading = false; updateUi(); return; }
            if (model.ownerId != null && !owner.equals(model.ownerId)) {
                cards.clear(); model.completedIds.clear(); model.loaded = false; cardsLoaded = false;
                model.pendingId = model.pendingCard = model.pendingRating = null;
            }
            model.bind(this, owner);
            if (studyDeckMode) {
                if (cardsLoaded && model.loaded) { loading = false; updateUi(); }
                else loadPracticeCards();
                return;
            }
            if (cardsLoaded && model.loaded) { loading = false; onReviewChanged(); return; }
            org.json.JSONObject snapshot = FlashcardSessionStore.read(this, owner);
            if (snapshot != null && owner.equals(snapshot.optString("owner")) && snapshot.optJSONArray("cards") != null
                    && snapshot.optJSONArray("cards").length() > 0) {
                if (restoreFromSystem || getIntent().getBooleanExtra("resume_flashcard_session", false)) {
                    restoreFromSystem = false;
                    getIntent().removeExtra("resume_flashcard_session"); restoreSession(snapshot);
                } else {
                    loading = false;
                    new androidx.appcompat.app.AlertDialog.Builder(this).setTitle("Tiếp tục học")
                            .setMessage("Bạn có một phiên flashcard chưa hoàn thành.")
                            .setPositiveButton("Tiếp tục học", (d, w) -> restoreSession(snapshot))
                            .setNegativeButton("Bỏ phiên", (d, w) -> {
                                if (FlashcardSessionStore.clear(this, owner)) loadCards();
                                else Toast.makeText(this, "Không thể xóa phiên trên thiết bị.", Toast.LENGTH_LONG).show();
                            }).setNeutralButton("Để sau", (d, w) -> finish()).setOnCancelListener(d -> finish()).show();
                }
            } else { loading = false; loadCards(); }
        }, error -> { checkingIdentity = false; loading = false; updateUi(); Toast.makeText(this, error, Toast.LENGTH_LONG).show(); });
    }

    private void loadPracticeCards() {
        int filter = getIntent().getIntExtra("practice_filter", 1);
        FlashcardRepository.loadPracticeCards(this, filter, new FlashcardRepository.Callback<List<FlashcardRepository.FlashcardItem>>() {
            @Override public void onSuccess(List<FlashcardRepository.FlashcardItem> values) {
                cards.clear(); cards.addAll(values); index = reviewed = 0; front = true;
                model.cardIndex = model.reviewed = 0; model.front = true;
                cardsLoaded = model.loaded = true; loading = false; updateUi();
            }
            @Override public void onError(String message) {
                loading = false; updateUi(); Toast.makeText(FlashcardActivity.this, message, Toast.LENGTH_LONG).show();
            }
        });
    }

    private void restoreSession(org.json.JSONObject data) {
        try {
            org.json.JSONArray saved = data.getJSONArray("cards");
            if (saved.length() > 30 || data.optString("session_id").isEmpty()) throw new IllegalArgumentException();
            cards.clear(); model.completedIds.clear();
            for (int i = 0; i < saved.length(); i++) {
                FlashcardRepository.FlashcardItem item = new FlashcardRepository.FlashcardItem(saved.getJSONObject(i));
                java.util.UUID.fromString(item.savedId); cards.add(item);
            }
            org.json.JSONArray completed = data.optJSONArray("completed_ids");
            if (completed != null) for (int i = 0; i < completed.length(); i++) model.completedIds.add(completed.getString(i));
            model.sessionId = data.getString("session_id"); model.createdAt = data.getLong("created_at");
            model.snapshotStarted = true;
            model.reviewed = data.optInt("reviewed"); model.dueCount = data.optInt("due_count");
            model.goalRemaining = data.optInt("goal_remaining", model.dueCount);
            model.pendingId = data.optString("pending_id", null); model.pendingCard = data.optString("pending_card", null);
            model.pendingRating = data.optString("pending_rating", null);
            if (model.pendingId != null) {
                java.util.UUID.fromString(model.pendingId);
                if (model.pendingCard == null || model.pendingRating == null) throw new IllegalArgumentException();
            }
            index = Math.min(Math.max(0, data.optInt("index")), Math.max(0, cards.size()-1));
            front = data.optBoolean("front", true); model.cardIndex = index; model.front = front;
            final String currentId = cards.isEmpty() ? null : cards.get(index).savedId;
            loading = true; updateUi();
            FlashcardRepository.reconcile(this, cards, model.pendingCard, new FlashcardRepository.Callback<List<FlashcardRepository.FlashcardItem>>() {
                @Override public void onSuccess(List<FlashcardRepository.FlashcardItem> values) {
                    model.fixedIntervals = FlashcardRepository.lastFixedIntervals;
                    int removed = Math.max(0, cards.size() - values.size());
                    model.dueCount = Math.max(0, model.dueCount - removed);
                    cards.clear(); cards.addAll(values); index = 0;
                    String targetId = model.pendingCard != null ? model.pendingCard : currentId;
                    if (targetId != null) for (int i = 0; i < cards.size(); i++) if (targetId.equals(cards.get(i).savedId)) { index = i; break; }
                    model.cardIndex = index;
                    if (model.pendingCard != null) {
                        boolean found = false; for (FlashcardRepository.FlashcardItem v : cards) if (v.savedId.equals(model.pendingCard)) found = true;
                        if (!found) { loading = false; Toast.makeText(FlashcardActivity.this, "Thẻ đang đồng bộ không còn tồn tại.", Toast.LENGTH_LONG).show(); updateUi(); return; }
                    }
                    cardsLoaded = model.loaded = true; reviewed = model.reviewed; loading = false;
                    if (cards.isEmpty()) { FlashcardSessionStore.clearIfSame(FlashcardActivity.this, model); updateUi(); return; }
                    if (!model.persist()) { Toast.makeText(FlashcardActivity.this, "Không thể lưu phiên an toàn.", Toast.LENGTH_LONG).show(); updateUi(); return; }
                    updateUi();
                    if (model.pendingId != null) model.review(model.pendingCard, model.pendingRating);
                }
                @Override public void onError(String error) { loading = false; updateUi(); Toast.makeText(FlashcardActivity.this, error, Toast.LENGTH_LONG).show(); }
            });
        } catch (Exception e) { loading = false; Toast.makeText(this, "Không thể khôi phục phiên đã lưu.", Toast.LENGTH_LONG).show(); updateUi(); }
    }

    private void loadCards() {
        if (loading || ratingInFlight) return;
        FlashcardRepository.takeStudyDeck();
        if (BackendApi.token == null) { startActivity(new Intent(this, LoginActivity.class)); finish(); return; }
        loading = true; updateUi();
        FlashcardRepository.loadDueQueue(this, FlashcardRepository.DEFAULT_QUEUE_LIMIT,
                new FlashcardRepository.Callback<List<FlashcardRepository.FlashcardItem>>() {
            @Override public void onSuccess(List<FlashcardRepository.FlashcardItem> queue) {
                loading = false; cards.clear(); cards.addAll(queue); index = 0; reviewed = 0; front = true; cardsLoaded = true; model.loaded = true; model.reviewed = 0; model.dueCount = FlashcardRepository.lastDueCount; model.goalRemaining = FlashcardRepository.lastGoalRemaining; model.completedIds.clear(); model.sessionId = java.util.UUID.randomUUID().toString(); model.createdAt = System.currentTimeMillis(); model.cardIndex = 0; model.front = true; model.snapshotStarted = false; studyDeckMode = false;
                model.fixedIntervals = FlashcardRepository.lastFixedIntervals;
                if (!cards.isEmpty() && !model.persist()) { cardsLoaded = model.loaded = false; cards.clear(); Toast.makeText(FlashcardActivity.this, "Không thể lưu phiên an toàn.", Toast.LENGTH_LONG).show(); }
                updateUi();
            }
            @Override public void onError(String message) {
                loading = false; updateUi(); Toast.makeText(FlashcardActivity.this, message, Toast.LENGTH_LONG).show();
            }
        });
    }

    private void submitRating(String rating) {
        if (loading || ratingInFlight || cards.isEmpty()) return;
        if (studyDeckMode) {
            cards.remove(index); reviewed++; model.reviewed = reviewed;
            if (index >= cards.size()) index = 0;
            front = model.front = true; model.cardIndex = index; updateUi(); return;
        }
        FlashcardRepository.FlashcardItem current = cards.get(index);
        if (studyDeckMode && current.savedId.isEmpty()) {
            Toast.makeText(this, "Không thể đồng bộ thẻ này. Hãy tải lại danh sách từ vựng.", Toast.LENGTH_LONG).show();
            return;
        }
        model.review(current.savedId, rating);
    }

    private void onReviewChanged() {
        ratingInFlight = model.inFlight; reviewed = model.reviewed;
        if (model.authExpired) {
            model.authExpired = false; BackendApi.token = null; SessionManager.clear(this);
            Toast.makeText(this, "Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.", Toast.LENGTH_LONG).show();
            startActivity(new Intent(this, LoginActivity.class)); finish(); return;
        }
        if (model.conflict) {
            model.conflict = false;
            if (!cards.isEmpty() && index < cards.size()) { cards.remove(index); model.dueCount = Math.max(0, model.dueCount - 1); }
            model.pendingId = model.pendingCard = model.pendingRating = null;
            if (cards.isEmpty()) FlashcardSessionStore.clearIfSame(this, model); else model.persist();
        }
        if (index >= cards.size()) index = 0;
        if (model.success) { model.success = false; front = true; }
        if (model.message != null) { Toast.makeText(this, model.message, Toast.LENGTH_LONG).show(); model.message = null; }
        updateUi();
    }

    private void speakCurrentCard() { if (!cards.isEmpty() && tts != null) tts.speak(cards.get(index).word, TextToSpeech.QUEUE_FLUSH, null, null); }

    private void updateUi() {
        setRatingButtonsEnabled(!loading && !ratingInFlight && !cards.isEmpty());
        if (loading || cards.isEmpty()) {
            for (TextView interval : new TextView[]{hardInterval, goodInterval, easyInterval})
                if (interval != null) interval.setText("—");
        }
        if (loading) { setText(studyDeckMode ? "Đang tải từ vựng…" : "Đang tải thẻ đến hạn…", "", "Đồng bộ từ vựng của bạn", ""); if (progress != null) progress.setProgress(0); return; }
        if (cards.isEmpty()) {
            if (studyDeckMode) {
                setText("Đã hoàn thành lượt luyện tập", "Lịch ôn của bạn không thay đổi.", "", "Đã xem " + reviewed + " thẻ");
                if (progress != null) progress.setProgress(100); return;
            }
            if (model.goalRemaining > 0) setText("Còn thẻ cần ôn lại", "Còn " + model.goalRemaining + " thẻ trong mục tiêu hôm nay. Hãy quay lại khi thẻ đến hạn.", "Hoàn thành tất cả để giữ chuỗi học tập.", "Đã ôn " + reviewed + " thẻ");
            else if (model.dueCount > 0) setText("Đã hoàn thành phiên này", "Còn " + model.dueCount + " thẻ đến hạn. Hãy mở phiên mới để tiếp tục.", "", "Đã ôn " + reviewed + " thẻ");
            else setText("Bạn đã hoàn thành các flashcard đến hạn", "Bạn đã hoàn thành lượt ôn hiện tại.", "Chỉ thẻ đến hạn được tính vào chuỗi học tập.", reviewed > 0 ? "Đã ôn " + reviewed + " thẻ" : "0 / 0");
            if (progress != null) progress.setProgress(100); return;
        }
        FlashcardRepository.FlashcardItem current = cards.get(index);
        if (counter != null) counter.setText(studyDeckMode
                ? "Luyện tập · " + (reviewed + 1) + "/" + (reviewed + cards.size())
                : "Đến hạn " + model.dueCount + " · Phiên " + (reviewed + 1) + "/" + (reviewed + cards.size()));
        setIntervalPreview(hardInterval, current, "hard");
        setIntervalPreview(goodInterval, current, "good");
        setIntervalPreview(easyInterval, current, "easy");
        if (progress != null) progress.setProgress(reviewed * 100 / (reviewed + cards.size()));
        if (front) setText(current.word, current.phonetic, studyDeckMode ? "Chạm để xem nghĩa · Không đổi lịch ôn" : "Chạm vào thẻ để xem nghĩa", null);
        else setText(current.meaning, "", "Chạm vào thẻ để xem từ tiếng Anh", null);
    }

    private void setText(String main, String secondary, String instruction, String count) {
        if (word != null) word.setText(main); if (sub != null) sub.setText(secondary); if (hint != null) hint.setText(instruction); if (count != null && counter != null) counter.setText(count);
    }
    private void setIntervalPreview(TextView view, FlashcardRepository.FlashcardItem card, String rating) {
        if (view != null) view.setText((model.fixedIntervals
                ? FlashcardIntervalPreview.days(card.repetitions, card.intervalDays, card.easeFactor, rating)
                : FlashcardIntervalPreview.legacyDays(card.repetitions, card.intervalDays, card.easeFactor, rating)) + " ngày");
    }
    private void setRatingButtonsEnabled(boolean enabled) { for (View button : new View[]{btnAgain, btnHard, btnGood, btnEasy}) if (button != null) button.setEnabled(enabled); }
    private void bindNavigation() {
        View navHome = findViewById(R.id.nav_home); if (navHome != null) navHome.setOnClickListener(v -> startActivity(new Intent(this, HomeActivity.class)));
        View navVocabulary = findViewById(R.id.nav_vocabulary); if (navVocabulary != null) navVocabulary.setOnClickListener(v -> startActivity(new Intent(this, VocabularyActivity.class)));
        View navProgress = findViewById(R.id.nav_progress); if (navProgress != null) navProgress.setOnClickListener(v -> startActivity(new Intent(this, ProgressActivity.class)));
        View navProfile = findViewById(R.id.nav_profile); if (navProfile != null) navProfile.setOnClickListener(v -> startActivity(new Intent(this, ProfileActivity.class)));
    }
    @Override protected void onDestroy() { model.detach(reviewChanged); if (tts != null) { tts.stop(); tts.shutdown(); } super.onDestroy(); }
}
