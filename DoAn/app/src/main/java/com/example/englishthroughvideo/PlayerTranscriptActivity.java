package com.example.englishthroughvideo;

import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Build;
import android.text.SpannableString;
import android.text.Spanned;
import android.text.method.LinkMovementMethod;
import android.text.style.ClickableSpan;
import android.text.TextPaint;
import android.util.Log;
import android.view.View;
import android.widget.TextView;
import android.widget.Toast;
import android.widget.LinearLayout;
import androidx.media3.common.MediaItem;
import androidx.media3.common.PlaybackException;
import androidx.media3.common.Player;
import androidx.media3.exoplayer.DefaultRenderersFactory;
import androidx.media3.exoplayer.ExoPlayer;
import androidx.media3.exoplayer.mediacodec.MediaCodecInfo;
import androidx.media3.exoplayer.mediacodec.MediaCodecSelector;
import androidx.media3.ui.PlayerView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.Locale;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import androidx.appcompat.app.AppCompatActivity;

public class PlayerTranscriptActivity extends AppCompatActivity {

    private static final String PLAYER_TAG = "EnglishVideoPlayer";
    private static final ExecutorService PROGRESS_WRITES = Executors.newSingleThreadExecutor();
    private String videoTitle;
    private String videoId;
    private String token;
    private boolean prepared;
    private boolean completed;
    private boolean completionSaved;
    private boolean foreground;
    private boolean pendingStart;
    private boolean resumePlayback = true;
    private int resumePosition;
    private ExoPlayer player;
    private PlayerView playerView;
    private JSONArray transcriptSegments = new JSONArray();
    private int restoredScroll;
    private final android.os.Handler highlightHandler = new android.os.Handler(android.os.Looper.getMainLooper());
    private final Runnable highlightCurrent = new Runnable() {
        @Override public void run() {
            if (player != null && prepared && findViewById(R.id.transcript_list) instanceof LinearLayout) {
                LinearLayout list = findViewById(R.id.transcript_list);
                long position = player.getCurrentPosition();
                for (int i = 0; i < list.getChildCount(); i++) {
                    View row = list.getChildAt(i);
                    if (!(row.getTag() instanceof long[])) continue;
                    long[] range = (long[]) row.getTag();
                    row.setBackgroundResource(position >= range[0] && position < range[1]
                            ? R.drawable.bg_streak_done : R.drawable.bg_card_white);
                }
            }
            if (foreground) highlightHandler.postDelayed(this, 500);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_4_1_player_transcript);

        videoId = getIntent().getStringExtra("VIDEO_ID");
        token = BackendApi.token;
        videoTitle = getIntent().getStringExtra("VIDEO_TITLE");
        if (videoTitle == null) videoTitle = "Video";
        resumePosition = savedInstanceState == null ? getIntent().getIntExtra("POSITION_MS", 0) : savedInstanceState.getInt("player_position");
        completed = savedInstanceState == null ? getIntent().getBooleanExtra("VIDEO_COMPLETED", false) : savedInstanceState.getBoolean("player_completed");
        restoredScroll = savedInstanceState == null ? 0 : savedInstanceState.getInt("transcript_scroll");
        if (savedInstanceState != null) resumePlayback = savedInstanceState.getBoolean("player_was_playing", true);
        ((TextView) findViewById(R.id.tv_player_video_title)).setText(videoTitle);

        playerView = findViewById(R.id.video_view);
        // AVDs and a few low-end devices can expose an H.264 decoder that fails after
        // preparation. Decoder fallback retries an alternative (including software)
        // decoder instead of stopping playback.
        DefaultRenderersFactory renderersFactory = new DefaultRenderersFactory(this)
                .setEnableDecoderFallback(true);
        if (Build.FINGERPRINT.contains("generic") || Build.HARDWARE.contains("goldfish")) {
            renderersFactory.setMediaCodecSelector((mimeType, requiresSecureDecoder,
                                                     requiresTunnelingDecoder) -> {
                List<MediaCodecInfo> decoders = new ArrayList<>(
                        MediaCodecSelector.DEFAULT.getDecoderInfos(mimeType,
                                requiresSecureDecoder, requiresTunnelingDecoder));
                if ("video/avc".equals(mimeType)) {
                    decoders.sort((first, second) -> Boolean.compare(
                            isAndroidSoftwareDecoder(second.name),
                            isAndroidSoftwareDecoder(first.name)));
                }
                return decoders;
            });
        }
        player = new ExoPlayer.Builder(this, renderersFactory).build();
        playerView.setPlayer(player);
        player.addListener(new Player.Listener() {
            @Override
            public void onPlaybackStateChanged(int state) {
                Log.i(PLAYER_TAG, "playback state=" + state + ", position=" + player.getCurrentPosition());
                if (state == Player.STATE_READY) {
                    prepared = true;
                    if (resumePosition > 0 && resumePosition < player.getDuration()) {
                        player.seekTo(resumePosition);
                        resumePosition = 0;
                    }
                    if (resumePlayback && (foreground || pendingStart)) {
                        pendingStart = false;
                        player.play();
                    }
                } else if (state == Player.STATE_ENDED && !completionSaved) {
                    completed = true;
                    completionSaved = true;
                    saveProgress((int) Math.min(Integer.MAX_VALUE,
                            Math.max(0L, player.getDuration())));
                }
            }

            @Override
            public void onPlayerError(PlaybackException error) {
                prepared = false;
                Log.e(PLAYER_TAG, "Playback failed: " + error.getErrorCodeName(), error);
                Toast.makeText(PlayerTranscriptActivity.this,
                        "Không thể phát video: " + error.getErrorCodeName(),
                        Toast.LENGTH_LONG).show();
            }

            @Override
            public void onIsPlayingChanged(boolean isPlaying) {
                Log.i(PLAYER_TAG, "isPlaying=" + isPlaying + ", position=" + player.getCurrentPosition());
            }
        });
        if (videoId != null && token != null) {
            String path = "/videos/" + videoId;
            BackendApi.run(this, () -> (JSONObject) BackendApi.send(
                    path + "/playback", "GET", null, null, token), playback -> {
                String playbackUrl = playback.optString("playback_url");
                if (!playbackUrl.startsWith("https://")) {
                    Toast.makeText(this, "Địa chỉ video không hợp lệ.", Toast.LENGTH_LONG).show();
                    return;
                }
                player.setMediaItem(MediaItem.fromUri(playbackUrl));
                player.setPlayWhenReady(resumePlayback);
                player.prepare();
                if (foreground && resumePlayback) player.play();
                else pendingStart = resumePlayback;
            });
            loadTranscript(path);
        } else {
            ((TextView) findViewById(R.id.transcript_status)).setText("Thiếu dữ liệu video hoặc phiên đăng nhập.");
        }

        // Back button click
        View btnBack = findViewById(R.id.btn_back);
        if (btnBack != null) {
            btnBack.setOnClickListener(v -> finish());
        }

        TextView tabTranscript = findViewById(R.id.tab_transcript);
        TextView tabSummary = findViewById(R.id.tab_summary);
        TextView tabVocab = findViewById(R.id.tab_vocab);
        if (tabTranscript != null) tabTranscript.setOnClickListener(v -> renderTranscript());
        if (tabSummary != null) tabSummary.setOnClickListener(v -> renderSummary());
        if (tabVocab != null) tabVocab.setOnClickListener(v -> renderVocabulary());
    }

