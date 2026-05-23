package com.forgemind

import android.media.MediaPlayer
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.ReadableArray
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import android.util.Base64
import java.util.Locale
import org.json.JSONObject

class ForgeMindTtsModule(private val reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext), TextToSpeech.OnInitListener {

  private var tts: TextToSpeech? = null
  private var player: MediaPlayer? = null
  private val handler = Handler(Looper.getMainLooper())
  private val queuedAudioFiles = mutableListOf<File>()
  private var queuedAudioComplete = true
  private var backendSpeechCacheKey: String? = null
  private var backendSpeechFormat = "aac"
  private var ready = false

  override fun getName(): String = "ForgeMindTts"

  override fun initialize() {
    super.initialize()
    tts = TextToSpeech(reactContext, this)
  }

  override fun onInit(status: Int) {
    ready = status == TextToSpeech.SUCCESS
    if (ready) {
      tts?.language = Locale.US
    }
  }

  @ReactMethod
  fun speak(text: String, promise: Promise) {
    speakTexts(listOf(text), promise)
  }

  @ReactMethod
  fun speakSegments(texts: ReadableArray, promise: Promise) {
    val segments = mutableListOf<String>()
    for (index in 0 until texts.size()) {
      val text = texts.getString(index).trim()
      if (text.isNotEmpty()) {
        segments.add(text)
      }
    }
    speakTexts(segments, promise)
  }

  @ReactMethod
  fun enqueue(text: String, promise: Promise) {
    val trimmed = text.trim()
    if (trimmed.isEmpty()) {
      promise.resolve(null)
      return
    }
    Thread {
      try {
        val audioFile = getCachedBackendSpeech(trimmed)
        reactContext.runOnUiQueueThread {
          val shouldStart = player == null && queuedAudioFiles.isEmpty()
          queuedAudioComplete = false
          queuedAudioFiles.add(audioFile)
          if (shouldStart) {
            playQueuedAudioAt(0)
          }
          queuedAudioComplete = true
          promise.resolve(null)
        }
      } catch (backendError: Exception) {
        reactContext.runOnUiQueueThread {
          if (player == null && queuedAudioFiles.isEmpty()) {
            speakWithDeviceTts(trimmed, promise)
          } else {
            promise.reject("tts_enqueue_failed", backendError.message, backendError)
          }
        }
      }
    }.start()
  }

  @ReactMethod
  fun enqueueAudioBase64(audioBase64: String, format: String, cacheKey: String, promise: Promise) {
    if (audioBase64.trim().isEmpty()) {
      promise.resolve(null)
      return
    }
    Thread {
      try {
        val extension = audioFileExtension(format)
        val audioFile = File(reactContext.cacheDir, "forgemind-ws-tts-${sha256("$format|$cacheKey")}.$extension")
        if (!audioFile.exists() || audioFile.length() == 0L) {
          val audio = Base64.decode(audioBase64, Base64.DEFAULT)
          if (audio.isEmpty()) {
            throw IllegalStateException("WebSocket speech returned empty audio")
          }
          val temporaryOutput = File(reactContext.cacheDir, "${audioFile.name}.tmp")
          temporaryOutput.writeBytes(audio)
          if (audioFile.exists()) {
            audioFile.delete()
          }
          temporaryOutput.renameTo(audioFile)
        }
        reactContext.runOnUiQueueThread {
          val shouldStart = player == null && queuedAudioFiles.isEmpty()
          queuedAudioComplete = false
          queuedAudioFiles.add(audioFile)
          if (shouldStart) {
            playQueuedAudioAt(0)
          }
          queuedAudioComplete = true
          promise.resolve(null)
        }
      } catch (error: Exception) {
        reactContext.runOnUiQueueThread {
          promise.reject("tts_enqueue_audio_failed", error.message, error)
        }
      }
    }.start()
  }

  private fun speakTexts(texts: List<String>, promise: Promise) {
    if (texts.isEmpty()) {
      promise.resolve(null)
      return
    }
    Thread {
      try {
        val firstAudioFile = getCachedBackendSpeech(texts.first())
        reactContext.runOnUiQueueThread {
          try {
            playAudioQueueStreaming(firstAudioFile)
            promise.resolve(null)
          } catch (audioError: Exception) {
            speakWithDeviceTts(texts.joinToString(" "), promise)
          }
        }
        for (text in texts.drop(1)) {
          val audioFile = getCachedBackendSpeech(text)
          reactContext.runOnUiQueueThread {
            queuedAudioFiles.add(audioFile)
          }
        }
        reactContext.runOnUiQueueThread {
          queuedAudioComplete = true
        }
      } catch (backendError: Exception) {
        reactContext.runOnUiQueueThread {
          speakWithDeviceTts(texts.joinToString(" "), promise)
        }
      }
    }.start()
  }

  private fun getCachedBackendSpeech(text: String): File {
    val cacheKey = getBackendSpeechCacheKey()
    val extension = audioFileExtension(backendSpeechFormat)
    val cacheFile = File(reactContext.cacheDir, "forgemind-tts-${sha256("$cacheKey|$text")}.$extension")
    if (cacheFile.exists() && cacheFile.length() > 0) {
      return cacheFile
    }
    return downloadBackendSpeech(text, cacheFile)
  }

