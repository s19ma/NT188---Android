package com.example.englishthroughvideo;

import android.os.Handler;
import android.os.Looper;
import androidx.lifecycle.ViewModel;
import android.content.Context;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Owns the session and request across Activity recreation. */
public class FlashcardReviewModel extends ViewModel {
    final ArrayList<FlashcardRepository.FlashcardItem> cards = new ArrayList<>();
    final ArrayList<String> completedIds = new ArrayList<>();
    boolean loaded, inFlight, snapshotStarted, fixedIntervals;
    int reviewed, dueCount, cardIndex, goalRemaining;
    boolean front = true;
    String ownerId, sessionId;
    long createdAt;
    private Context applicationContext;
    String pendingId, pendingRating, pendingCard, message;
    boolean conflict, success, authExpired;
    private Runnable listener;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService executor = Executors.newSingleThreadExecutor();

    void observe(Runnable callback) { listener = callback; }
    void detach(Runnable callback) { if (listener == callback) listener = null; }
    private void changed() { if (listener != null) listener.run(); }
    void bind(Context context, String owner) { applicationContext = context.getApplicationContext(); ownerId = owner; }
    boolean persist() { return applicationContext != null && FlashcardSessionStore.save(applicationContext, this); }

    void review(String card, String rating) {
        if (inFlight) return;
        if (pendingId == null) {
            pendingId = UUID.randomUUID().toString(); pendingCard = card; pendingRating = rating;
        }
        if (!card.equals(pendingCard) || !rating.equals(pendingRating)) {
            message = "Hãy thử lại đánh giá trước đó để đồng bộ."; changed(); return;
        }
        // Persist the original request before the first byte can leave the device.
        if (!persist()) { message = "Không thể lưu phiên an toàn. Hãy thử lại."; changed(); return; }
        inFlight = true; message = null; changed();
        final String id = pendingId, chosen = pendingRating, saved = pendingCard, token = BackendApi.token;
        executor.execute(() -> {
            try {
                JSONObject body = new JSONObject().put("rating", chosen).put("request_id", id);
                BackendApi.send("/users/me/flashcards/" + saved + "/review", "POST", "application/json", body.toString(), token);
                main.post(() -> {
                    inFlight = false;
                    for (int i = 0; i < cards.size(); i++) if (cards.get(i).savedId.equals(saved)) { cards.remove(i); completedIds.add(saved); reviewed++; dueCount = Math.max(0, dueCount - 1); break; }
                    if (!"again".equals(chosen)) goalRemaining = Math.max(0, goalRemaining - 1);
                    pendingId = pendingRating = pendingCard = null;
                    cardIndex = 0; front = true;
                    if (cards.isEmpty()) FlashcardSessionStore.clearIfSame(applicationContext, this); else persist();
                    message = null; success = true; changed();
                });
            } catch (Exception error) {
                main.post(() -> {
                    inFlight = false;
                    if (error instanceof BackendApi.ApiException && ((BackendApi.ApiException) error).status == 409
                            && ("Flashcard is not due for review".equals(error.getMessage())
                            || "Flashcard is not in today's remaining review goal".equals(error.getMessage()))) {
                        // Keep pending state durable until the Activity resolves the conflict.
                        conflict = true;
                        message = "Thẻ không còn trong danh sách ôn hôm nay; đang đồng bộ lại.";
                    } else if (error instanceof BackendApi.ApiException && ((BackendApi.ApiException) error).status == 401) {
                        authExpired = true; message = "Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.";
                    } else message = "Không thể lưu. Hãy thử lại cùng mức đánh giá.";
                    changed();
                });
            }
        });
    }
    @Override protected void onCleared() { listener = null; executor.shutdown(); }
}
