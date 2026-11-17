package com.example.englishthroughvideo;

import android.app.Activity;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.List;

public final class VocabularyRepository {
    public static class VocabItem {
        public String savedId, vocabularyId, word, phonetic, pos, level, meaning, example, synonyms, learningStatus;
        public boolean isMastered() { return "learned".equals(learningStatus); }
        public static VocabItem fromSavedResponse(JSONObject row) throws Exception {
            JSONObject vocabulary = row.getJSONObject("vocabulary");
            VocabItem item = new VocabItem();
            item.savedId = row.getString("id");
            item.vocabularyId = row.getString("vocabulary_id");
            item.word = vocabulary.getString("lemma");
            item.phonetic = text(vocabulary, "phonetic");
            item.pos = text(vocabulary, "part_of_speech");
            item.meaning = text(vocabulary, "definition");
            item.example = text(row, "context_sentence");
            item.level = "";
            item.synonyms = "";
            item.learningStatus = row.optString("learning_status", "new");
            return item;
        }
        private static String text(JSONObject object, String key) {
            return object.isNull(key) ? "" : object.optString(key, "");
        }
    }

    private VocabularyRepository() { }
    public static void load(Activity activity, String token, FlashcardRepository.Callback<List<VocabItem>> callback) {
        BackendApi.run(activity, () -> {
            List<VocabItem> result = new ArrayList<>();
            for (int skip = 0; ; skip += 100) {
                JSONArray rows = (JSONArray) BackendApi.send("/users/me/vocabulary?skip=" + skip + "&limit=100", "GET", null, null, token);
                for (int i = 0; i < rows.length(); i++) result.add(VocabItem.fromSavedResponse(rows.getJSONObject(i)));
                if (rows.length() < 100) break;
            }
            return result;
        }, callback::onSuccess, callback::onError);
    }
}
