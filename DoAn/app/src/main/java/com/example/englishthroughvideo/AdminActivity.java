package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Toast;
import org.json.JSONObject;
import androidx.appcompat.app.AppCompatActivity;

public class AdminActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_20_admin_qu_n_tr);

        View rootView = findViewById(android.R.id.content);
        if (rootView != null) {
            rootView.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    if (BackendApi.token == null) return;
                    BackendApi.run(AdminActivity.this, () -> (JSONObject) BackendApi.send(
                            "/admin/overview", "GET", null, null, BackendApi.token), result -> {
                        String summary = "Người dùng: " + result.optInt("total_users")
                                + "\nVideo published: " + result.optInt("published_videos")
                                + "\nVideo draft: " + result.optInt("draft_videos")
                                + "\nLượt làm quiz: " + result.optInt("quiz_attempts");
                        Toast.makeText(AdminActivity.this, summary, Toast.LENGTH_LONG).show();
                        startActivity(new Intent(AdminActivity.this, AdminVideoManagementActivity.class));
                    });
                }
            });
        }
    }
}
