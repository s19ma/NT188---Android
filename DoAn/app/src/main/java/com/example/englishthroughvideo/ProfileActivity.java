package com.example.englishthroughvideo;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.view.View;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;

public class ProfileActivity extends AppCompatActivity {

    private static final int PICK_IMAGE_REQUEST = 1001;
    private ImageView ivAvatar;
    private TextView tvProfileName, tvProfileEmail;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_11_h_s_c_nh_n);

        ivAvatar = findViewById(R.id.iv_avatar);
        tvProfileName = findViewById(R.id.tv_profile_name);
        tvProfileEmail = findViewById(R.id.tv_profile_email);

        View btnChangeAvatar = findViewById(R.id.btn_change_avatar);
        View btnEditProfile = findViewById(R.id.btn_edit_profile);
        View btnLogout = findViewById(R.id.btn_logout);

        // Click Avatar or Change Avatar button to choose a new icon
        View.OnClickListener changeAvatarListener = v -> {
            final String[] avatarOptions = {
                "📘 Biểu tượng Tiếng Anh mới (ENG Book Icon)",
                "🎨 Avatar Phong cách Tím Indigo",
                "🟢 Avatar Phong cách Xanh Lá",
                "📁 Chọn ảnh từ Thư viện / Download"
            };

            AlertDialog.Builder builder = new AlertDialog.Builder(this);
            builder.setTitle("Chọn ảnh đại diện mới");
            builder.setItems(avatarOptions, (dialog, which) -> {
                if (which == 0) {
                    if (ivAvatar != null) {
                        ivAvatar.setImageResource(R.mipmap.ic_launcher);
                    }
                    Toast.makeText(this, "Đã đổi ảnh đại diện sang ENG Book Icon thành công!", Toast.LENGTH_SHORT).show();
                } else if (which == 1) {
                    if (ivAvatar != null) {
                        ivAvatar.setImageResource(R.drawable.bg_card_primary);
                    }
                    Toast.makeText(this, "Đã đổi ảnh đại diện Tím Indigo thành công!", Toast.LENGTH_SHORT).show();
                } else if (which == 2) {
                    if (ivAvatar != null) {
                        ivAvatar.setImageResource(R.drawable.bg_chip_selected);
                    }
                    Toast.makeText(this, "Đã đổi ảnh đại diện Xanh lá thành công!", Toast.LENGTH_SHORT).show();
                } else {
                    try {
                        Intent intent = new Intent(Intent.ACTION_PICK, MediaStore.Images.Media.EXTERNAL_CONTENT_URI);
                        startActivityForResult(intent, PICK_IMAGE_REQUEST);
                    } catch (Exception e) {
                        if (ivAvatar != null) ivAvatar.setImageResource(R.mipmap.ic_launcher);
                        Toast.makeText(this, "Đã đổi ảnh đại diện mới thành công!", Toast.LENGTH_SHORT).show();
                    }
                }
            });
            builder.show();
        };

        if (btnChangeAvatar != null) btnChangeAvatar.setOnClickListener(changeAvatarListener);
        if (ivAvatar != null) ivAvatar.setOnClickListener(changeAvatarListener);

        // Click to Edit Profile Information
        if (btnEditProfile != null) {
            btnEditProfile.setOnClickListener(v -> showEditProfileDialog());
        }

        // Click Logout -> Open Login screen
        if (btnLogout != null) {
            btnLogout.setOnClickListener(v -> {
                BackendApi.token = null;
                SessionManager.clear(this);
                Toast.makeText(ProfileActivity.this, "Đã đăng xuất tài khoản", Toast.LENGTH_SHORT).show();
                Intent intent = new Intent(ProfileActivity.this, LoginActivity.class);
                intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
                startActivity(intent);
            });
        }

        // Bottom Navigation Bar Tabs
        View navHome = findViewById(R.id.nav_home);
        if (navHome != null) navHome.setOnClickListener(v -> startActivity(new Intent(ProfileActivity.this, HomeActivity.class)));

        View navVocabulary = findViewById(R.id.nav_vocabulary);
        if (navVocabulary != null) navVocabulary.setOnClickListener(v -> startActivity(new Intent(ProfileActivity.this, VocabularyActivity.class)));

        View navFlashcard = findViewById(R.id.nav_flashcard);
        if (navFlashcard != null) navFlashcard.setOnClickListener(v -> startActivity(new Intent(ProfileActivity.this, FlashcardActivity.class)));

        View navProgress = findViewById(R.id.nav_progress);
        if (navProgress != null) navProgress.setOnClickListener(v -> startActivity(new Intent(ProfileActivity.this, ProfileActivity.this.getClass())));
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (BackendApi.token == null) BackendApi.token = SessionManager.load(this);
        if (BackendApi.token == null) return;
        BackendApi.run(this, () -> (org.json.JSONObject) BackendApi.send(
                "/users/me", "GET", null, null, BackendApi.token), user -> {
            if (tvProfileName != null) tvProfileName.setText(user.isNull("display_name") ? "" : user.optString("display_name", ""));
            if (tvProfileEmail != null) tvProfileEmail.setText(user.optString("email", ""));
        });
    }

    private void showEditProfileDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("Chỉnh sửa thông tin cá nhân");

        final EditText inputName = new EditText(this);
        inputName.setHint("Họ và tên");
        if (tvProfileName != null) inputName.setText(tvProfileName.getText().toString());

        final EditText inputEmail = new EditText(this);
        inputEmail.setHint("Email");
        if (tvProfileEmail != null) inputEmail.setText(tvProfileEmail.getText().toString());

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(40, 20, 40, 20);
        layout.addView(inputName);
        layout.addView(inputEmail);
        builder.setView(layout);

        builder.setPositiveButton("Lưu", (dialog, which) -> {
            String newName = inputName.getText().toString().trim();
            String newEmail = inputEmail.getText().toString().trim();

            if (newName.isEmpty()) return;
            BackendApi.run(ProfileActivity.this, () -> BackendApi.send("/users/me", "PATCH", "application/json",
                    new org.json.JSONObject().put("display_name", newName).toString(), BackendApi.token), result -> {
                if (tvProfileName != null) tvProfileName.setText(newName);
                if (!newEmail.equals(tvProfileEmail == null ? "" : tvProfileEmail.getText().toString())) {
                    Toast.makeText(ProfileActivity.this, "Backend chưa hỗ trợ đổi email.", Toast.LENGTH_LONG).show();
                }
            });
        });

        builder.setNegativeButton("Hủy", (dialog, which) -> dialog.cancel());
        builder.show();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, @Nullable Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == PICK_IMAGE_REQUEST && resultCode == RESULT_OK && data != null && data.getData() != null) {
            Uri imageUri = data.getData();
            if (ivAvatar != null) {
                ivAvatar.setImageURI(imageUri);
                Toast.makeText(this, "Đổi ảnh đại diện thành công!", Toast.LENGTH_SHORT).show();
            }
        }
    }
}
