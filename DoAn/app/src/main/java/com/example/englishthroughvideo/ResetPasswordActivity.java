package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.text.InputType;
import android.widget.*;
import androidx.appcompat.app.AppCompatActivity;
import org.json.JSONObject;

public class ResetPasswordActivity extends AppCompatActivity {
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        String email=getIntent().getStringExtra("EMAIL"), otp=getIntent().getStringExtra("OTP");
        if(email==null||otp==null){finish();return;}
        int p=(int)(24*getResources().getDisplayMetrics().density);
        ScrollView scroll=new ScrollView(this); LinearLayout root=new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setPadding(p,p,p,p); scroll.addView(root);
        TextView heading=new TextView(this); heading.setText("Đặt lại mật khẩu"); heading.setTextSize(22); root.addView(heading);
        EditText password=new EditText(this); password.setHint("Mật khẩu mới (ít nhất 8 ký tự)"); password.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD); root.addView(password);
        EditText confirm=new EditText(this); confirm.setHint("Xác nhận mật khẩu mới"); confirm.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD); root.addView(confirm);
        Button submit=new Button(this); submit.setText("Lưu mật khẩu"); root.addView(submit); setContentView(scroll);
        submit.setOnClickListener(v -> {
            String value=password.getText().toString();
            if(value.length()<8||value.length()>128||!value.equals(confirm.getText().toString())){Toast.makeText(this,"Mật khẩu cần 8–128 ký tự và phải trùng xác nhận.",Toast.LENGTH_LONG).show();return;}
            submit.setEnabled(false);
            BackendApi.run(this, () -> BackendApi.send("/auth/password-reset/confirm","POST","application/json",new JSONObject().put("email",email).put("code",otp).put("password",value).toString(),null), result -> {
                startActivity(new Intent(this,ResetPasswordSuccessActivity.class)); finish();
            }, error -> {submit.setEnabled(true);Toast.makeText(this,error,Toast.LENGTH_LONG).show();});
        });
    }
}
