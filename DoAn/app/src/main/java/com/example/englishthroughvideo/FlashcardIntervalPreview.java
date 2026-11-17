package com.example.englishthroughvideo;

import java.math.BigDecimal;
import java.math.RoundingMode;
/** Display-only preview of the backend's fixed rating intervals. */
final class FlashcardIntervalPreview {
    private FlashcardIntervalPreview() { }

    static int days(int repetitions, int intervalDays, double easeFactor, String rating) {
        switch (rating) {
            case "hard": return 1;
            case "good": return 3;
            case "easy": return 7;
            default: throw new IllegalArgumentException("Unsupported rating");
        }
    }

    static int legacyDays(int repetitions, int intervalDays, double easeFactor, String rating) {
        if (repetitions <= 0) return 1;
        if (repetitions == 1) return 6;
        BigDecimal delta;
        switch (rating) {
            case "hard": delta = new BigDecimal("-0.22"); break;
            case "good": delta = BigDecimal.ZERO; break;
            case "easy": delta = new BigDecimal("0.10"); break;
            default: throw new IllegalArgumentException("Unsupported rating");
        }
        BigDecimal ease = BigDecimal.valueOf(easeFactor).add(delta)
                .max(new BigDecimal("1.30")).setScale(2, RoundingMode.HALF_UP);
        return Math.max(1, BigDecimal.valueOf(intervalDays).multiply(ease)
                .setScale(0, RoundingMode.HALF_UP).intValue());
    }
}
