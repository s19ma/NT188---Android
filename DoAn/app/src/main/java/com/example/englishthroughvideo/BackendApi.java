package com.example.englishthroughvideo;

import android.app.Activity;
import android.widget.Toast;
import org.json.JSONObject;
import org.json.JSONTokener;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

final class BackendApi {
    private static final ExecutorService NETWORK = Executors.newFixedThreadPool(3);
    static String token;

    interface Request<T> { T run() throws Exception; }
    interface Success<T> { void accept(T result); }

    static <T> void run(Activity activity, Request<T> request, Success<T> success) {
        run(activity, request, success,
                error -> Toast.makeText(activity, error, Toast.LENGTH_LONG).show());
    }

    static <T> void run(Activity activity, Request<T> request, Success<T> success,
                        Success<String> failure) {
        NETWORK.execute(() -> {
            try {
                T result = request.run();
                activity.runOnUiThread(() -> {
                    if (!activity.isFinishing() && !activity.isDestroyed()) success.accept(result);
                });
            } catch (Exception error) {
                String message = error instanceof ApiException ? error.getMessage()
                        : "Không thể kết nối hoặc đọc dữ liệu từ máy chủ.";
                activity.runOnUiThread(() -> {
                    if (error instanceof ApiException && ((ApiException) error).status == 401) {
                        token = null;
                        SessionManager.clear(activity);
                    }
                    if (!activity.isFinishing() && !activity.isDestroyed()) failure.accept(message);
                });
            }
        });
    }

    static Object send(String path, String method, String type, String body, String bearer)
            throws Exception {
        if (BuildConfig.API_BASE_URL.isEmpty()) {
            throw new ApiException(0, "Ứng dụng chưa được cấu hình địa chỉ API.");
        }
        HttpURLConnection connection = (HttpURLConnection)
                new URL(BuildConfig.API_BASE_URL + "/api/v1" + path).openConnection();
        try {
            connection.setInstanceFollowRedirects(false);
            connection.setRequestMethod(method);
            connection.setConnectTimeout(12000);
            connection.setReadTimeout(15000);
            connection.setRequestProperty("Accept", "application/json");
            if (bearer != null) connection.setRequestProperty("Authorization", "Bearer " + bearer);
            if (body != null) {
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", type);
                try (OutputStream output = connection.getOutputStream()) {
                    output.write(body.getBytes(StandardCharsets.UTF_8));
                }
            }
            int status = connection.getResponseCode();
            if (status < 200 || status >= 300) {
                String message = "Máy chủ trả về lỗi HTTP " + status + ".";
                InputStream errorStream = connection.getErrorStream();
                if (errorStream != null) {
                    try (InputStream input = errorStream) {
                        ByteArrayOutputStream output = new ByteArrayOutputStream();
                        byte[] buffer = new byte[1024];
                        int count;
                        while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                        Object payload = new JSONTokener(output.toString("UTF-8")).nextValue();
                        if (payload instanceof JSONObject) {
                            String detail = ((JSONObject) payload).optString("detail");
                            if (!detail.isEmpty()) message = detail;
                        }
                    } catch (Exception ignored) { }
                }
                if (status == 401) message = "Sai email, mật khẩu hoặc phiên đăng nhập đã hết hạn.";
                if (status == 409 && !path.startsWith("/users/me/flashcards/")) message = "Email này đã được đăng ký.";
                if (status == 422) message = "Dữ liệu nhập chưa hợp lệ.";
                throw new ApiException(status, message);
            }
            try (InputStream input = connection.getInputStream()) {
                ByteArrayOutputStream output = new ByteArrayOutputStream();
                byte[] buffer = new byte[4096];
                int count;
                while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                if (output.size() == 0) return JSONObject.NULL;
                return new JSONTokener(output.toString("UTF-8")).nextValue();
            }
        } finally {
            connection.disconnect();
        }
    }

    /** Read the authenticated server clock; never use the device clock to decide due status. */
    static long flashcardServerTime(String bearer) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(BuildConfig.API_BASE_URL + "/api/v1/users/me/flashcards/overview").openConnection();
        try {
            connection.setConnectTimeout(12000); connection.setReadTimeout(15000);
            connection.setRequestProperty("Authorization", "Bearer " + bearer);
            int status = connection.getResponseCode();
            if (status != 200) throw new ApiException(status, "Không thể đồng bộ phiên ôn tập.");
            long date = connection.getHeaderFieldDate("Date", -1);
            if (date < 0) throw new IOException("Server clock unavailable");
            try (InputStream in = connection.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[2048]; int n;
                while ((n = in.read(buffer)) != -1) out.write(buffer, 0, n);
                JSONObject overview = new JSONObject(out.toString("UTF-8"));
                if (!overview.optBoolean("idempotent_review_supported", false))
                    throw new ApiException(0, "Máy chủ chưa hỗ trợ khôi phục phiên an toàn.");
            }
            return date;
        } finally { connection.disconnect(); }
    }

    /** Streams one multipart file to the protected admin upload APIs. */
    static Object sendMultipart(String path, String fieldName, String filename, String mimeType,
                                InputStream input, String bearer) throws Exception {
        String boundary = "----EnglishVideo" + System.nanoTime();
        HttpURLConnection connection = (HttpURLConnection) new URL(BuildConfig.API_BASE_URL + "/api/v1" + path).openConnection();
        try {
            connection.setRequestMethod("POST"); connection.setConnectTimeout(12000); connection.setReadTimeout(60000);
            connection.setDoOutput(true); connection.setChunkedStreamingMode(8192);
            connection.setRequestProperty("Accept", "application/json");
            connection.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
            if (bearer != null) connection.setRequestProperty("Authorization", "Bearer " + bearer);
            try (OutputStream output = connection.getOutputStream(); InputStream source = input) {
                String header = "--" + boundary + "\r\nContent-Disposition: form-data; name=\"" + fieldName
                        + "\"; filename=\"" + filename.replace("\"", "") + "\"\r\nContent-Type: " + mimeType + "\r\n\r\n";
                output.write(header.getBytes(StandardCharsets.UTF_8));
                byte[] buffer = new byte[8192]; int count;
                while ((count = source.read(buffer)) != -1) output.write(buffer, 0, count);
                output.write(("\r\n--" + boundary + "--\r\n").getBytes(StandardCharsets.UTF_8));
            }
            int status = connection.getResponseCode();
            if (status < 200 || status >= 300) throw new ApiException(status, "Máy chủ trả về lỗi HTTP " + status + ".");
            try (InputStream response = connection.getInputStream()) {
                ByteArrayOutputStream output = new ByteArrayOutputStream(); byte[] buffer = new byte[4096]; int count;
                while ((count = response.read(buffer)) != -1) output.write(buffer, 0, count);
                return output.size() == 0 ? JSONObject.NULL : new JSONTokener(output.toString("UTF-8")).nextValue();
            }
        } finally { connection.disconnect(); }
    }

    static final class ApiException extends IOException {
        final int status;

        ApiException(int status, String message) {
            super(message);
            this.status = status;
        }
    }
}