    private void loadTranscript(String path) {
        TextView status = findViewById(R.id.transcript_status);
        status.setText("Đang tải phụ đề…");
        BackendApi.run(this, () -> {
            try {
                JSONObject response = (JSONObject) BackendApi.send(
                        path + "/subtitles", "GET", null, null, token);
                return response.getJSONArray("segments");
            } catch (BackendApi.ApiException error) {
                if (error.status == 404) return new JSONArray();
                throw error;
            }
        }, segments -> {
            transcriptSegments = segments;
            renderTranscript();
        }, status::setText);
    }

    private void renderTranscript() {
        selectContentTab(R.id.tab_transcript);
        TextView status = findViewById(R.id.transcript_status);
        LinearLayout list = findViewById(R.id.transcript_list);
        list.removeAllViews();
        status.setText(transcriptSegments.length() == 0 ? "Chưa có phụ đề." : "");
        int padding = Math.round(12 * getResources().getDisplayMetrics().density);
        for (int i = 0; i < transcriptSegments.length(); i++) {
            JSONObject segment = transcriptSegments.optJSONObject(i);
            if (segment == null) continue;
            int position = segment.optInt("start_ms");
            int seconds = position / 1000;
            String time = String.format(Locale.ROOT, "%d:%02d", seconds / 60, seconds % 60);
            String content = segment.optString("content");
            TextView row = panelRow(time + "  " + content, padding);
            row.setTag(new long[]{segment.optLong("start_ms"), segment.optLong("end_ms")});
            bindTranscriptWords(row, time.length() + 2, content, segment.optLong("id"));
            row.setOnClickListener(v -> { if (prepared) player.seekTo(position); });
            list.addView(row);
        }
        if (restoredScroll > 0) {
            android.widget.ScrollView scroll = findViewById(R.id.transcript_scroll);
            int position = restoredScroll;
            restoredScroll = 0;
            scroll.post(() -> scroll.scrollTo(0, position));
        }
    }

