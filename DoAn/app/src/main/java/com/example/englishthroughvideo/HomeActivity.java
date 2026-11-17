package com.example.englishthroughvideo;

import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.View;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import android.widget.LinearLayout;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class HomeActivity extends AppCompatActivity {

    private TextView tabAll, tabLearning, tabCompleted, status;
    private LinearLayout videoList;
    private EditText search;
    private JSONArray videos;
    private final Map<String, JSONObject> progress = new HashMap<>();
    private int selectedTab;
    private int loadVersion;
    private boolean resumePromptShown;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_4_home_th_vi_n_video);

        tabAll = findViewById(R.id.tab_all);
        tabLearning = findViewById(R.id.tab_learning);
        tabCompleted = findViewById(R.id.tab_completed);
        status = findViewById(R.id.video_status);
        videoList = findViewById(R.id.video_list);
        search = findViewById(R.id.et_search);
        tabAll.setOnClickListener(v -> selectTab(0));
        tabLearning.setOnClickListener(v -> selectTab(1));
        tabCompleted.setOnClickListener(v -> selectTab(2));

        search.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) {
                renderVideos();
            }
            @Override public void afterTextChanged(Editable s) {}
        });

        // Bottom Navigation Bar Tabs
        View navVocabulary = findViewById(R.id.nav_vocabulary);
        if (navVocabulary != null) navVocabulary.setOnClickListener(v -> startActivity(new Intent(HomeActivity.this, VocabularyActivity.class)));
        View navFlashcard = findViewById(R.id.nav_flashcard);
        if (navFlashcard != null) navFlashcard.setOnClickListener(v -> startActivity(new Intent(HomeActivity.this, FlashcardActivity.class)));
        View navProgress = findViewById(R.id.nav_progress);
        if (navProgress != null) navProgress.setOnClickListener(v -> startActivity(new Intent(HomeActivity.this, ProgressActivity.class)));
        View navProfile = findViewById(R.id.nav_profile);
        if (navProfile != null) navProfile.setOnClickListener(v -> startActivity(new Intent(HomeActivity.this, ProfileActivity.class)));
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (BackendApi.token == null) BackendApi.token = SessionManager.load(this);
        String token = BackendApi.token;
        if (token == null) {
            startActivity(new Intent(this, LoginActivity.class));
            finish();
            return;
        }
        int version = ++loadVersion;
        offerFlashcardResume(token, version);
        loadStreak(token, version);
        status.setText("Đang tải video…");
        status.setOnClickListener(null);
        BackendApi.run(this, () -> {
            JSONArray catalog = (JSONArray) BackendApi.send("/videos", "GET", null, null, null);
            Map<String, JSONObject> positions = new HashMap<>();
            for (int skip = 0; ; skip += 100) {
                JSONArray page = (JSONArray) BackendApi.send(
                        "/users/me/progress?limit=100&skip=" + skip, "GET", null, null, token);
                for (int i = 0; i < page.length(); i++) {
                    JSONObject row = page.getJSONObject(i);
                    positions.put(row.getString("video_id"), row);
                }
                if (page.length() < 100) break;
            }
            return new Catalog(catalog, positions);
        }, result -> {
            if (version != loadVersion) return;
            videos = result.videos;
            progress.clear();
            progress.putAll(result.progress);
            renderVideos();
        }, error -> {
            if (version != loadVersion) return;
            status.setText(error + " Chạm để đăng nhập lại hoặc tải lại.");
            status.setOnClickListener(v -> {
                if (error.startsWith("Sai email")) {
                    BackendApi.token = null;
                    startActivity(new Intent(this, LoginActivity.class));
                    finish();
                } else {
                    recreate();
                }
            });
        });
    }

    private void offerFlashcardResume(String token, int version) {
        if (resumePromptShown) return;
        BackendApi.run(this, () -> (JSONObject) BackendApi.send("/users/me", "GET", null, null, token), user -> {
            String owner = user.optString("id");
            JSONObject snapshot = FlashcardSessionStore.read(this, owner);
            if (version != loadVersion || isFinishing() || owner.isEmpty() || snapshot == null
                    || !owner.equals(snapshot.optString("owner")) || snapshot.optJSONArray("cards") == null
                    || snapshot.optJSONArray("cards").length() == 0) return;
            resumePromptShown = true;
            new androidx.appcompat.app.AlertDialog.Builder(this)
                    .setTitle("Tiếp tục học")
                    .setMessage("Bạn có một phiên flashcard chưa hoàn thành.")
                    .setPositiveButton("Tiếp tục học", (dialog, which) -> {
                        Intent intent = new Intent(this, FlashcardActivity.class);
                        intent.putExtra("resume_flashcard_session", true);
                        startActivity(intent);
                    })
                    .setNegativeButton("Bỏ phiên", (dialog, which) -> {
                        if (!FlashcardSessionStore.clear(this, owner)) android.widget.Toast.makeText(this, "Không thể xóa phiên trên thiết bị.", android.widget.Toast.LENGTH_LONG).show();
                    })
                    .setNeutralButton("Để sau", (dialog, which) -> { })
                    .show();
        }, error -> { });
    }

    private void loadStreak(String token, int version) {
        TextView count = findViewById(R.id.streak_count);
        int[] ids = {R.id.streak_day_0, R.id.streak_day_1, R.id.streak_day_2,
                R.id.streak_day_3, R.id.streak_day_4, R.id.streak_day_5, R.id.streak_day_6};
        String[] labels = {"T2", "T3", "T4", "T5", "T6", "T7", "CN"};
        count.setText("-- ngày");
        for (int i = 0; i < ids.length; i++) {
            TextView day = findViewById(ids[i]);
            day.setText(labels[i] + "\n–");
            day.setTextColor(Color.parseColor("#64748B"));
            day.setBackgroundResource(R.drawable.bg_streak_pending);
        }
        BackendApi.run(this, () -> (JSONObject) BackendApi.send("/users/me/streak", "GET", null, null, token), result -> {
            if (version != loadVersion) return;
            count.setText("🔥 " + result.optInt("current_streak") + " ngày");
            JSONArray week = result.optJSONArray("week");
            if (week == null) return;
            String today = result.optString("today");
            for (int i = 0; i < ids.length && i < week.length(); i++) {
                JSONObject entry = week.optJSONObject(i);
                if (entry == null) continue;
                boolean active = entry.optBoolean("active");
                boolean isToday = today.equals(entry.optString("date"));
                TextView day = findViewById(ids[i]);
                day.setText(labels[i] + "\n" + (active ? (isToday ? "🔥" : "✓") : "•"));
                day.setBackgroundResource(isToday && active ? R.drawable.bg_streak_today : active ? R.drawable.bg_streak_done : R.drawable.bg_streak_pending);
                day.setTextColor(Color.parseColor(isToday && active ? "#FFFFFF" : active ? "#4F46E5" : "#94A3B8"));
            }
        }, error -> { if (version == loadVersion) count.setText("Chưa tải được"); });
    }

    private void selectTab(int index) {
        selectedTab = index;
        TextView[] tabs = {tabAll, tabLearning, tabCompleted};
        for (int i = 0; i < tabs.length; i++) {
            tabs[i].setBackgroundResource(i == index ? R.drawable.bg_chip_selected : R.drawable.bg_chip_unselected);
            tabs[i].setTextColor(i == index ? Color.WHITE : Color.parseColor("#64748B"));
        }
        renderVideos();
    }

    private void renderVideos() {
        if (videos == null) return;
        videoList.removeAllViews();
        boolean landscape = getResources().getConfiguration().orientation == android.content.res.Configuration.ORIENTATION_LANDSCAPE;
        LinearLayout rowContainer = null;
        int visibleCards = 0;
        String query = search.getText().toString().trim().toLowerCase(Locale.ROOT);
        for (int i = 0; i < videos.length(); i++) {
            JSONObject video = videos.optJSONObject(i);
            if (video == null) continue;
            String id = video.optString("id");
            String title = video.optString("title");
            JSONObject position = progress.get(id);
            boolean completed = position != null && position.optBoolean("is_completed");
            if (selectedTab == 1 && (position == null || completed)) continue;
            if (selectedTab == 2 && !completed) continue;
            if (!title.toLowerCase(Locale.ROOT).contains(query)) continue;

            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.VERTICAL);
            card.setBackgroundResource(R.drawable.bg_card_white);
            card.setClickable(true);
            card.setFocusable(true);
            String level = video.isNull("cefr_level") ? "" : " · " + video.optString("cefr_level");
            int padding = Math.round(16 * getResources().getDisplayMetrics().density);
            card.setPadding(padding, padding, padding, padding);
            String thumbnailUrl = video.optString("thumbnail_url", "");
            if (!thumbnailUrl.isEmpty()) {
                ImageView thumbnail = new ImageView(this);
                thumbnail.setScaleType(ImageView.ScaleType.CENTER_CROP);
                thumbnail.setContentDescription("Thumbnail: " + title);
                LinearLayout.LayoutParams imageLayout = new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        Math.round(160 * getResources().getDisplayMetrics().density));
                imageLayout.bottomMargin = padding / 2;
                card.addView(thumbnail, imageLayout);
                loadThumbnail(thumbnailUrl, thumbnail);
            }
            TextView titleView = new TextView(this);
            titleView.setText(title + level);
            titleView.setTextColor(Color.parseColor("#0F172A"));
            titleView.setTextSize(16);
            card.addView(titleView);

            TextView learningBadge = new TextView(this);
            boolean started = position != null && position.optInt("position_ms", 0) > 0;
            String badgeText = completed ? "Hoàn thành" : (started ? "Đang học" : "Chưa học");
            int badgeColor = completed ? Color.parseColor("#15803D")
                    : (started ? Color.parseColor("#D97706") : Color.parseColor("#64748B"));
            learningBadge.setText(badgeText);
            learningBadge.setTextSize(12);
            learningBadge.setTextColor(badgeColor);
            learningBadge.setPadding(0, Math.round(6 * getResources().getDisplayMetrics().density), 0, 0);
            card.addView(learningBadge);
            LinearLayout.LayoutParams layout = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
            layout.bottomMargin = padding / 2;
            if (landscape) {
                if (visibleCards % 2 == 0) {
                    rowContainer = new LinearLayout(this);
                    rowContainer.setOrientation(LinearLayout.HORIZONTAL);
                    videoList.addView(rowContainer, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));
                }
                LinearLayout.LayoutParams gridParams = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
                gridParams.setMargins(0, 0, padding / 2, padding / 2);
                rowContainer.addView(card, gridParams);
                visibleCards++;
            } else videoList.addView(card, layout);
            card.setOnClickListener(v -> {
                Intent intent = new Intent(this, PlayerTranscriptActivity.class);
                intent.putExtra("VIDEO_ID", id);
                intent.putExtra("VIDEO_TITLE", title);
                intent.putExtra("VIDEO_COMPLETED", completed);
                intent.putExtra("POSITION_MS", position == null || completed ? 0 : position.optInt("position_ms"));
                startActivity(intent);
            });
        }
        if (landscape && visibleCards % 2 != 0 && rowContainer != null) {
            rowContainer.addView(new View(this), new LinearLayout.LayoutParams(0, 1, 1f));
        }
        status.setText(videoList.getChildCount() == 0 ? "Không có video phù hợp." : "");
    }

    private void loadThumbnail(String imageUrl, ImageView target) {
        BackendApi.run(this, () -> {
            HttpURLConnection connection = (HttpURLConnection) new URL(imageUrl).openConnection();
            connection.setConnectTimeout(12000);
            connection.setReadTimeout(15000);
            try {
                try (InputStream input = connection.getInputStream()) {
                    Bitmap bitmap = BitmapFactory.decodeStream(input);
                    if (bitmap == null) throw new IllegalStateException("Không đọc được thumbnail.");
                    return bitmap;
                }
            } finally {
                connection.disconnect();
            }
        }, target::setImageBitmap, error -> target.setVisibility(View.GONE));
    }

    private static final class Catalog {
        final JSONArray videos;
        final Map<String, JSONObject> progress;

        Catalog(JSONArray videos, Map<String, JSONObject> progress) {
            this.videos = videos;
            this.progress = progress;
        }
    }
}
