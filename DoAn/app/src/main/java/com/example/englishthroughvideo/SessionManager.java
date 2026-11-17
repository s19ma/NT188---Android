package com.example.englishthroughvideo;

import android.content.Context;
import android.content.SharedPreferences;
import androidx.security.crypto.EncryptedSharedPreferences;
import androidx.security.crypto.MasterKey;

/** Stores the JWT encrypted with a key held by Android Keystore. */
final class SessionManager {
    private static final String PREFS = "english_video_session";
    private static final String TOKEN = "access_token";

    private SessionManager() {}

    static SharedPreferences preferences(Context context) throws Exception {
        MasterKey key = new MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build();
        return EncryptedSharedPreferences.create(context, PREFS, key,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM);
    }

    static String load(Context context) {
        try { return preferences(context).getString(TOKEN, null); }
        catch (Exception ignored) { return null; }
    }

    static void save(Context context, String token) {
        try { preferences(context).edit().putString(TOKEN, token).apply(); }
        catch (Exception ignored) { }
    }

    static void clear(Context context) {
        try { preferences(context).edit().remove(TOKEN).apply(); }
        catch (Exception ignored) { }
    }
}
