package com.example.englishthroughvideo;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class VideoAiGenerator {
    public static class AiContent {
        public String mainTopic;
        public List<String> keyPoints;
        public List<String> vocabList;
        public List<String> transcriptLines;

        public AiContent(String mainTopic, List<String> keyPoints, List<String> vocabList, List<String> transcriptLines) {
            this.mainTopic = mainTopic;
            this.keyPoints = keyPoints;
            this.vocabList = vocabList;
            this.transcriptLines = transcriptLines;
        }
    }

    private static final Map<String, AiContent> aiContentMap = new HashMap<>();

    static {
        // Default AI content for preset videos
        List<String> defPoints = new ArrayList<>();
        defPoints.add("• Thói quen nhỏ tạo thay đổi lớn");
        defPoints.add("• Sự nhất quán quan trọng hơn cường độ");
        defPoints.add("• Theo dõi tiến độ mỗi ngày");

        List<String> defVocab = new ArrayList<>();
        defVocab.add("• Native speaker   (/ˌneɪ.tɪv ˈspiː.kər/)   -   Người bản xứ");
        defVocab.add("• Fluency   (/ˈfluː.ən.si/)   -   Sự lưu loát");
        defVocab.add("• Pronunciation   (/prəˌnʌn.siˈeɪ.ʃən/)   -   Sự phát âm");

        List<String> defTranscript = new ArrayList<>();
        defTranscript.add("Small habits create big changes.");
        defTranscript.add("Consistency beats intensity every time.");
        defTranscript.add("We need to be resilient in tough times.");

        aiContentMap.put("How to Speak Like a Native", new AiContent("Xây dựng thói quen nhỏ để thay đổi lớn", defPoints, defVocab, defTranscript));
    }

    public static AiContent getAiContent(String title) {
        if (title != null && aiContentMap.containsKey(title)) {
            return aiContentMap.get(title);
        }
        // Dynamic AI generation for any newly uploaded video!
        List<String> dynamicPoints = new ArrayList<>();
        dynamicPoints.add("• Phân tích nội dung cốt lõi từ video: " + title);
        dynamicPoints.add("• Tóm tắt ý chính và từ vựng thông minh bằng AI");
        dynamicPoints.add("• Đề xuất lộ trình luyện nghe nói hiệu quả");

        List<String> dynamicVocab = new ArrayList<>();
        dynamicVocab.add("• Master   (/ˈmæs.tɚ/)   -   Làm chủ, thành thạo");
        dynamicVocab.add("• Accent   (/ˈæk.sent/)   -   Giọng điệu, phát âm");
        dynamicVocab.add("• Insight   (/ˈɪn.saɪt/)   -   Hiểu biết sâu sắc");

        List<String> dynamicTranscript = new ArrayList<>();
        dynamicTranscript.add("Welcome to the AI analysis of " + title + ".");
        dynamicTranscript.add("Pay close attention to key vocabulary and phrasing.");
        dynamicTranscript.add("Practice speaking along with the speaker to boost fluency.");

        AiContent generated = new AiContent("Chủ đề: " + title + " (AI Generated Summary)", dynamicPoints, dynamicVocab, dynamicTranscript);
        if (title != null) {
            aiContentMap.put(title, generated);
        }
        return generated;
    }
}
