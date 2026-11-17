package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Toast;
import org.json.JSONObject;
import androidx.appcompat.app.AppCompatActivity;

public class AdminReportActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_29_danh_s_ch_b_o_c_o_admin);

        View rootView = findViewById(android.R.id.content);
        if (rootView != null) {
            rootView.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    BackendApi.run(AdminReportActivity.this, () -> (JSONObject) BackendApi.send(
                            "/admin/overview", "GET", null, null, BackendApi.token), result -> {
                        Toast.makeText(AdminReportActivity.this,
                                "Users: " + result.optInt("total_users") + " · Quiz: " + result.optInt("quiz_attempts"),
                                Toast.LENGTH_LONG).show();
                    });
                }
            });
        }
    }
}
