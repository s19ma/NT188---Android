package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import androidx.appcompat.app.AppCompatActivity;

public class SpacedRepetitionActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_31_l_ch_n_t_p_spaced_repetition);

        View rootView = findViewById(android.R.id.content);
        if (rootView != null) {
            rootView.setOnClickListener(v -> {
                Intent intent = new Intent(SpacedRepetitionActivity.this, FlashcardActivity.class);
                startActivity(intent);
            });
        }
    }
}
