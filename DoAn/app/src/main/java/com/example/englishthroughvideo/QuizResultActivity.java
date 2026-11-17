package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;

public class QuizResultActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_19_k_t_qu_quiz);
        int score = getIntent().getIntExtra("SCORE", -1);
        int total = getIntent().getIntExtra("TOTAL", -1);
        if (score >= 0 && total > 0) {
            Toast.makeText(this, "Kết quả: " + score + "/" + total, Toast.LENGTH_LONG).show();
        }

        View rootView = findViewById(android.R.id.content);
        if (rootView != null) {
            rootView.setOnClickListener(v -> {
                Toast.makeText(QuizResultActivity.this, "Trở về trang chủ", Toast.LENGTH_SHORT).show();
                Intent intent = new Intent(QuizResultActivity.this, HomeActivity.class);
                intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
                startActivity(intent);
            });
        }
    }
}
