package com.example.englishthroughvideo;

import android.os.Bundle;
import android.view.View;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.app.AlertDialog;
import org.json.JSONObject;

public class VocabDetailActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_6_5_chi_ti_t_t_v_ng);

        View btnBack = findViewById(R.id.tv_back);
        if (btnBack != null) {
            btnBack.setOnClickListener(v -> finish());
        }

        TextView tvWord = findViewById(R.id.tv_detail_word);
        TextView tvLevel = findViewById(R.id.tv_detail_level);
        TextView tvPhonetic = findViewById(R.id.tv_detail_phonetic);
        TextView tvMeaning = findViewById(R.id.tv_detail_meaning);
        TextView tvExample = findViewById(R.id.tv_detail_example);
        TextView tvSynonyms = findViewById(R.id.tv_detail_synonyms);

        String word = getIntent().getStringExtra("VOCAB_WORD");
        String phonetic = getIntent().getStringExtra("VOCAB_PHONETIC");
        String level = getIntent().getStringExtra("VOCAB_LEVEL");
        String meaning = getIntent().getStringExtra("VOCAB_MEANING");
        String example = getIntent().getStringExtra("VOCAB_EXAMPLE");
        String synonyms = getIntent().getStringExtra("VOCAB_SYNONYMS");
        String savedId = getIntent().getStringExtra("VOCAB_SAVED_ID");

        if (word != null && tvWord != null) tvWord.setText(word);
        if (phonetic != null && tvPhonetic != null) tvPhonetic.setText(phonetic + "  ·  noun");
        if (level != null && tvLevel != null) tvLevel.setText("Trình độ: " + level);
        if (meaning != null && tvMeaning != null) tvMeaning.setText("Nghĩa: " + meaning);
        if (example != null && tvExample != null) tvExample.setText(example + "\nVí dụ minh họa trong ngữ cảnh video học tập.");
        if (synonyms != null && tvSynonyms != null) tvSynonyms.setText("• Đồng nghĩa: " + synonyms + "\n• Trái nghĩa: casual, informal");

        View btnEdit = findViewById(R.id.btn_edit);
        if (btnEdit != null) {
            btnEdit.setOnClickListener(v -> {
                if (savedId == null || BackendApi.token == null) return;
                String[] states = {"new", "learning", "learned"};
                new AlertDialog.Builder(this).setTitle("Trạng thái học")
                        .setItems(states, (dialog, which) -> BackendApi.run(this, () -> BackendApi.send(
                                "/users/me/vocabulary/" + savedId + "/status", "PATCH", "application/json",
                                new JSONObject().put("learning_status", states[which]).toString(), BackendApi.token), result ->
                                Toast.makeText(this, "Đã cập nhật trạng thái.", Toast.LENGTH_SHORT).show()))
                        .show();
            });
        }

        View btnDelete = findViewById(R.id.btn_delete);
        if (btnDelete != null) {
            btnDelete.setOnClickListener(v -> {
                if (savedId == null || BackendApi.token == null) return;
                BackendApi.run(this, () -> BackendApi.send("/users/me/vocabulary/" + savedId,
                        "DELETE", null, null, BackendApi.token), result -> finish());
            });
        }
    }
}
