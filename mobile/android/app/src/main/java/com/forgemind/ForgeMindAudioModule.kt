package com.forgemind

import android.media.MediaRecorder
import android.util.Base64
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import java.io.File

class ForgeMindAudioModule(private val reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

  private var recorder: MediaRecorder? = null
  private var currentPath: String? = null

  override fun getName(): String = "ForgeMindAudioRecorder"

  @ReactMethod
  fun start(promise: Promise) {
    if (recorder != null) {
      promise.reject("already_recording", "Recording is already active")
      return
    }

    try {
      promise.resolve(startNewRecorder())
    } catch (error: Exception) {
      recorder?.release()
      recorder = null
      currentPath = null
      promise.reject("record_start_failed", error.message, error)
    }
  }

  @ReactMethod
  fun getMaxAmplitude(promise: Promise) {
    try {
      promise.resolve(recorder?.maxAmplitude ?: 0)
    } catch (error: Exception) {
      promise.reject("amplitude_failed", error.message, error)
    }
  }

  @ReactMethod
  fun rotateChunk(promise: Promise) {
    val activeRecorder = recorder
    val path = currentPath
    if (activeRecorder == null || path == null) {
      promise.reject("not_recording", "No active recording")
      return
    }

    try {
      activeRecorder.stop()
      activeRecorder.release()
      recorder = null
      currentPath = null
      startNewRecorder()
      promise.resolve(path)
    } catch (error: Exception) {
      recorder = null
      currentPath = null
      promise.reject("chunk_rotate_failed", error.message, error)
    }
  }

  @ReactMethod
  fun stop(promise: Promise) {
    val activeRecorder = recorder
    val path = currentPath
    if (activeRecorder == null || path == null) {
      promise.reject("not_recording", "No active recording")
      return
    }

    try {
      activeRecorder.stop()
      activeRecorder.release()
      promise.resolve(path)
    } catch (error: Exception) {
      promise.reject("record_stop_failed", error.message, error)
    } finally {
      recorder = null
      currentPath = null
    }
  }

  @ReactMethod
  fun cancel(promise: Promise) {
    val path = currentPath
    try {
      recorder?.release()
      if (path != null) {
        File(path).delete()
      }
      promise.resolve(null)
    } catch (error: Exception) {
      promise.reject("record_cancel_failed", error.message, error)
    } finally {
      recorder = null
      currentPath = null
    }
  }

  @ReactMethod
  fun readBase64(path: String, promise: Promise) {
    try {
      val file = File(path)
      if (!file.exists()) {
        promise.reject("file_missing", "Audio file does not exist")
        return
      }
      promise.resolve(Base64.encodeToString(file.readBytes(), Base64.NO_WRAP))
    } catch (error: Exception) {
      promise.reject("read_base64_failed", error.message, error)
    }
  }

  @ReactMethod
  fun deleteFile(path: String, promise: Promise) {
    try {
      File(path).delete()
      promise.resolve(null)
    } catch (error: Exception) {
      promise.reject("delete_file_failed", error.message, error)
    }
  }

  private fun startNewRecorder(): String {
    val output = File(reactContext.cacheDir, "forgemind-voice-${System.currentTimeMillis()}.m4a")
    val mediaRecorder = MediaRecorder()
    mediaRecorder.setAudioSource(MediaRecorder.AudioSource.MIC)
    mediaRecorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
    mediaRecorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
    mediaRecorder.setAudioChannels(1)
    mediaRecorder.setAudioEncodingBitRate(96000)
    mediaRecorder.setAudioSamplingRate(24000)
    mediaRecorder.setOutputFile(output.absolutePath)
    mediaRecorder.prepare()
    mediaRecorder.start()
    recorder = mediaRecorder
    currentPath = output.absolutePath
    return output.absolutePath
  }
}
