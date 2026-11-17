package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONObject;
import java.net.URLEncoder;
import androidx.appcompat.app.AppCompatActivity;

public class LoginActivity extends AppCompatActivity {

    private static final String TAG = "LoginActivity";
    private EditText etEmail, etPassword;
    private View btnLogin;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            if (BackendApi.token == null) BackendApi.token = SessionManager.load(this);
            if (BackendApi.token != null) {
                startActivity(new Intent(this, HomeActivity.class));
                finish();
                return;
            }
            setContentView(R.layout.layout_1_ng_nh_p);

            etEmail = findViewById(R.id.et_email);
            etPassword = findViewById(R.id.et_password);
            btnLogin = findViewById(R.id.btn_login);

            btnLogin.setOnClickListener(v -> {
                String email = etEmail.getText().toString().trim();
                String password = etPassword.getText().toString();
                if (email.isEmpty() || password.isEmpty()) {
                    Toast.makeText(this, "Nhập email và mật khẩu.", Toast.LENGTH_SHORT).show();
                    return;
                }
                btnLogin.setEnabled(false);
                BackendApi.run(this, () -> {
                    String form = "username=" + URLEncoder.encode(email, "UTF-8")
                            + "&password=" + URLEncoder.encode(password, "UTF-8");
                    return (JSONObject) BackendApi.send("/users/login", "POST",
                            "application/x-www-form-urlencoded", form, null);
                }, result -> {
                    BackendApi.token = result.optString("access_token");
                    btnLogin.setEnabled(true);
                    if (BackendApi.token.isEmpty()) {
                        BackendApi.token = null;
                        Toast.makeText(this, "Máy chủ không trả về phiên đăng nhập.", Toast.LENGTH_LONG).show();
                        return;
                    }
                    SessionManager.save(this, BackendApi.token);
                    startActivity(new Intent(this, HomeActivity.class));
                    finish();
                }, error -> {
                    btnLogin.setEnabled(true);
                    if ("Email verification required".equals(error)) {
                        Intent verify = new Intent(this, OtpVerificationActivity.class);
                        verify.putExtra("EMAIL", email);
                        startActivity(verify);
                        return;
                    }
                    Toast.makeText(this, error, Toast.LENGTH_LONG).show();
                });
            });

            TextView tvForgotPassword = findViewById(R.id.tv_forgot_password);
            if (tvForgotPassword != null) {
                tvForgotPassword.setOnClickListener(v -> startActivity(new Intent(LoginActivity.this, ForgotPasswordActivity.class)));
            }

            TextView tvRegister = findViewById(R.id.tv_register);
            if (tvRegister != null) {
                tvRegister.setOnClickListener(v -> startActivity(new Intent(LoginActivity.this, RegisterActivity.class)));
            }
        } catch (Exception e) {
            Log.e(TAG, "Error in LoginActivity onCreate", e);
            Toast.makeText(this, "Lỗi khởi động: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }
}
