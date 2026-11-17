package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;

public class QuizDictationActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_17_quiz_dictation);

        View rootView = findViewById(android.R.id.content);
        if (rootView != null) {
            rootView.setOnClickListener(v -> {
                Toast.makeText(QuizDictationActivity.this, "Hoàn thành bài Quiz!", Toast.LENGTH_SHORT).show();
                Intent intent = new Intent(QuizDictationActivity.this, QuizResultActivity.class);
                startActivity(intent);
            });
        }
    }
}
