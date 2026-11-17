package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.text.InputFilter;
import android.text.InputType;
import android.widget.*;
import androidx.appcompat.app.AppCompatActivity;
import org.json.JSONObject;

public class ForgotPasswordOtpActivity extends AppCompatActivity {
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        String email = getIntent().getStringExtra("EMAIL");
        if (email == null) { finish(); return; }
        int p = (int)(24 * getResources().getDisplayMetrics().density);
        ScrollView scroll = new ScrollView(this); LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL); root.setPadding(p,p,p,p); scroll.addView(root);
        TextView title = new TextView(this); title.setText("Xác minh mã đặt lại mật khẩu"); title.setTextSize(22); root.addView(title);
        TextView info = new TextView(this); info.setText("Nếu tài khoản hợp lệ, mã 6 chữ số sẽ được gửi tới " + email); root.addView(info);
        EditText input = new EditText(this); input.setHint("Mã OTP"); input.setInputType(InputType.TYPE_CLASS_NUMBER); input.setFilters(new InputFilter[]{new InputFilter.LengthFilter(6)}); root.addView(input);
        Button submit = new Button(this); submit.setText("Xác minh"); root.addView(submit); setContentView(scroll);
        submit.setOnClickListener(v -> {
            String code=input.getText().toString().trim();
            if(!code.matches("\\d{6}")){Toast.makeText(this,"Mã OTP phải gồm 6 chữ số.",Toast.LENGTH_SHORT).show();return;}
            submit.setEnabled(false);
            BackendApi.run(this, () -> BackendApi.send("/auth/password-reset/verify","POST","application/json",new JSONObject().put("email",email).put("code",code).toString(),null), result -> {
                submit.setEnabled(true); Intent next=new Intent(this,ResetPasswordActivity.class); next.putExtra("EMAIL",email); next.putExtra("OTP",code); startActivity(next);
            }, error -> {submit.setEnabled(true); Toast.makeText(this,error,Toast.LENGTH_LONG).show();});
        });
    }
}
