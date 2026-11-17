package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.text.InputFilter;
import android.text.InputType;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import org.json.JSONObject;

public class OtpVerificationActivity extends AppCompatActivity {
    private long resendAt;
    private android.os.CountDownTimer timer;
    private Button resendButton;
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        String email = getIntent().getStringExtra("EMAIL");
        if (email == null || email.isEmpty()) { finish(); return; }
        int pad = (int)(24 * getResources().getDisplayMetrics().density);
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setPadding(pad,pad,pad,pad); scroll.addView(root);
        TextView title = new TextView(this); title.setText("Xác minh email"); title.setTextSize(24); root.addView(title);
        TextView description = new TextView(this); description.setText("Nếu yêu cầu hợp lệ, mã gồm 6 chữ số sẽ được gửi đến " + email + ". Mã có hiệu lực 5 phút."); description.setPadding(0,pad/2,0,pad/2); root.addView(description);
        EditText code = new EditText(this); code.setHint("Mã xác minh"); code.setInputType(InputType.TYPE_CLASS_NUMBER); code.setFilters(new InputFilter[]{new InputFilter.LengthFilter(6)}); root.addView(code);
        Button verify = new Button(this); verify.setText("Xác minh"); root.addView(verify);
        Button resend = new Button(this); resendButton = resend; resend.setText("Gửi lại mã"); root.addView(resend);
        Button back = new Button(this); back.setText("Quay lại đăng nhập"); back.setOnClickListener(v -> finish()); root.addView(back);
        setContentView(scroll);
        resendAt = state == null ? android.os.SystemClock.elapsedRealtime() + 60000 : state.getLong("resend_at", 0);
        updateCountdown();
        verify.setOnClickListener(v -> {
            String value = code.getText().toString().trim();
            if (!value.matches("\\d{6}")) { Toast.makeText(this,"Mã phải gồm 6 chữ số.",Toast.LENGTH_SHORT).show(); return; }
            verify.setEnabled(false); resend.setEnabled(false);
            BackendApi.run(this, () -> BackendApi.send("/auth/email-verification/confirm", "POST", "application/json", new JSONObject().put("email",email).put("code",value).toString(), null), result -> {
                startActivity(new Intent(this, RegisterSuccessActivity.class)); finish();
            }, error -> { verify.setEnabled(true); updateCountdown(); Toast.makeText(this,error,Toast.LENGTH_LONG).show(); });
        });
        resend.setOnClickListener(v -> {
            resend.setEnabled(false);
            BackendApi.run(this, () -> BackendApi.send("/auth/email-verification/resend", "POST", "application/json", new JSONObject().put("email",email).toString(), null), result -> {
                resendAt=android.os.SystemClock.elapsedRealtime()+60000; updateCountdown(); Toast.makeText(this,"Yêu cầu đã được tiếp nhận. Hãy kiểm tra email sau ít phút.",Toast.LENGTH_LONG).show();
            }, error -> { updateCountdown(); Toast.makeText(this,error,Toast.LENGTH_LONG).show(); });
        });
    }
    private void updateCountdown() {
        if(timer!=null) timer.cancel();
        long remaining=resendAt-android.os.SystemClock.elapsedRealtime();
        if(remaining<=0){resendButton.setEnabled(true);resendButton.setText("Gửi lại mã");return;}
        resendButton.setEnabled(false);
        timer=new android.os.CountDownTimer(remaining,1000){
            public void onTick(long millis){resendButton.setText("Gửi lại sau " + ((millis+999)/1000) + " giây");}
            public void onFinish(){resendButton.setText("Gửi lại mã");resendButton.setEnabled(true);}
        }.start();
    }
    @Override protected void onSaveInstanceState(Bundle out){out.putLong("resend_at",resendAt);super.onSaveInstanceState(out);}
    @Override protected void onDestroy(){if(timer!=null)timer.cancel();super.onDestroy();}
}
