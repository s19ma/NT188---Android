package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;

public class QuizFillActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_16_quiz_i_n_t);

        View rootView = findViewById(android.R.id.content);
        if (rootView != null) {
            rootView.setOnClickListener(v -> {
                Toast.makeText(QuizFillActivity.this, "Câu 2: Đáp án 'changes' chính xác!", Toast.LENGTH_SHORT).show();
                Intent intent = new Intent(QuizFillActivity.this, QuizDictationActivity.class);
                startActivity(intent);
            });
        }
    }
}
