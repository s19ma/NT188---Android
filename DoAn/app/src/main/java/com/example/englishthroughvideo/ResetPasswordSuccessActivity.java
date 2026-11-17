package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import androidx.appcompat.app.AppCompatActivity;

public class ResetPasswordSuccessActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_3_2_c_p_nh_t_m_t_kh_u_th_nh_c_ng);

        // Click anywhere or on root view to navigate following Figma prototype flow
        View rootView = findViewById(android.R.id.content);
        if (rootView != null) {
            rootView.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    Intent intent = new Intent(ResetPasswordSuccessActivity.this, LoginActivity.class);
                    startActivity(intent);
                }
            });
        }
    }
}
