package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.graphics.Color;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class VideoVocabActivity extends AppCompatActivity {
    private String videoTitle = "How to Speak Like a Native";
    private String videoId;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_4_4_t_v_ng_trong_video);

        if (getIntent() != null && getIntent().hasExtra("VIDEO_TITLE")) {
            String passed = getIntent().getStringExtra("VIDEO_TITLE");
            if (passed != null && !passed.isEmpty()) {
                videoTitle = passed;
            }
        }
        videoId = getIntent().getStringExtra("VIDEO_ID");

        TextView tvTitle = findViewById(R.id.tv_player_video_title);
        if (tvTitle != null) {
            tvTitle.setText(videoTitle);
        }
        loadVideoVocabulary();

        View btnBack = findViewById(R.id.btn_back);
        if (btnBack != null) {
            btnBack.setOnClickListener(v -> finish());
        }

        TextView tabTranscript = findViewById(R.id.tab_transcript);
        TextView tabSummary = findViewById(R.id.tab_summary);

        if (tabTranscript != null) {
            tabTranscript.setOnClickListener(v -> {
                Intent intent = new Intent(VideoVocabActivity.this, PlayerTranscriptActivity.class);
                intent.putExtra("VIDEO_TITLE", videoTitle);
                intent.putExtra("VIDEO_ID", videoId);
                startActivity(intent);
                finish();
            });
        }

        if (tabSummary != null) {
            tabSummary.setOnClickListener(v -> {
                Intent intent = new Intent(VideoVocabActivity.this, SummaryActivity.class);
                intent.putExtra("VIDEO_TITLE", videoTitle);
                intent.putExtra("VIDEO_ID", videoId);
                startActivity(intent);
                finish();
            });
        }
    }

    private void loadVideoVocabulary() {
        if (videoId == null || BackendApi.token == null) return;
        LinearLayout list = findViewById(R.id.video_vocab_list);
        if (list == null) return;
        TextView status = new TextView(this);
        status.setText("Đang tải từ vựng…");
        list.addView(status);
        BackendApi.run(this, () -> (JSONArray) BackendApi.send(
                "/videos/" + videoId + "/vocabulary?limit=30", "GET", null, null, BackendApi.token), words -> {
            list.removeAllViews();
            if (words.length() == 0) {
                status.setText("Chưa có từ vựng cho video này.");
                list.addView(status);
            }
            for (int i = 0; i < words.length(); i++) {
                JSONObject item = words.optJSONObject(i);
                if (item == null) continue;
                String word = item.optString("lemma");
                String phonetic = item.isNull("phonetic") ? "" : item.optString("phonetic", "");
                String part = item.isNull("part_of_speech") ? "" : item.optString("part_of_speech", "");
                String meaning = item.isNull("definition") ? "Chưa có định nghĩa" : item.optString("definition", "");
                TextView row = new TextView(this);
                row.setText("• " + word + "  " + phonetic + "\n  " + part + " — " + meaning);
                row.setTextSize(13);
                row.setTextColor(Color.parseColor("#334155"));
                int padding = Math.round(8 * getResources().getDisplayMetrics().density);
                row.setPadding(0, 0, 0, padding);
                row.setOnClickListener(v -> {
                    Intent popup = new Intent(this, DictionaryPopupActivity.class);
                    popup.putExtra("CLICKED_WORD", word);
                    popup.putExtra("CLICKED_SENTENCE", "Từ xuất hiện trong video: " + videoTitle);
                    popup.putExtra("VIDEO_ID", videoId);
                    startActivity(popup);
                });
                list.addView(row);
            }
        }, error -> status.setText(error));
    }
}
