/**
 * voice-processor.js — AudioWorklet processor for voice capture.
 *
 * Runs on a dedicated audio thread (not main thread), eliminating
 * jank and audio glitches. Downsamples from browser sample rate
 * to 16 kHz mono PCM and performs energy-based VAD (Voice Activity
 * Detection) to suppress silent frames.
 *
 * Messages TO main thread:
 *   { type: 'audio', pcm16: Int16Array }  — voice-active audio chunk
 *   { type: 'energy', rms: number }       — current RMS energy (0–1)
 *   { type: 'silence' }                   — silence detected
 *   { type: 'speech' }                    — speech started
 *
 * Messages FROM main thread:
 *   { type: 'init', sampleRate: number }  — set source sample rate
 *   { type: 'mute', muted: boolean }      — mute/unmute mic
 *   { type: 'set_vad_threshold', threshold: number } — adjust VAD sensitivity
 */
class VoiceProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this._sourceSampleRate = 48000;
        this._muted = false;
        this._vadThreshold = 0.008; // RMS energy threshold for speech
        this._isSpeaking = false;
        this._silenceFrames = 0;
        this._speechFrames = 0;
        // Buffer to accumulate ~100ms of audio before sending
        this._buffer = new Float32Array(0);
        this._bufferTarget = 4800; // ~100ms at 48kHz

        this.port.onmessage = (e) => {
            const msg = e.data;
            if (msg.type === 'init') {
                this._sourceSampleRate = msg.sampleRate || 48000;
                this._bufferTarget = Math.round(this._sourceSampleRate * 0.1); // 100ms
            } else if (msg.type === 'mute') {
                this._muted = msg.muted;
            } else if (msg.type === 'set_vad_threshold') {
                this._vadThreshold = msg.threshold;
            }
        };
    }

    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (!input || !input[0] || input[0].length === 0) return true;

        const channelData = input[0]; // mono

        // Compute RMS energy
        let sumSq = 0;
        for (let i = 0; i < channelData.length; i++) {
            sumSq += channelData[i] * channelData[i];
        }
        const rms = Math.sqrt(sumSq / channelData.length);

        // Send energy for visualization every frame (~2.67ms at 128 samples)
        this.port.postMessage({ type: 'energy', rms });

        // VAD: detect speech vs silence
        if (rms > this._vadThreshold) {
            this._speechFrames++;
            this._silenceFrames = 0;
            if (!this._isSpeaking && this._speechFrames >= 3) {
                this._isSpeaking = true;
                this.port.postMessage({ type: 'speech' });
            }
        } else {
            this._silenceFrames++;
            this._speechFrames = 0;
            if (this._isSpeaking && this._silenceFrames >= 30) { // ~80ms silence
                this._isSpeaking = false;
                this.port.postMessage({ type: 'silence' });
            }
        }

        // If muted or silent, skip sending audio
        if (this._muted || !this._isSpeaking) return true;

        // Accumulate into buffer
        const newBuf = new Float32Array(this._buffer.length + channelData.length);
        newBuf.set(this._buffer);
        newBuf.set(channelData, this._buffer.length);
        this._buffer = newBuf;

        // Once we have enough (~100ms), downsample and send
        if (this._buffer.length >= this._bufferTarget) {
            const pcm16 = this._downsampleTo16k(this._buffer);
            this.port.postMessage({ type: 'audio', pcm16 }, [pcm16.buffer]);
            this._buffer = new Float32Array(0);
        }

        return true;
    }

    /**
     * Downsample Float32 from source rate to 16kHz, convert to Int16.
     */
    _downsampleTo16k(float32) {
        const ratio = this._sourceSampleRate / 16000;
        const newLen = Math.round(float32.length / ratio);
        const result = new Int16Array(newLen);
        for (let i = 0; i < newLen; i++) {
            const idx = Math.round(i * ratio);
            const s = Math.max(-1, Math.min(1, float32[idx] || 0));
            result[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return result;
    }
}

registerProcessor('voice-processor', VoiceProcessor);
