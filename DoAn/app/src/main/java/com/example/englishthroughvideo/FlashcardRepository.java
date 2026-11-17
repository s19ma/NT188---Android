package com.example.englishthroughvideo;

import android.app.Activity;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.List;
import java.util.HashMap;
import java.util.Map;

/** Client for the spaced-repetition flashcard endpoints. */
public final class FlashcardRepository {
    public static final int DEFAULT_QUEUE_LIMIT = 30;
    public static volatile int lastDueCount;
    public static volatile int lastGoalRemaining;
    public static volatile boolean lastFixedIntervals;
    private static final List<FlashcardItem> studyDeck = new ArrayList<>();

    public interface Callback<T> { void onSuccess(T value); void onError(String message); }

    /** Mirrors UserVocabularyResponse, including its nested VocabularyResponse. */
    public static final class FlashcardItem implements java.io.Serializable {
        private static final long serialVersionUID = 1L;
        public final String savedId, vocabularyId, word, phonetic, meaning, context, learningStatus;
        public final double easeFactor;
        public final int intervalDays, repetitions, reviewCount;
        public final String nextReviewAt, lastReviewedAt;

        FlashcardItem(JSONObject saved) {
            JSONObject vocabulary = saved.optJSONObject("vocabulary");
            if (vocabulary == null) vocabulary = new JSONObject();
            savedId = saved.optString("id");
            vocabularyId = saved.optString("vocabulary_id");
            word = vocabulary.optString("lemma");
            phonetic = vocabulary.isNull("phonetic") ? "" : vocabulary.optString("phonetic", "");
            meaning = vocabulary.isNull("definition") ? "" : vocabulary.optString("definition", "");
            context = saved.isNull("context_sentence") ? "" : saved.optString("context_sentence", "");
            learningStatus = saved.optString("learning_status", "new");
            easeFactor = saved.optDouble("ease_factor", 2.5d);
            intervalDays = saved.optInt("interval_days", 0);
            repetitions = saved.optInt("repetitions", 0);
            reviewCount = saved.optInt("review_count", 0);
            nextReviewAt = saved.optString("next_review_at", null);
            lastReviewedAt = saved.optString("last_reviewed_at", null);
        }

        private FlashcardItem(VocabularyRepository.VocabItem item) {
            savedId = item.savedId == null ? "" : item.savedId;
            vocabularyId = item.vocabularyId == null ? "" : item.vocabularyId;
            word = item.word == null ? "" : item.word;
            phonetic = item.phonetic == null ? "" : item.phonetic;
            meaning = item.meaning == null ? "" : item.meaning;
            context = item.example == null ? "" : item.example;
            learningStatus = item.learningStatus == null ? "new" : item.learningStatus;
            easeFactor = 2.5d;
            intervalDays = repetitions = reviewCount = 0;
            nextReviewAt = lastReviewedAt = null;
        }

        JSONObject toJson() throws Exception {
            JSONObject vocabulary = new JSONObject().put("id", vocabularyId).put("lemma", word)
                    .put("phonetic", phonetic).put("definition", meaning);
            return new JSONObject().put("id", savedId).put("vocabulary_id", vocabularyId)
                    .put("vocabulary", vocabulary).put("context_sentence", context)
                    .put("learning_status", learningStatus).put("ease_factor", easeFactor)
                    .put("interval_days", intervalDays).put("repetitions", repetitions)
                    .put("review_count", reviewCount).put("next_review_at", nextReviewAt)
                    .put("last_reviewed_at", lastReviewedAt);
        }
    }

    private FlashcardRepository() { }

    /** Read all saved cards, including cards scheduled for a later review. */
    public static void loadPracticeCards(Activity activity, int filter, Callback<List<FlashcardItem>> callback) {
        final String token = BackendApi.token;
        BackendApi.run(activity, () -> {
            List<FlashcardItem> result = new ArrayList<>();
            for (int skip = 0; ; skip += 100) {
                JSONArray page = (JSONArray) BackendApi.send("/users/me/vocabulary?skip=" + skip + "&limit=100", "GET", null, null, token);
                for (int i = 0; i < page.length(); i++) {
                    FlashcardItem item = new FlashcardItem(page.getJSONObject(i));
                    boolean learned = "learned".equals(item.learningStatus);
                    if ((filter == 2 && learned) || (filter == 3 && !learned)) continue;
                    result.add(item);
                }
                if (page.length() < 100) break;
            }
            return result;
        }, callback::onSuccess, callback::onError);
    }

    /**
     * Stages the exact filtered vocabulary list selected from the Vocabulary screen.
     * This is separate from the server's due queue so “study all” always has cards to flip.
     */
    public static void startStudyDeck(List<VocabularyRepository.VocabItem> vocabulary) {
        studyDeck.clear();
        for (VocabularyRepository.VocabItem item : vocabulary) {
            if (item != null && item.word != null && !item.word.trim().isEmpty()) studyDeck.add(new FlashcardItem(item));
        }
    }

    /** Returns the staged deck once, preventing a later normal Flashcard entry from reusing it. */
    public static List<FlashcardItem> takeStudyDeck() {
        List<FlashcardItem> result = new ArrayList<>(studyDeck);
        studyDeck.clear();
        return result;
    }

