// Gemini API Translation Service
// Translates the entire site in a SINGLE API call by flattening and batching

const GEMINI_API_KEY = import.meta.env.VITE_GEMINI_API_KEY;
const GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent';

// Cache for translated content
const translationCache = new Map();

/**
 * Flatten a nested object into a flat object with dot-notation keys
 * Example: { a: { b: "hello" } } => { "a.b": "hello" }
 */
function flattenObject(obj, prefix = '') {
    const result = {};

    for (const [key, value] of Object.entries(obj)) {
        const newKey = prefix ? `${prefix}.${key}` : key;

        if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
            Object.assign(result, flattenObject(value, newKey));
        } else if (typeof value === 'string') {
            result[newKey] = value;
        }
        // Skip non-string primitives and arrays for simplicity
    }

    return result;
}

/**
 * Unflatten a flat object back to nested structure
 * Example: { "a.b": "hello" } => { a: { b: "hello" } }
 */
function unflattenObject(flat) {
    const result = {};

    for (const [key, value] of Object.entries(flat)) {
        const parts = key.split('.');
        let current = result;

        for (let i = 0; i < parts.length - 1; i++) {
            if (!current[parts[i]]) {
                current[parts[i]] = {};
            }
            current = current[parts[i]];
        }

        current[parts[parts.length - 1]] = value;
    }

    return result;
}

/**
 * Animated progress simulator - makes the progress bar feel more dynamic
 * Progressively increases, pauses at 67%, then climbs to 87% and stays there
 */
function createProgressSimulator(onProgress) {
    let currentProgress = 0;
    let intervalId = null;
    let isPaused = false;

    const simulate = () => {
        if (isPaused) return;

        if (currentProgress < 15) {
            // Fast initial progress
            currentProgress += 2;
        } else if (currentProgress < 45) {
            // Slower middle section
            currentProgress += 1;
        } else if (currentProgress < 67) {
            // Even slower approaching 67%
            currentProgress += 0.5;
        } else if (currentProgress === 67) {
            // Pause at 67% for 2 seconds
            isPaused = true;
            setTimeout(() => {
                isPaused = false;
            }, 2000);
            currentProgress += 0.1;
        } else if (currentProgress < 87) {
            // Climb slowly to 87%
            currentProgress += 0.3;
        }
        // Stop at 87% - will stay there until real completion

        currentProgress = Math.min(currentProgress, 87);
        onProgress(Math.round(currentProgress));
    };

    return {
        start: () => {
            currentProgress = 0;
            onProgress(0);
            intervalId = setInterval(simulate, 100);
        },
        stop: () => {
            if (intervalId) {
                clearInterval(intervalId);
                intervalId = null;
            }
        },
        complete: () => {
            if (intervalId) {
                clearInterval(intervalId);
                intervalId = null;
            }
            // Smooth completion from current to 100
            const finishAnimation = () => {
                if (currentProgress < 100) {
                    currentProgress += 3;
                    currentProgress = Math.min(currentProgress, 100);
                    onProgress(Math.round(currentProgress));
                    if (currentProgress < 100) {
                        setTimeout(finishAnimation, 50);
                    }
                }
            };
            finishAnimation();
        }
    };
}

/**
 * Translate entire translation object in ONE API call
 * @param {object} baseTranslations - The full English translations object
 * @param {string} targetLanguage - Target language code
 * @param {string} targetLanguageName - Full name of the target language
 * @param {function} onProgress - Progress callback
 * @returns {Promise<object>} - Translated object with same structure
 */