    private void renderSummary() {
        selectContentTab(R.id.tab_summary);
        TextView status = findViewById(R.id.transcript_status);
        LinearLayout list = findViewById(R.id.transcript_list);
        list.removeAllViews();
        status.setText("Đang tải tóm tắt…");
        BackendApi.run(this, () -> (JSONObject) BackendApi.send("/videos/" + videoId + "/summary",
                "GET", null, null, token), summary -> {
            JSONArray points = summary.optJSONArray("key_points");
            if (points == null || points.length() == 0) {
                status.setText("Video này chưa có tóm tắt.");
                return;
            }
            status.setText(summary.optString("summary_text", "Các ý chính của video"));
            int padding = Math.round(12 * getResources().getDisplayMetrics().density);
            for (int i = 0; i < points.length(); i++) {
                String point = points.optString(i);
                if (point.isEmpty()) continue;
                TextView row = panelRow(point, padding);
                int pick = transcriptSegments.length() == 0 ? 0 : i * (transcriptSegments.length() - 1) / Math.max(1, points.length() - 1);
                JSONObject segment = transcriptSegments.optJSONObject(pick);
                if (segment != null) {
                    int position = segment.optInt("start_ms");
                    row.setOnClickListener(v -> { if (prepared) player.seekTo(position); });
                }
                list.addView(row);
            }
        }, error -> status.setText(error.contains("404") ? "Video này chưa có tóm tắt." : error));
    }

    private void renderVocabulary() {
        selectContentTab(R.id.tab_vocab);
        TextView status = findViewById(R.id.transcript_status);
        LinearLayout list = findViewById(R.id.transcript_list);
        list.removeAllViews();
        status.setText("Đang tải từ vựng của video…");
        BackendApi.run(this, () -> (JSONArray) BackendApi.send("/videos/" + videoId + "/vocabulary?limit=30",
                "GET", null, null, token), words -> {
            list.removeAllViews();
            status.setText(words.length() == 0 ? "Chưa có từ vựng cho video này." : "Chạm một từ để tra và lưu.");
            int padding = Math.round(12 * getResources().getDisplayMetrics().density);
            for (int i = 0; i < words.length(); i++) {
                JSONObject item = words.optJSONObject(i);
                if (item == null) continue;
                String word = item.optString("lemma");
                TextView row = panelRow(word + "  " + item.optString("phonetic") + "\n"
                        + item.optString("part_of_speech") + " — " + item.optString("definition"), padding);
                row.setOnClickListener(v -> {
                    Intent popup = new Intent(this, DictionaryPopupActivity.class);
                    popup.putExtra("CLICKED_WORD", word);
                    popup.putExtra("CLICKED_SENTENCE", "Từ trong video: " + videoTitle);
                    popup.putExtra("VIDEO_ID", videoId);
                    startActivity(popup);
                });
                list.addView(row);
            }
        }, status::setText);
    }

