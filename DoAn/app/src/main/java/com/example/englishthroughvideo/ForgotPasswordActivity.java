package com.example.englishthroughvideo;

import android.os.Bundle;
import android.content.Intent;
import android.widget.EditText;
import android.view.View;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;

public class ForgotPasswordActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_3_qu_n_m_t_kh_u);

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

        EditText emailInput = findViewById(R.id.et_forgot_email);
        // Click Tiếp tục -> request a real OTP from the backend SMTP service.
        View btnContinue = findViewById(R.id.btn_continue);
        if (btnContinue != null) {
            btnContinue.setOnClickListener(v -> {
                String email = emailInput == null ? "" : emailInput.getText().toString().trim();
                if (email.isEmpty()) {
                    Toast.makeText(this, "Nhập địa chỉ email của bạn.", Toast.LENGTH_SHORT).show();
                    return;
                }
                btnContinue.setEnabled(false);
                BackendApi.run(this, () -> BackendApi.send("/auth/password-reset/request", "POST",
                        "application/json", new org.json.JSONObject().put("email", email).toString(), null), result -> {
                    Intent intent = new Intent(this, ForgotPasswordOtpActivity.class);
                    intent.putExtra("EMAIL", email);
                    btnContinue.setEnabled(true);
                    startActivity(intent);
                }, error -> {
                    btnContinue.setEnabled(true);
                    Toast.makeText(this, error, Toast.LENGTH_LONG).show();
                });
            });
        }
    }
}
