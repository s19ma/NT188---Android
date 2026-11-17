package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import org.json.JSONArray;
import org.json.JSONObject;

public class SummaryActivity extends AppCompatActivity {
    private String videoTitle = "How to Speak Like a Native";
    private String videoId;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_4_3_t_m_t_t_video);

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
        loadSummary();

        View btnBack = findViewById(R.id.btn_back);
        if (btnBack != null) {
            btnBack.setOnClickListener(v -> finish());
        }

        TextView tabTranscript = findViewById(R.id.tab_transcript);
        TextView tabVocab = findViewById(R.id.tab_vocab);

        if (tabTranscript != null) {
            tabTranscript.setOnClickListener(v -> {
                Intent intent = new Intent(SummaryActivity.this, PlayerTranscriptActivity.class);
                intent.putExtra("VIDEO_TITLE", videoTitle);
                intent.putExtra("VIDEO_ID", videoId);
                startActivity(intent);
                finish();
            });
        }

        if (tabVocab != null) {
            tabVocab.setOnClickListener(v -> {
                Intent intent = new Intent(SummaryActivity.this, VideoVocabActivity.class);
                intent.putExtra("VIDEO_TITLE", videoTitle);
                intent.putExtra("VIDEO_ID", videoId);
                startActivity(intent);
                finish();
            });
        }
    }

    private void loadSummary() {
        if (videoId == null || BackendApi.token == null) return;
        BackendApi.run(this, () -> (JSONObject) BackendApi.send(
                "/videos/" + videoId + "/subtitles", "GET", null, null, BackendApi.token), response -> {
            JSONArray segments = response.optJSONArray("segments");
            if (segments == null || segments.length() == 0) return;
            setText(R.id.summary_topic, videoTitle);
            int[] picks = {0, segments.length() / 2, segments.length() - 1};
            int[] pointIds = {R.id.summary_point_1, R.id.summary_point_2, R.id.summary_point_3};
            int[] chapterIds = {R.id.summary_chapter_1, R.id.summary_chapter_2, R.id.summary_chapter_3};
            for (int i = 0; i < picks.length; i++) {
                JSONObject segment = segments.optJSONObject(picks[i]);
                if (segment == null) continue;
                String content = segment.optString("content").trim();
                setText(pointIds[i], "•  " + content);
                int seconds = segment.optInt("start_ms") / 1000;
                setText(chapterIds[i], String.format("%d:%02d  -  %s", seconds / 60, seconds % 60,
                        content.length() > 52 ? content.substring(0, 52) + "…" : content));
            }
        });
    }

    private void setText(int id, String value) {
        TextView view = findViewById(id);
        if (view != null) view.setText(value);
    }
}
