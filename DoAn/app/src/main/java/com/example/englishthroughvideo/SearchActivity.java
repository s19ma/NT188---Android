package com.example.englishthroughvideo;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import androidx.appcompat.app.AppCompatActivity;

public class SearchActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.layout_4_6_t_m_ki_m_t_ng_h_p);

        // Click anywhere or on root view to navigate following Figma prototype flow
        View rootView = findViewById(android.R.id.content);
        if (rootView != null) {
            rootView.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    Intent intent = new Intent(SearchActivity.this, HomeActivity.class);
                    startActivity(intent);
                }
            });
        }
    }
}