    private TextView panelRow(String text, int padding) {
        TextView row = new TextView(this);
        row.setText(text);
        row.setPadding(padding, padding, padding, padding);
        row.setBackgroundResource(R.drawable.bg_card_white);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        params.bottomMargin = padding;
        row.setLayoutParams(params);
        return row;
    }

    /** Keeps the selected content tab visibly tied to the panel being shown. */
    private void selectContentTab(int selectedId) {
        int[] tabIds = {R.id.tab_transcript, R.id.tab_summary, R.id.tab_vocab};
        for (int tabId : tabIds) {
            TextView tab = findViewById(tabId);
            if (tab == null) continue;
            boolean selected = tabId == selectedId;
            tab.setBackgroundResource(selected ? R.drawable.bg_chip_selected : R.drawable.bg_chip_unselected);
            tab.setTextColor(Color.parseColor(selected ? "#FFFFFFFF" : "#FF64748B"));
        }
    }

    private void bindTranscriptWords(TextView row, int offset, String sentence, long segmentId) {
        SpannableString text = new SpannableString(row.getText());
        Matcher matcher = Pattern.compile("[A-Za-z]+(?:['-][A-Za-z]+)*").matcher(sentence);
        while (matcher.find()) {
            final String selectedWord = matcher.group();
            text.setSpan(new ClickableSpan() {
                @Override public void onClick(View widget) {
                    Intent popup = new Intent(PlayerTranscriptActivity.this, DictionaryPopupActivity.class);
                    popup.putExtra("CLICKED_WORD", selectedWord);
                    popup.putExtra("CLICKED_SENTENCE", sentence);
                    popup.putExtra("VIDEO_ID", videoId);
                    popup.putExtra("TRANSCRIPT_SEGMENT_ID", segmentId);
                    startActivity(popup);
                }
                @Override public void updateDrawState(TextPaint paint) {
                    paint.setColor(getResources().getColor(android.R.color.holo_blue_dark));
                    paint.setUnderlineText(false);
                }
            }, offset + matcher.start(), offset + matcher.end(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        }
        row.setText(text);
        row.setMovementMethod(LinkMovementMethod.getInstance());
        row.setHighlightColor(0x22000000);
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        outState.putInt("player_position", prepared ? (int) player.getCurrentPosition() : resumePosition);
        outState.putBoolean("player_completed", completed);
        outState.putBoolean("player_was_playing", resumePlayback);
        android.widget.ScrollView scroll = findViewById(R.id.transcript_scroll);
        if (scroll != null) outState.putInt("transcript_scroll", scroll.getScrollY());
        super.onSaveInstanceState(outState);
    }

    @Override
    protected void onResume() {
        super.onResume();
        foreground = true;
        highlightHandler.removeCallbacks(highlightCurrent);
        highlightHandler.post(highlightCurrent);
        if (pendingStart) {
            pendingStart = false;
            player.play();
        }
    }

    @Override
    protected void onPause() {
        foreground = false;
        highlightHandler.removeCallbacks(highlightCurrent);
        if (prepared) {
            resumePlayback = player.getPlayWhenReady();
            resumePosition = (int) player.getCurrentPosition();
            if (!completionSaved && resumePosition > 0) saveProgress(resumePosition);
            player.pause();
        }
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        if (player != null) player.release();
        super.onDestroy();
    }

    private void saveProgress(int position) {
        if (videoId == null || token == null) return;
        boolean watchedToEnd = completed;
        PROGRESS_WRITES.execute(() -> {
            try {
                JSONObject body = new JSONObject().put("position_ms", position)
                        .put("is_completed", watchedToEnd);
                BackendApi.send("/users/me/progress/" + videoId, "PUT", "application/json",
                        body.toString(), token);
            } catch (Exception error) {
                runOnUiThread(() -> Toast.makeText(getApplicationContext(),
                        "Không lưu được tiến độ xem.", Toast.LENGTH_SHORT).show());
            }
        });
    }

    private static boolean isAndroidSoftwareDecoder(String name) {
        return name.startsWith("OMX.google.") || name.startsWith("c2.android.");
    }
}
