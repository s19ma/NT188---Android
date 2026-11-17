package com.example.englishthroughvideo;

import org.junit.Test;
import static org.junit.Assert.assertEquals;

public class FlashcardIntervalPreviewTest {
    @Test public void intervalsAreFixedRegardlessOfCardHistory() {
        for (int repetitions : new int[]{0, 1, 4, 8}) {
            assertEquals(1, FlashcardIntervalPreview.days(repetitions, 20, 2.5, "hard"));
            assertEquals(3, FlashcardIntervalPreview.days(repetitions, 20, 2.5, "good"));
            assertEquals(7, FlashcardIntervalPreview.days(repetitions, 20, 2.5, "easy"));
        }
    }

    @Test public void legacyServerUsesItsExistingSm2Intervals() {
        assertEquals(1, FlashcardIntervalPreview.legacyDays(0, 0, 2.5, "easy"));
        assertEquals(6, FlashcardIntervalPreview.legacyDays(1, 1, 2.5, "good"));
        assertEquals(14, FlashcardIntervalPreview.legacyDays(2, 6, 2.5, "hard"));
        assertEquals(15, FlashcardIntervalPreview.legacyDays(2, 6, 2.5, "good"));
        assertEquals(16, FlashcardIntervalPreview.legacyDays(2, 6, 2.5, "easy"));
    }
}