    /** Loads cards due now, in the backend scheduler's ordering. */
    public static void loadDueQueue(Activity activity, int limit, Callback<List<FlashcardItem>> callback) {
        if (BackendApi.token == null) { callback.onError("Hãy đăng nhập để ôn flashcard."); return; }
        int safeLimit = Math.max(1, Math.min(limit, 30));
        BackendApi.run(activity, () -> {
            JSONObject overview = (JSONObject) BackendApi.send("/users/me/flashcards/overview", "GET", null, null, BackendApi.token);
            if (!overview.optBoolean("idempotent_review_supported", false))
                throw new BackendApi.ApiException(0, "Máy chủ chưa hỗ trợ ôn tập an toàn. Vui lòng thử lại sau khi cập nhật máy chủ.");
            lastDueCount = overview.optInt("due", 0);
            lastGoalRemaining = overview.optInt("daily_goal_remaining", lastDueCount);
            lastFixedIntervals = overview.optBoolean("fixed_review_intervals", false);
            JSONArray response = (JSONArray) BackendApi.send("/users/me/flashcards?due_only=true&limit=" + safeLimit,
                    "GET", null, null, BackendApi.token);
            List<FlashcardItem> cards = new ArrayList<>();
            for (int index = 0; index < response.length(); index++) {
                JSONObject item = response.optJSONObject(index);
                if (item != null && !item.optString("id").isEmpty()) cards.add(new FlashcardItem(item));
            }
            return cards;
        }, callback::onSuccess, callback::onError);
    }

    /** Revalidate only the original IDs, without replacing them with new due cards. */
    public static void reconcile(Activity activity, List<FlashcardItem> original, String pendingId,
                                 Callback<List<FlashcardItem>> callback) {
        final List<FlashcardItem> snapshot = new ArrayList<>(original);
        final String token = BackendApi.token;
        BackendApi.run(activity, () -> {
            JSONObject overview = (JSONObject) BackendApi.send("/users/me/flashcards/overview", "GET", null, null, token);
            lastFixedIntervals = overview.optBoolean("fixed_review_intervals", false);
            JSONArray dueRows = (JSONArray) BackendApi.send("/users/me/flashcards?due_only=true&limit=30", "GET", null, null, token);
            java.util.Set<String> eligible = new java.util.HashSet<>();
            for (int i = 0; i < dueRows.length(); i++) eligible.add(dueRows.getJSONObject(i).getString("id"));
            Map<String, FlashcardItem> current = new HashMap<>();
            for (int skip = 0; ; skip += 100) {
                JSONArray page = (JSONArray) BackendApi.send("/users/me/vocabulary?limit=100&skip=" + skip, "GET", null, null, token);
                for (int i = 0; i < page.length(); i++) {
                    JSONObject row = page.optJSONObject(i);
                    if (row != null) { FlashcardItem item = new FlashcardItem(row); current.put(item.savedId, item); }
                }
                if (page.length() < 100) break;
            }
            List<FlashcardItem> remaining = new ArrayList<>();
            for (FlashcardItem old : snapshot) {
                FlashcardItem item = current.get(old.savedId);
                if (item == null) continue;
                if (eligible.contains(item.savedId) || item.savedId.equals(pendingId)) remaining.add(item);
            }
            return remaining;
        }, callback::onSuccess, callback::onError);
    }

    static java.util.Date parseReviewTime(String value) throws Exception {
        if (value == null || !value.matches(".*(Z|[+-][0-9]{2}:[0-9]{2})$"))
            throw new IllegalArgumentException("Review time lacks UTC offset");
        String normalized = value.replaceFirst("\\.[0-9]+(?=Z|[+-][0-9]{2}:[0-9]{2}$)", "");
        java.text.SimpleDateFormat parser = new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", java.util.Locale.US);
        parser.setLenient(false);
        return parser.parse(normalized);
    }

    /** Sends the exact ReviewVocabularyRequest JSON: {"rating":"again|hard|good|easy"}. */
    public static void rate(Activity activity, String savedId, String rating, Callback<FlashcardItem> callback) {
        if (savedId == null || savedId.isEmpty()) { callback.onError("Flashcard không có mã lưu hợp lệ."); return; }
        if (!isRating(rating)) { callback.onError("Mức đánh giá flashcard không hợp lệ."); return; }
        BackendApi.run(activity, () -> {
            JSONObject response = (JSONObject) BackendApi.send("/users/me/flashcards/" + savedId + "/review",
                    "POST", "application/json", new JSONObject().put("rating", rating).toString(), BackendApi.token);
            return new FlashcardItem(response);
        }, callback::onSuccess, callback::onError);
    }

    public static void delete(Activity activity, String savedId, Callback<Void> callback) {
        BackendApi.run(activity, () -> {
            BackendApi.send("/users/me/vocabulary/" + savedId, "DELETE", null, null, BackendApi.token);
            return null;
        }, ignored -> callback.onSuccess(null), callback::onError);
    }

    private static boolean isRating(String rating) {
        return "again".equals(rating) || "hard".equals(rating) || "good".equals(rating) || "easy".equals(rating);
    }
}