export async function translateFullTranslationObject(baseTranslations, targetLanguage, targetLanguageName, onProgress) {
    if (!GEMINI_API_KEY) {
        console.error('Gemini API key not found. Please set VITE_GEMINI_API_KEY in .env');
        return baseTranslations;
    }

    // Check cache first
    const cacheKey = `full_${targetLanguage}`;
    if (translationCache.has(cacheKey)) {
        if (onProgress) onProgress(100);
        return translationCache.get(cacheKey);
    }

    // Create progress simulator for smooth animation
    const progressSimulator = onProgress ? createProgressSimulator(onProgress) : null;

    try {
        // Start the progress animation
        if (progressSimulator) progressSimulator.start();

        // Step 1: Flatten the entire translations object
        const flattened = flattenObject(baseTranslations);
        const keys = Object.keys(flattened);
        const values = Object.values(flattened);

        // Step 2: Create a numbered list for translation (more reliable than JSON)
        // Format: [1] Original text
        //         [2] Another text
        const numberedTexts = values.map((text, i) => `[${i + 1}] ${text}`).join('\n');

        // Step 3: Make ONE API call with all texts
        const response = await fetch(`${GEMINI_API_URL}?key=${GEMINI_API_KEY}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                contents: [{
                    parts: [{
                        text: `You are a professional translator. Translate ALL of the following ${values.length} texts from English to ${targetLanguageName}.

CRITICAL RULES:
1. Return EXACTLY ${values.length} translations, one per line
2. Each line MUST start with the number in brackets like [1], [2], etc.
3. Preserve ALL special characters: {}, [], →, •, ⚠️, 🔐, &, etc.
4. Keep placeholders like {category}, {count} EXACTLY as they are - do NOT translate them
5. Maintain the same tone and formality
6. Do NOT add any extra text, explanations, or notes
7. Do NOT skip any items - translate ALL ${values.length} texts

Here are the texts to translate:

${numberedTexts}`
                    }]
                }],
                generationConfig: {
                    temperature: 0.1,
                    topP: 0.95,
                    topK: 40,
                    maxOutputTokens: 65536,
                }
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Gemini API error: ${response.status} - ${errorText}`);
        }

        const data = await response.json();
        const translatedContent = data.candidates?.[0]?.content?.parts?.[0]?.text || '';

        // Step 4: Parse the numbered response
        const translatedValues = parseNumberedResponse(translatedContent, values.length, values);

        // Step 5: Rebuild the flattened object with translated values
        const translatedFlat = {};
        keys.forEach((key, i) => {
            translatedFlat[key] = translatedValues[i] || flattened[key]; // Fallback to original if missing
        });

        // Step 6: Unflatten back to nested structure
        const result = unflattenObject(translatedFlat);

        // Cache the result
        translationCache.set(cacheKey, result);

        // Complete the progress animation smoothly
        if (progressSimulator) progressSimulator.complete();

        return result;

    } catch (error) {
        console.error('Translation error:', error);
        if (progressSimulator) progressSimulator.stop();
        if (onProgress) onProgress(100);
        return baseTranslations; // Return original on error
    }
}

/**
 * Parse numbered response from Gemini
 * Handles various formats: [1] text, 1. text, 1) text, etc.
 */
function parseNumberedResponse(content, expectedCount, originalValues) {
    const results = new Array(expectedCount).fill(null);
    const lines = content.split('\n');

    let currentNumber = null;
    let currentText = '';

    for (const line of lines) {
        // Try to match [N] format first (most reliable)
        const bracketMatch = line.match(/^\s*\[(\d+)\]\s*(.*)$/);
        // Also try N. or N) formats
        const dotMatch = line.match(/^\s*(\d+)[.)]\s*(.*)$/);

        const match = bracketMatch || dotMatch;

        if (match) {
            // Save previous if exists
            if (currentNumber !== null && currentNumber >= 1 && currentNumber <= expectedCount) {
                results[currentNumber - 1] = currentText.trim();
            }

            currentNumber = parseInt(match[1]);
            currentText = match[2];
        } else if (currentNumber !== null) {
            // Continuation of previous line
            currentText += ' ' + line.trim();
        }
    }

    // Don't forget the last one
    if (currentNumber !== null && currentNumber >= 1 && currentNumber <= expectedCount) {
        results[currentNumber - 1] = currentText.trim();
    }

    // Fill any missing with originals
    for (let i = 0; i < expectedCount; i++) {
        if (!results[i] || results[i].trim() === '') {
            results[i] = originalValues[i];
        }
    }

    return results;
}

/**
 * Clear the translation cache
 */
export function clearTranslationCache() {
    translationCache.clear();
}

/**
 * Get cache statistics
 */
export function getCacheStats() {
    return {
        size: translationCache.size,
        keys: Array.from(translationCache.keys()),
    };
}

export default {
    translateFullTranslationObject,
    clearTranslationCache,
    getCacheStats,
};
