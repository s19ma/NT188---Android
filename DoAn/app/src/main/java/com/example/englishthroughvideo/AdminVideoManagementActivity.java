package com.example.englishthroughvideo;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.widget.*;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.InputStream;

/** Admin-only content workflow: draft metadata -> assets -> summary -> publish. */
public class AdminVideoManagementActivity extends AppCompatActivity {
    private static final int PICK_VIDEO=1, PICK_THUMB=2, PICK_SRT=3;
    private EditText title, description, category, level, duration, summary, points;
    private TextView status, selected;
    private String videoId; private Uri videoUri, thumbUri, subtitleUri;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state); buildScreen();
        if (state == null) loadVideos();
        else {
            videoId=state.getString("videoId"); videoUri=state.getParcelable("videoUri"); thumbUri=state.getParcelable("thumbUri"); subtitleUri=state.getParcelable("subtitleUri");
            EditText[] fields={title,description,category,level,duration,summary,points};
            for(int i=0;i<fields.length;i++) fields[i].setText(state.getString("field"+i, ""));
            status.setText(state.getString("status", "Chọn hoặc tạo video.")); selected.setText(state.getString("selected", "Chưa chọn file."));
        }
    }

    @Override protected void onSaveInstanceState(Bundle state) {
        state.putString("videoId",videoId); state.putParcelable("videoUri",videoUri); state.putParcelable("thumbUri",thumbUri); state.putParcelable("subtitleUri",subtitleUri);
        EditText[] fields={title,description,category,level,duration,summary,points};
        for(int i=0;i<fields.length;i++) state.putString("field"+i,fields[i].getText().toString());
        state.putString("status",status.getText().toString()); state.putString("selected",selected.getText().toString());
        super.onSaveInstanceState(state);
    }

    private void buildScreen() {
        ScrollView scroll = new ScrollView(this); LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL); int pad=(int)(16*getResources().getDisplayMetrics().density); root.setPadding(pad,pad,pad,pad); scroll.addView(root);
        TextView heading = text("Quản lý video", 24); root.addView(heading);
        status = text("Đang tải danh sách…", 14); root.addView(status);
        LinearLayout content = new LinearLayout(this);
        boolean landscape = getResources().getConfiguration().orientation == android.content.res.Configuration.ORIENTATION_LANDSCAPE;
        content.setOrientation(landscape ? LinearLayout.HORIZONTAL : LinearLayout.VERTICAL); root.addView(content);
        LinearLayout metadataColumn=new LinearLayout(this), assetsColumn=new LinearLayout(this);
        metadataColumn.setOrientation(LinearLayout.VERTICAL); assetsColumn.setOrientation(LinearLayout.VERTICAL);
        if (landscape) {
            content.addView(metadataColumn,new LinearLayout.LayoutParams(0,-2,1f));
            LinearLayout.LayoutParams right=new LinearLayout.LayoutParams(0,-2,1f); right.setMarginStart(pad); content.addView(assetsColumn,right);
        } else { content.addView(metadataColumn); content.addView(assetsColumn); }
        Button choose=button("Chọn / sửa video đã có"); choose.setOnClickListener(v->loadVideos()); metadataColumn.addView(choose);
        Button draft=button("Tạo video nháp mới"); draft.setOnClickListener(v->createDraft()); metadataColumn.addView(draft);
        title=input("Tiêu đề video"); description=input("Mô tả"); category=input("Chủ đề / category"); level=input("CEFR: A1, A2, B1, B2, C1, C2"); duration=input("Thời lượng (giây, tùy chọn)");
        metadataColumn.addView(title); metadataColumn.addView(description); metadataColumn.addView(category); metadataColumn.addView(level); metadataColumn.addView(duration);
        Button save=button("Lưu metadata"); save.setOnClickListener(v->saveMetadata()); metadataColumn.addView(save);
        summary=input("Tóm tắt ngắn (tùy chọn)"); points=input("Các ý chính, mỗi dòng một ý");
        Button saveSummary=button("Lưu tóm tắt"); saveSummary.setOnClickListener(v->saveSummary());
        if (landscape) { metadataColumn.addView(summary); metadataColumn.addView(points); metadataColumn.addView(saveSummary); }
        selected=text("Chưa chọn file.", 13); assetsColumn.addView(selected);
        Button pickVideo=button("Chọn file video"); pickVideo.setOnClickListener(v->pick(PICK_VIDEO,"video/*")); assetsColumn.addView(pickVideo);
        Button pickThumb=button("Chọn thumbnail (JPG/PNG/WebP)"); pickThumb.setOnClickListener(v->pick(PICK_THUMB,"image/*")); assetsColumn.addView(pickThumb);
        Button pickSrt=button("Chọn phụ đề SRT"); pickSrt.setOnClickListener(v->pick(PICK_SRT,"application/x-subrip")); assetsColumn.addView(pickSrt);
        Button upload=button("Tải các file đã chọn"); upload.setOnClickListener(v->uploadAssets()); assetsColumn.addView(upload);
        if (!landscape) { assetsColumn.addView(summary); assetsColumn.addView(points); assetsColumn.addView(saveSummary); }
        Button publish=button("Xuất bản video"); publish.setOnClickListener(v->publish()); assetsColumn.addView(publish);
        setContentView(scroll);
    }
    private TextView text(String value,int size){ TextView v=new TextView(this); v.setText(value); v.setTextSize(size); v.setPadding(0,8,0,8); return v; }
    private EditText input(String hint){ EditText v=new EditText(this); v.setHint(hint); v.setMinLines(1); return v; }
    private Button button(String label){ Button b=new Button(this); b.setText(label); return b; }
    private void pick(int code,String type){ Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT); i.setType(type); i.addCategory(Intent.CATEGORY_OPENABLE); startActivityForResult(i,code); }

    private void loadVideos(){
        if(BackendApi.token==null){ status.setText("Bạn cần đăng nhập admin."); return; }
        status.setText("Đang tải video…"); BackendApi.run(this,()->(JSONArray)BackendApi.send("/admin/videos?limit=100","GET",null,null,BackendApi.token), rows->{
            status.setText("Chọn video hoặc tạo bản nháp mới."); String[] labels=new String[rows.length()];
            for(int i=0;i<rows.length();i++){ JSONObject item=rows.optJSONObject(i); labels[i]=item.optString("title")+" · "+item.optString("status"); }
            new AlertDialog.Builder(this).setTitle("Video quản trị").setItems(labels,(d,which)->loadIntoForm(rows.optJSONObject(which))).show();
        }, error->status.setText(error));
    }
    private void loadIntoForm(JSONObject v){ if(v==null)return; videoId=v.optString("id"); title.setText(v.optString("title")); description.setText(v.optString("description")); category.setText(v.optString("category")); level.setText(v.optString("cefr_level")); duration.setText(v.has("duration_seconds")?String.valueOf(v.optInt("duration_seconds")):""); status.setText("Đang chỉnh sửa: "+title.getText()); }
    private JSONObject metadata() throws Exception { JSONObject p=new JSONObject().put("title",title.getText().toString().trim()).put("description",description.getText().toString().trim()).put("category",category.getText().toString().trim()); String lv=level.getText().toString().trim(); if(!lv.isEmpty())p.put("cefr_level",lv); String d=duration.getText().toString().trim(); if(!d.isEmpty())p.put("duration_seconds",Integer.parseInt(d)); return p; }
    private void createDraft(){ BackendApi.run(this,()->(JSONObject)BackendApi.send("/admin/videos","POST","application/json",metadata().toString(),BackendApi.token),this::loadIntoForm,error->status.setText(error)); }
    private void saveMetadata(){ if(videoId==null){createDraft();return;} BackendApi.run(this,()->(JSONObject)BackendApi.send("/admin/videos/"+videoId,"PATCH","application/json",metadata().toString(),BackendApi.token),this::loadIntoForm,error->status.setText(error)); }
    private void uploadAssets(){ if(videoId==null){status.setText("Hãy tạo hoặc chọn video trước.");return;} if(videoUri==null&&thumbUri==null&&subtitleUri==null){status.setText("Chưa chọn file nào.");return;} status.setText("Đang tải file lên Azure…"); BackendApi.run(this,()->{ if(videoUri!=null)upload(videoUri,"/admin/videos/"+videoId+"/upload-video"); if(thumbUri!=null)upload(thumbUri,"/admin/videos/"+videoId+"/upload-thumbnail"); if(subtitleUri!=null)upload(subtitleUri,"/admin/videos/"+videoId+"/upload-subtitle"); return "Đã tải file và đồng bộ phụ đề.";},result->status.setText(result),error->status.setText(error)); }
    private void upload(Uri uri,String path) throws Exception { String name=uri.getLastPathSegment(); String mime=getContentResolver().getType(uri); if(mime==null)mime="application/octet-stream"; InputStream input=getContentResolver().openInputStream(uri); if(input==null)throw new IllegalStateException("Không thể đọc file."); BackendApi.sendMultipart(path,"file",name==null?"upload":name,mime,input,BackendApi.token); }
    private void saveSummary(){ if(videoId==null){status.setText("Hãy tạo hoặc chọn video trước.");return;} String[] lines=points.getText().toString().split("\\n"); JSONArray keys=new JSONArray(); for(String line:lines)if(!line.trim().isEmpty())keys.put(line.trim()); if(keys.length()==0){status.setText("Nhập ít nhất một ý chính.");return;} BackendApi.run(this,()->(JSONObject)BackendApi.send("/admin/videos/"+videoId+"/summary","PUT","application/json",new JSONObject().put("summary_text",summary.getText().toString().trim()).put("key_points",keys).put("source","manual").toString(),BackendApi.token),r->status.setText("Đã lưu tóm tắt."),e->status.setText(e)); }
    private void publish(){ if(videoId==null){status.setText("Hãy tạo hoặc chọn video trước.");return;} BackendApi.run(this,()->(JSONObject)BackendApi.send("/admin/videos/"+videoId+"/publish","POST",null,null,BackendApi.token),r->{status.setText("Đã xuất bản. Android sẽ nhận video khi tải lại thư viện.");loadIntoForm(r);},e->status.setText(e)); }
    @Override protected void onActivityResult(int code,int result,@Nullable Intent data){ super.onActivityResult(code,result,data); if(result!=RESULT_OK||data==null||data.getData()==null)return; Uri uri=data.getData(); if(code==PICK_VIDEO)videoUri=uri; else if(code==PICK_THUMB)thumbUri=uri; else if(code==PICK_SRT)subtitleUri=uri; selected.setText("Đã chọn: "+uri.getLastPathSegment()); }
}