  private fun getBackendSpeechCacheKey(): String {
    backendSpeechCacheKey?.let { return it }
    val fallback = "speech|${BuildConfig.API_BASE_URL}|v3"
    return try {
      val connection = URL("${BuildConfig.API_BASE_URL}/config").openConnection() as HttpURLConnection
      connection.requestMethod = "GET"
      connection.connectTimeout = 2500
      connection.readTimeout = 2500
      if (connection.responseCode !in 200..299) {
        connection.disconnect()
        backendSpeechCacheKey = fallback
        fallback
      } else {
        val body = connection.inputStream.bufferedReader().use { it.readText() }
        connection.disconnect()
        val config = JSONObject(body)
        val provider = config.optString("tts_provider", "unknown")
        val model = config.optString("tts_model", "unknown")
        val voice = config.optString("tts_voice", "unknown")
        val format = config.optString("tts_response_format", "aac")
        backendSpeechFormat = format
        val cacheKey = "speech|${BuildConfig.API_BASE_URL}|$provider|$model|$voice|$format"
        backendSpeechCacheKey = cacheKey
        cacheKey
      }
    } catch (_: Exception) {
      backendSpeechCacheKey = fallback
      fallback
    }
  }

  private fun downloadBackendSpeech(text: String): File {
    return downloadBackendSpeech(text, File(reactContext.cacheDir, "forgemind-tts-${sha256(text)}.${audioFileExtension(backendSpeechFormat)}"))
  }

  private fun downloadBackendSpeech(text: String, output: File): File {
    val connection = URL("${BuildConfig.API_BASE_URL}/speech").openConnection() as HttpURLConnection
    connection.requestMethod = "POST"
    connection.connectTimeout = 10000
    connection.readTimeout = 30000
    connection.doOutput = true
    connection.setRequestProperty("Content-Type", "application/json")
    connection.setRequestProperty("Accept", acceptedAudioType(backendSpeechFormat))

    val body = JSONObject().put("text", text).toString().toByteArray(Charsets.UTF_8)
    connection.outputStream.use { stream ->
      stream.write(body)
    }

    if (connection.responseCode !in 200..299) {
      connection.disconnect()
      throw IllegalStateException("Backend speech failed with HTTP ${connection.responseCode}")
    }

    val temporaryOutput = File(reactContext.cacheDir, "${output.name}.tmp")
    connection.inputStream.use { input ->
      temporaryOutput.writeBytes(input.readBytes())
    }
    connection.disconnect()
    if (temporaryOutput.length() == 0L) {
      temporaryOutput.delete()
      throw IllegalStateException("Backend speech returned empty audio")
    }
    if (output.exists()) {
      output.delete()
    }
    temporaryOutput.renameTo(output)
    return output
  }

  private fun playAudioFile(audioFile: File) {
    playAudioQueue(listOf(audioFile))
  }

  private fun playAudioQueue(audioFiles: List<File>) {
    stopPlayback()
    queuedAudioFiles.clear()
    queuedAudioFiles.addAll(audioFiles)
    queuedAudioComplete = true
    playAudioQueueAt(audioFiles, 0)
  }

  private fun playAudioQueueStreaming(firstAudioFile: File) {
    stopPlayback()
    queuedAudioFiles.clear()
    queuedAudioFiles.add(firstAudioFile)
    queuedAudioComplete = false
    playQueuedAudioAt(0)
  }

  private fun playQueuedAudioAt(index: Int) {
    val audioFile = queuedAudioFiles.getOrNull(index)
    if (audioFile == null) {
      if (!queuedAudioComplete) {
        handler.postDelayed({ playQueuedAudioAt(index) }, 120)
      } else {
        stopPlayback()
      }
      return
    }
    player = MediaPlayer().apply {
      setDataSource(audioFile.absolutePath)
      setOnCompletionListener {
        it.release()
        player = null
        playQueuedAudioAt(index + 1)
      }
      setOnErrorListener { _, _, _ ->
        stopPlayback()
        true
      }
      prepare()
      start()
    }
  }

  private fun playAudioQueueAt(audioFiles: List<File>, index: Int) {
    if (index >= audioFiles.size) {
      stopPlayback()
      return
    }
    player = MediaPlayer().apply {
      val audioFile = audioFiles[index]
      setDataSource(audioFile.absolutePath)
      setOnCompletionListener {
        it.release()
        player = null
        playAudioQueueAt(audioFiles, index + 1)
      }
      setOnErrorListener { _, _, _ ->
        stopPlayback()
        true
      }
      prepare()
      start()
    }
  }

  private fun sha256(text: String): String {
    val digest = MessageDigest.getInstance("SHA-256").digest(text.toByteArray(Charsets.UTF_8))
    return digest.joinToString("") { "%02x".format(it) }
  }

  private fun audioFileExtension(format: String): String {
    return when (format.lowercase(Locale.US)) {
      "mp3" -> "mp3"
      "mpeg" -> "mp3"
      "wav" -> "wav"
      "linear16" -> "wav"
      "opus" -> "opus"
      else -> "aac"
    }
  }

  private fun acceptedAudioType(format: String): String {
    return when (format.lowercase(Locale.US)) {
      "mp3" -> "audio/mpeg"
      "mpeg" -> "audio/mpeg"
      "wav" -> "audio/wav"
      "linear16" -> "audio/wav"
      "opus" -> "audio/opus"
      else -> "audio/aac"
    }
  }

  private fun speakWithDeviceTts(text: String, promise: Promise) {
    val engine = tts
    if (!ready || engine == null) {
      promise.reject("tts_unavailable", "Text to speech is not available")
      return
    }
    stopPlayback()
    engine.stop()
    engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "forgemind-tts-${System.currentTimeMillis()}")
    promise.resolve(null)
  }

  private fun stopPlayback() {
    handler.removeCallbacksAndMessages(null)
    player?.stop()
    player?.release()
    player = null
    queuedAudioFiles.clear()
    queuedAudioComplete = true
  }

  @ReactMethod
  fun stop(promise: Promise) {
    stopPlayback()
    tts?.stop()
    promise.resolve(null)
  }

  override fun invalidate() {
    stopPlayback()
    tts?.stop()
    tts?.shutdown()
    tts = null
    ready = false
    super.invalidate()
  }
}
