package com.example.englishthroughvideo;

import android.os.Bundle;
import android.content.Intent;
import android.view.View;
import android.widget.Toast;
import android.widget.EditText;
import org.json.JSONObject;
import androidx.appcompat.app.AppCompatActivity;

public class RegisterActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_2_ng_k);

        // Click Quay lại -> về Login
        View tvBack = findViewById(R.id.tv_back);
        if (tvBack != null) {
            tvBack.setOnClickListener(v -> finish());
        }

        // Click Đăng nhập -> về Login
        View tvLogin = findViewById(R.id.tv_login);
        if (tvLogin != null) {
            tvLogin.setOnClickListener(v -> finish());
        }

        EditText emailInput = findViewById(R.id.et_register_email);
        EditText passwordInput = findViewById(R.id.et_register_password);
        EditText confirmInput = findViewById(R.id.et_register_confirm_password);
        View submit = findViewById(R.id.btn_continue);
        submit.setOnClickListener(v -> {
            String email = emailInput.getText().toString().trim();
            String password = passwordInput.getText().toString();
            if (email.isEmpty() || password.length() < 8) {
                Toast.makeText(this, "Nhập email và mật khẩu ít nhất 8 ký tự.", Toast.LENGTH_SHORT).show();
                return;
            }
            if (!password.equals(confirmInput.getText().toString())) {
                Toast.makeText(this, "Mật khẩu xác nhận không khớp.", Toast.LENGTH_SHORT).show();
                return;
            }
            submit.setEnabled(false);
            BackendApi.run(this, () -> {
                JSONObject body = new JSONObject().put("email", email).put("password", password);
                return BackendApi.send("/users/register", "POST", "application/json", body.toString(), null);
            }, result -> {
                Intent intent = new Intent(this, OtpVerificationActivity.class);
                intent.putExtra("EMAIL", email);
                startActivity(intent);
                finish();
            }, error -> {
                submit.setEnabled(true);
                Toast.makeText(this, error, Toast.LENGTH_LONG).show();
            });
        });
    }
}
