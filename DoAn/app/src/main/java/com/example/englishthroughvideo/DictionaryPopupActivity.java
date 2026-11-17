package com.example.englishthroughvideo;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.tts.TextToSpeech;
import android.view.View;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Locale;

public class DictionaryPopupActivity extends AppCompatActivity {

    private TextToSpeech tts;
    private TextView tvWord, tvPhonetic, tvMeaning, tvSentence, tvRelated;
    private Handler mainHandler;
    private boolean saveInFlight;
    private String vocabularyId;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_4_2_tra_t);

        tvWord = findViewById(R.id.tv_popup_word);
        tvPhonetic = findViewById(R.id.tv_popup_phonetic);
        tvMeaning = findViewById(R.id.tv_popup_meaning);
        tvSentence = findViewById(R.id.tv_popup_sentence);
        tvRelated = findViewById(R.id.tv_popup_related);
        mainHandler = new Handler(Looper.getMainLooper());
        View backToVideo = findViewById(R.id.btn_popup_back);
        if (backToVideo != null) backToVideo.setOnClickListener(v -> finish());

        String word = getIntent().getStringExtra("CLICKED_WORD");
        String sentence = getIntent().getStringExtra("CLICKED_SENTENCE");

        if (word == null || word.trim().isEmpty()) {
            word = "resilient";
        }
        if (sentence == null) {
            sentence = "We need to be resilient in tough times.";
        }

        if (tvWord != null) tvWord.setText(word);
        if (tvSentence != null) tvSentence.setText(sentence);

        // Use the project backend vocabulary database, not an unrelated public dictionary or local fallback.
        fetchVocabularyFromBackend(word);

        tts = new TextToSpeech(this, status -> {
            if (status == TextToSpeech.SUCCESS) tts.setLanguage(Locale.US);
        });

        // Click Save to Flashcard & Dictionary button
        View btnSaveVocab = findViewById(R.id.btn_save_vocab);
        if (btnSaveVocab != null) {
            btnSaveVocab.setOnClickListener(v -> {
                String wordToSave = tvWord != null ? tvWord.getText().toString() : "word";
                if (BackendApi.token == null) {
                    Toast.makeText(this, "Hãy đăng nhập để lưu từ.", Toast.LENGTH_LONG).show();
                    return;
                }
                if (saveInFlight) return;
                saveInFlight = true;
                BackendApi.run(this, () -> {
                    if (vocabularyId == null || vocabularyId.isEmpty()) {
                        throw new BackendApi.ApiException(409, "Hãy chờ tra từ xong trước khi lưu.");
                    }
                    JSONObject payload = new JSONObject().put("context_sentence", getIntent().getStringExtra("CLICKED_SENTENCE"));
                    String videoId = getIntent().getStringExtra("VIDEO_ID");
                    if (videoId != null && !videoId.isEmpty()) payload.put("video_id", videoId);
                    long segmentId = getIntent().getLongExtra("TRANSCRIPT_SEGMENT_ID", -1);
                    if (segmentId > 0) payload.put("transcript_segment_id", segmentId);
                    return BackendApi.send("/vocabulary/" + vocabularyId + "/save", "POST", "application/json",
                            payload.toString(), BackendApi.token);
                }, result -> {
                    Toast.makeText(this, "Đã lưu từ vào danh sách ôn tập.", Toast.LENGTH_SHORT).show();
                    finish();
                }, error -> {
                    saveInFlight = false;
                    Toast.makeText(this, error, Toast.LENGTH_LONG).show();
                });
            });
        }
    }

    private void fetchVocabularyFromBackend(String word) {
        vocabularyId = null;
        if (tvPhonetic != null) tvPhonetic.setText("Đang tra từ điển…");
        if (tvMeaning != null) tvMeaning.setText("Đang tải định nghĩa…");
        if (tvRelated != null) tvRelated.setText("Đang tải…");
        View save = findViewById(R.id.btn_save_vocab);
        if (save != null) save.setEnabled(false);
        BackendApi.run(this, () -> (JSONObject) BackendApi.send("/dictionary/"
                + java.net.URLEncoder.encode(word.trim(), "UTF-8"), "GET", null, null, null), item -> {
            vocabularyId = item.optString("vocabulary_id");
            if (tvWord != null) tvWord.setText(item.optString("word", word));
            if (tvPhonetic != null) tvPhonetic.setText(item.optString("phonetic") + "  ·  " + item.optString("part_of_speech"));
            String definition = item.isNull("english_definition") ? "Chưa có định nghĩa." : item.optString("english_definition");
            String example = item.isNull("example") ? "" : item.optString("example");
            if (tvMeaning != null) tvMeaning.setText(definition + (example.isEmpty() ? "" : "\nVí dụ: " + example));
            if (tvRelated != null) {
                String synonyms = joinWords(item.optJSONArray("synonyms"));
                String antonyms = joinWords(item.optJSONArray("antonyms"));
                tvRelated.setText((synonyms.isEmpty() ? "Không có đồng nghĩa" : synonyms)
                        + "  /  " + (antonyms.isEmpty() ? "Không có trái nghĩa" : antonyms));
            }
            if (save != null) save.setEnabled(true);
        }, error -> {
            if (tvPhonetic != null) tvPhonetic.setText("Không có phát âm từ nguồn hiện tại.");
            if (tvMeaning != null) tvMeaning.setText("Không tìm thấy nghĩa cho từ này trong từ điển.");
            if (tvRelated != null) tvRelated.setText("Không có dữ liệu đồng nghĩa / trái nghĩa.");
        });
    }

    private String joinWords(JSONArray words) {
        if (words == null || words.length() == 0) return "";
        StringBuilder result = new StringBuilder();
        for (int i = 0; i < words.length(); i++) {
            String word = words.optString(i);
            if (word.isEmpty()) continue;
            if (result.length() > 0) result.append(", ");
            result.append(word);
        }
        return result.toString();
    }

    @Override
    protected void onDestroy() {
        if (tts != null) {
            tts.stop();
            tts.shutdown();
        }
        super.onDestroy();
    }
}
