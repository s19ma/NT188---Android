package com.example.englishthroughvideo;

import android.app.AlertDialog;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;

public class UploadVideoActivity extends AppCompatActivity {

    private static final int PICK_FILE_REQUEST = 3003;
    private EditText etTitle;
    private TextView tvSelectedFile;
    private String selectedVideoUriString = null;
    private final String selectedLevel = "B2";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_4_5t_i_video_l_n);

        View btnBack = findViewById(R.id.btn_back);
        etTitle = findViewById(R.id.et_video_title);
        tvSelectedFile = findViewById(R.id.tv_selected_file);
        View boxPickFile = findViewById(R.id.box_pick_file);
        View btnSubmit = findViewById(R.id.btn_submit_upload);

        if (btnBack != null) {
            btnBack.setOnClickListener(v -> finish());
        }

        final String[] options = {
            "📂 Chọn file từ Thư mục Download / Bộ nhớ thiết bị",
            "📹 Chọn từ Kho video mẫu có sẵn (Nhanh)"
        };

        final String[] sampleVideos = {
            "Mastering English Pronunciation.mp4",
            "Business Negotiation & Meetings.mp4",
            "Advanced Daily Conversation.mp4",
            "TED: Overcoming Fear of Public Speaking.mp4",
            "English Grammar Masterclass.mp4"
        };

        if (boxPickFile != null) {
            boxPickFile.setOnClickListener(v -> {
                AlertDialog.Builder builder = new AlertDialog.Builder(this);
                builder.setTitle("Chọn nguồn video tải lên");
                builder.setItems(options, (dialog, which) -> {
                    if (which == 0) {
                        // Open real file manager / download folder picker
                        try {
                            Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                            intent.setType("video/*");
                            startActivityForResult(Intent.createChooser(intent, "Chọn video từ Download"), PICK_FILE_REQUEST);
                        } catch (Exception e) {
                            Toast.makeText(this, "Không thể mở thư mục Download. Vui lòng chọn video mẫu.", Toast.LENGTH_SHORT).show();
                        }
                    } else {
                        // Show sample videos dialog
                        AlertDialog.Builder sampleBuilder = new AlertDialog.Builder(this);
                        sampleBuilder.setTitle("Chọn video mẫu");
                        sampleBuilder.setItems(sampleVideos, (d, w) -> {
                            String chosen = sampleVideos[w];
                            selectedVideoUriString = "android.resource://" + getPackageName() + "/" + android.R.drawable.ic_media_play;
                            if (tvSelectedFile != null) {
                                tvSelectedFile.setText("Đã chọn file: " + chosen);
                            }
                            if (etTitle != null) {
                                String titleWithoutExt = chosen.replaceAll("\\.[^.]+$", "");
                                etTitle.setText(titleWithoutExt);
                            }
                            Toast.makeText(this, "Đã chọn video thành công!", Toast.LENGTH_SHORT).show();
                        });
                        sampleBuilder.show();
                    }
                });
                builder.show();
            });
        }

        if (btnSubmit != null) {
            btnSubmit.setOnClickListener(v -> {
                String title = etTitle != null ? etTitle.getText().toString().trim() : "";
                if (title.isEmpty()) {
                    title = "Video học tiếng Anh mới";
                }
                Toast.makeText(UploadVideoActivity.this,
                        "Backend production chưa có API upload an toàn. Video chưa được gửi.", Toast.LENGTH_LONG).show();
            });
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, @Nullable Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == PICK_FILE_REQUEST && resultCode == RESULT_OK && data != null && data.getData() != null) {
            try {
                Uri videoUri = data.getData();
                try {
                    getContentResolver().takePersistableUriPermission(videoUri, Intent.FLAG_GRANT_READ_URI_PERMISSION);
                } catch (Exception ignored) {}

                selectedVideoUriString = videoUri.toString();
                String fileName = videoUri.getLastPathSegment();
                if (tvSelectedFile != null && fileName != null) {
                    tvSelectedFile.setText("Đã chọn từ Download: " + fileName);
                }
                if (etTitle != null && fileName != null) {
                    String title = fileName.replaceAll("\\.[^.]+$", "").replace("_", " ");
                    etTitle.setText(title);
                }
                Toast.makeText(this, "Đã chọn file từ thư mục Download thành công!", Toast.LENGTH_SHORT).show();
            } catch (Exception e) {
                Toast.makeText(this, "Lỗi đọc file từ Download.", Toast.LENGTH_SHORT).show();
            }
        }
    }
}
