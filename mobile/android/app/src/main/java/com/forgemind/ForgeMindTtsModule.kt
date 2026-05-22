package com.forgemind

import android.speech.tts.TextToSpeech
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import java.util.Locale

class ForgeMindTtsModule(private val reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext), TextToSpeech.OnInitListener {

  private var tts: TextToSpeech? = null
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
    val engine = tts
    if (!ready || engine == null) {
      promise.reject("tts_unavailable", "Text to speech is not available")
      return
    }
    engine.stop()
    engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "forgemind-tts-${System.currentTimeMillis()}")
    promise.resolve(null)
  }

  @ReactMethod
  fun stop(promise: Promise) {
    tts?.stop()
    promise.resolve(null)
  }

  override fun invalidate() {
    tts?.stop()
    tts?.shutdown()
    tts = null
    ready = false
    super.invalidate()
  }
}
