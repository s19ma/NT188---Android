package com.example.englishthroughvideo;

import android.os.Bundle;
import android.content.Intent;
import android.widget.EditText;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.app.AlertDialog;
import org.json.JSONArray;
import org.json.JSONObject;

public class QuizActivity extends AppCompatActivity {
    private JSONArray questions;
    private final JSONObject answers = new JSONObject();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_7_quiz);

        if (BackendApi.token == null) {
            Toast.makeText(this, "Hãy đăng nhập trước khi làm quiz.", Toast.LENGTH_LONG).show();
            finish();
            return;
        }
        BackendApi.run(this, () -> (JSONObject) BackendApi.send("/quizzes/default", "GET", null,
                null, BackendApi.token), result -> {
            questions = result.optJSONArray("questions");
            if (questions == null || questions.length() == 0) {
                Toast.makeText(this, "Không có câu hỏi quiz.", Toast.LENGTH_LONG).show();
                return;
            }
            askQuestion(0);
        });
    }

    private void askQuestion(int index) {
        if (index >= questions.length()) {
            submitQuiz();
            return;
        }
        JSONObject question = questions.optJSONObject(index);
        if (question == null) return;
        String id = question.optString("id");
        String prompt = "Câu " + (index + 1) + "/" + questions.length() + "\n\n" + question.optString("prompt");
        JSONArray options = question.optJSONArray("options");
        if (options != null && options.length() > 0) {
            String[] labels = new String[options.length()];
            for (int i = 0; i < options.length(); i++) labels[i] = options.optString(i);
            new AlertDialog.Builder(this).setTitle("Quiz").setMessage(prompt)
                    .setSingleChoiceItems(labels, -1, (dialog, which) -> {
                        try { answers.put(id, labels[which]); } catch (Exception ignored) {}
                        dialog.dismiss();
                        askQuestion(index + 1);
                    }).setNegativeButton("Hủy", (dialog, which) -> finish()).show();
        } else {
            EditText input = new EditText(this);
            input.setHint("Nhập câu trả lời");
            new AlertDialog.Builder(this).setTitle("Quiz").setMessage(prompt).setView(input)
                    .setNegativeButton("Hủy", (dialog, which) -> finish())
                    .setPositiveButton("Tiếp", (dialog, which) -> {
                        try { answers.put(id, input.getText().toString()); } catch (Exception ignored) {}
                        askQuestion(index + 1);
                    }).show();
        }
    }

    private void submitQuiz() {
        BackendApi.run(this, () -> (JSONObject) BackendApi.send("/quizzes/default/submit", "POST",
                "application/json", new JSONObject().put("answers", answers).toString(), BackendApi.token), result -> {
            Intent intent = new Intent(this, QuizResultActivity.class);
            intent.putExtra("SCORE", result.optInt("score"));
            intent.putExtra("TOTAL", result.optInt("total_questions"));
            startActivity(intent);
            finish();
        });
    }
}
