package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.TextView;
import org.json.JSONObject;
import androidx.appcompat.app.AppCompatActivity;

public class ProgressActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_8_ti_n_h_c_t_p);

        // Bottom Navigation Bar Setup
        View navHome = findViewById(R.id.nav_home);
        if (navHome != null) {
            navHome.setOnClickListener(v -> startActivity(new Intent(ProgressActivity.this, HomeActivity.class)));
        }

        View navVocabulary = findViewById(R.id.nav_vocabulary);
        if (navVocabulary != null) {
            navVocabulary.setOnClickListener(v -> startActivity(new Intent(ProgressActivity.this, VocabularyActivity.class)));
        }

        View navFlashcard = findViewById(R.id.nav_flashcard);
        if (navFlashcard != null) {
            navFlashcard.setOnClickListener(v -> startActivity(new Intent(ProgressActivity.this, FlashcardActivity.class)));
        }

        View navProgress = findViewById(R.id.nav_progress);
        if (navProgress != null) {
            navProgress.setOnClickListener(v -> {
                // Already on Progress
            });
        }

        View navProfile = findViewById(R.id.nav_profile);
        if (navProfile != null) {
            navProfile.setOnClickListener(v -> startActivity(new Intent(ProgressActivity.this, ProfileActivity.class)));
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (BackendApi.token == null) BackendApi.token = SessionManager.load(this);
        if (BackendApi.token == null) return;
        BackendApi.run(this, () -> (JSONObject) BackendApi.send("/users/me/statistics", "GET", null, null, BackendApi.token), stats -> {
            ((TextView) findViewById(R.id.tv_stat_learned_words)).setText(String.valueOf(stats.optInt("learned_words")));
            ((TextView) findViewById(R.id.tv_stat_completed_videos)).setText(String.valueOf(stats.optInt("videos_completed")));
            ((TextView) findViewById(R.id.tv_stat_saved_words)).setText(String.valueOf(stats.optInt("saved_words")));
            ((TextView) findViewById(R.id.tv_stat_due_cards)).setText(String.valueOf(stats.optInt("due_flashcards")));
            ((TextView) findViewById(R.id.tv_progress_summary)).setText(
                    stats.optInt("videos_in_progress") + " video đang học · " + stats.optInt("total_reviews") + " lượt ôn");
        }, error -> ((TextView) findViewById(R.id.tv_progress_summary)).setText(error));
    }
}
