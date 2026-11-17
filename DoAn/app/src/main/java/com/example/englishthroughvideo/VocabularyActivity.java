package com.example.englishthroughvideo;

import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import java.util.ArrayList;
import java.util.List;

public class VocabularyActivity extends AppCompatActivity {

    private TextView tabVocabAll, tabVocabLearning, tabVocabMastered, tvStudyBtnText;
    private View btnStudyAll;
    private LinearLayout containerVocabList;
    private final List<VocabularyRepository.VocabItem> vocabList = new ArrayList<>();
    private int loadVersion;
    private int currentFilter = 1; // 1: All, 2: Learning, 3: Mastered

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_6_vocabulary);

        tabVocabAll = findViewById(R.id.tab_vocab_all);
        tabVocabLearning = findViewById(R.id.tab_vocab_learning);
        tabVocabMastered = findViewById(R.id.tab_vocab_mastered);
        containerVocabList = findViewById(R.id.container_vocab_list);
        btnStudyAll = findViewById(R.id.btn_study_flashcard_all);

        if (btnStudyAll instanceof LinearLayout) {
            View child = ((LinearLayout) btnStudyAll).getChildAt(0);
            if (child instanceof TextView) {
                tvStudyBtnText = (TextView) child;
            }
        }

        if (tabVocabAll != null) {
            tabVocabAll.setText("Tất cả (" + vocabList.size() + ")");
            tabVocabAll.setOnClickListener(v -> selectVocabTab(1));
        }
        if (tabVocabLearning != null) tabVocabLearning.setOnClickListener(v -> selectVocabTab(2));
        if (tabVocabMastered != null) tabVocabMastered.setOnClickListener(v -> selectVocabTab(3));

        if (btnStudyAll != null) {
            btnStudyAll.setOnClickListener(v -> {
                List<VocabularyRepository.VocabItem> selected = new ArrayList<>();
                for (VocabularyRepository.VocabItem item : vocabList) {
                    if (currentFilter == 2 && item.isMastered()) continue;
                    if (currentFilter == 3 && !item.isMastered()) continue;
                    selected.add(item);
                }
                if (selected.isEmpty()) {
                    Toast.makeText(this, "Không có từ vựng trong mục này.", Toast.LENGTH_SHORT).show();
                    return;
                }
                Intent intent = new Intent(VocabularyActivity.this, FlashcardActivity.class);
                intent.putExtra("practice_filter", currentFilter);
                startActivity(intent);
            });
        }

        renderVocabList();

        // Bottom Navigation Bar Tabs
        View navHome = findViewById(R.id.nav_home);
        if (navHome != null) navHome.setOnClickListener(v -> startActivity(new Intent(VocabularyActivity.this, HomeActivity.class)));

        View navFlashcard = findViewById(R.id.nav_flashcard);
        if (navFlashcard != null) navFlashcard.setOnClickListener(v -> startActivity(new Intent(VocabularyActivity.this, FlashcardActivity.class)));

        View navProgress = findViewById(R.id.nav_progress);
        if (navProgress != null) navProgress.setOnClickListener(v -> startActivity(new Intent(VocabularyActivity.this, ProgressActivity.class)));

        View navProfile = findViewById(R.id.nav_profile);
        if (navProfile != null) navProfile.setOnClickListener(v -> startActivity(new Intent(VocabularyActivity.this, ProfileActivity.class)));
    }

    @Override protected void onResume() {
        super.onResume();
        if (BackendApi.token == null) BackendApi.token = SessionManager.load(this);
        if (BackendApi.token == null) { startActivity(new Intent(this, LoginActivity.class)); finish(); return; }
        final int version = ++loadVersion;
        btnStudyAll.setEnabled(false);
        VocabularyRepository.load(this, BackendApi.token, new FlashcardRepository.Callback<List<VocabularyRepository.VocabItem>>() {
            @Override public void onSuccess(List<VocabularyRepository.VocabItem> items) {
                if (version != loadVersion) return;
                vocabList.clear(); vocabList.addAll(items);
                int learned = 0;
                for (VocabularyRepository.VocabItem item : items) if (item.isMastered()) learned++;
                tabVocabAll.setText("Tất cả (" + items.size() + ")");
                tabVocabLearning.setText("Đang học (" + (items.size() - learned) + ")");
                tabVocabMastered.setText("Đã thuộc (" + learned + ")");
                btnStudyAll.setEnabled(true);
                renderVocabList();
            }
            @Override public void onError(String message) {
                if (version != loadVersion) return;
                vocabList.clear(); renderVocabList();
                Toast.makeText(VocabularyActivity.this, message, Toast.LENGTH_LONG).show();
            }
        });
    }

    private void renderVocabList() {
        if (containerVocabList == null) return;
        containerVocabList.removeAllViews();
        boolean landscape = getResources().getConfiguration().orientation == android.content.res.Configuration.ORIENTATION_LANDSCAPE;
        LinearLayout row = null;
        int displayed = 0;

        for (VocabularyRepository.VocabItem item : vocabList) {
            if (currentFilter == 2 && item.isMastered()) continue;
            if (currentFilter == 3 && !item.isMastered()) continue;

            // Create Card Container
            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.VERTICAL);
            LinearLayout.LayoutParams cardParams = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
            );
            cardParams.setMargins(0, 0, 0, 16);
            card.setLayoutParams(cardParams);
            card.setBackgroundResource(R.drawable.bg_card_white);
            card.setPadding(40, 40, 40, 40);
            card.setClickable(true);
            card.setFocusable(true);

            // Top Row: Word & Status
            LinearLayout topRow = new LinearLayout(this);
            topRow.setOrientation(LinearLayout.HORIZONTAL);
            topRow.setLayoutParams(new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
            ));
            topRow.setGravity(Gravity.CENTER_VERTICAL);

            TextView tvWord = new TextView(this);
            tvWord.setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
            tvWord.setText(item.word);
            tvWord.setTextSize(20f);
            tvWord.setTextColor(Color.parseColor("#FF0F172A"));
            tvWord.setTypeface(null, android.graphics.Typeface.BOLD);

            TextView tvStatus = new TextView(this);
            tvStatus.setText(item.isMastered() ? "Đã thuộc" : "Đang học");
            tvStatus.setTextSize(12f);
            tvStatus.setTextColor(item.isMastered() ? Color.parseColor("#FF22C55E") : Color.parseColor("#FF4F46E5"));
            tvStatus.setBackgroundResource(R.drawable.bg_chip_unselected);
            tvStatus.setPadding(24, 8, 24, 8);

            topRow.addView(tvWord);
            topRow.addView(tvStatus);
            card.addView(topRow);

            // Phonetic
            TextView tvPhonetic = new TextView(this);
            LinearLayout.LayoutParams phParams = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
            );
            phParams.setMargins(0, 8, 0, 12);
            tvPhonetic.setLayoutParams(phParams);
            tvPhonetic.setText(item.phonetic + "  ·  " + item.pos);
            tvPhonetic.setTextSize(14f);
            tvPhonetic.setTextColor(Color.parseColor("#FF64748B"));
            card.addView(tvPhonetic);

            // Divider
            View divider = new View(this);
            LinearLayout.LayoutParams divParams = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    1
            );
            divParams.setMargins(0, 0, 0, 12);
            divider.setLayoutParams(divParams);
            divider.setBackgroundColor(Color.parseColor("#FFE2E8F0"));
            card.addView(divider);

            // Meaning
            TextView tvMeaning = new TextView(this);
            tvMeaning.setLayoutParams(new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
            ));
            tvMeaning.setText("Nghĩa: " + item.meaning);
            tvMeaning.setTextSize(14f);
            tvMeaning.setTextColor(Color.parseColor("#FF334155"));
            card.addView(tvMeaning);

            // Click listener to open detail
            card.setOnClickListener(v -> {
                Intent intent = new Intent(VocabularyActivity.this, VocabDetailActivity.class);
                intent.putExtra("VOCAB_WORD", item.word);
                intent.putExtra("VOCAB_SAVED_ID", item.savedId);
                intent.putExtra("VOCAB_PHONETIC", item.phonetic);
                intent.putExtra("VOCAB_LEVEL", item.level);
                intent.putExtra("VOCAB_MEANING", item.meaning);
                intent.putExtra("VOCAB_EXAMPLE", item.example);
                intent.putExtra("VOCAB_SYNONYMS", item.synonyms);
                startActivity(intent);
            });

            if (landscape) {
                if (displayed % 2 == 0) {
                    row = new LinearLayout(this);
                    row.setOrientation(LinearLayout.HORIZONTAL);
                    containerVocabList.addView(row, new LinearLayout.LayoutParams(-1, -2));
                }
                LinearLayout.LayoutParams grid = new LinearLayout.LayoutParams(0, -2, 1f);
                grid.setMargins(0, 0, 12, 16);
                row.addView(card, grid);
                displayed++;
            } else containerVocabList.addView(card);
        }
        if (landscape && displayed % 2 != 0 && row != null) row.addView(new View(this), new LinearLayout.LayoutParams(0, 1, 1f));
    }

    private void selectVocabTab(int index) {
        currentFilter = index;
        if (tabVocabAll == null || tabVocabLearning == null || tabVocabMastered == null) return;

        tabVocabAll.setBackgroundResource(R.drawable.bg_chip_unselected);
        tabVocabAll.setTextColor(Color.parseColor("#64748B"));

        tabVocabLearning.setBackgroundResource(R.drawable.bg_chip_unselected);
        tabVocabLearning.setTextColor(Color.parseColor("#64748B"));

        tabVocabMastered.setBackgroundResource(R.drawable.bg_chip_unselected);
        tabVocabMastered.setTextColor(Color.parseColor("#64748B"));

        if (index == 1) {
            tabVocabAll.setBackgroundResource(R.drawable.bg_chip_selected);
            tabVocabAll.setTextColor(Color.WHITE);
            if (tvStudyBtnText != null) tvStudyBtnText.setText("🎴 Ôn tập tất cả từ vựng bằng Flashcard");
        } else if (index == 2) {
            tabVocabLearning.setBackgroundResource(R.drawable.bg_chip_selected);
            tabVocabLearning.setTextColor(Color.WHITE);
            if (tvStudyBtnText != null) tvStudyBtnText.setText("🎴 Ôn tập từ vựng đang học bằng Flashcard");
        } else if (index == 3) {
            tabVocabMastered.setBackgroundResource(R.drawable.bg_chip_selected);
            tabVocabMastered.setTextColor(Color.WHITE);
            if (tvStudyBtnText != null) tvStudyBtnText.setText("🎴 Ôn tập từ vựng đã thuộc bằng Flashcard");
        }

        renderVocabList();
    }
}
