package com.example.englishthroughvideo;

import android.content.Context;
import org.json.JSONArray;
import org.json.JSONObject;

/** Encrypted local snapshot; never stores JWT, password, OTP, or Activity references. */
final class FlashcardSessionStore {
    private static final String KEY = "flashcard_session_v1_";
    private FlashcardSessionStore() { }

    static JSONObject read(Context context, String owner) {
        try {
            String value = SessionManager.preferences(context).getString(KEY + owner, null);
            return value == null ? null : new JSONObject(value);
        } catch (Exception e) { return null; }
    }

    static boolean save(Context context, FlashcardReviewModel m) {
        if (m.ownerId == null || !m.loaded) return false;
        try {
            if (m.snapshotStarted) {
                JSONObject existing = read(context, m.ownerId);
                if (existing == null || !m.sessionId.equals(existing.optString("session_id"))
                        || !m.ownerId.equals(existing.optString("owner"))) return false;
            }
            JSONArray cards = new JSONArray(), completed = new JSONArray();
            for (FlashcardRepository.FlashcardItem item : m.cards) cards.put(item.toJson());
            for (String id : m.completedIds) completed.put(id);
            JSONObject data = new JSONObject().put("version", 1).put("owner", m.ownerId)
                    .put("session_id", m.sessionId).put("created_at", m.createdAt)
                    .put("updated_at", System.currentTimeMillis()).put("cards", cards)
                    .put("completed_ids", completed).put("reviewed", m.reviewed).put("goal_remaining", m.goalRemaining)
                    .put("due_count", m.dueCount).put("index", m.cardIndex).put("front", m.front)
                    .put("pending_id", m.pendingId).put("pending_card", m.pendingCard)
                    .put("pending_rating", m.pendingRating).put("pending_state", m.pendingId == null ? "none" : "unknown");
            boolean saved = SessionManager.preferences(context).edit().putString(KEY + m.ownerId, data.toString()).commit();
            if (saved) m.snapshotStarted = true;
            return saved;
        } catch (Exception e) { return false; }
    }

    static boolean clear(Context context, String owner) {
        try { return SessionManager.preferences(context).edit().remove(KEY + owner).commit(); }
        catch (Exception e) { return false; }
    }

    static boolean clearIfSame(Context context, FlashcardReviewModel model) {
        JSONObject existing = read(context, model.ownerId);
        if (existing == null || !existing.optString("session_id").equals(model.sessionId)
                || !existing.optString("owner").equals(model.ownerId)) return false;
        return clear(context, model.ownerId);
    }
}
