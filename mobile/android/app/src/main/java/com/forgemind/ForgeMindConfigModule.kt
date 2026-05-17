package com.forgemind

import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule

class ForgeMindConfigModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

  override fun getName(): String = "ForgeMindConfig"

  override fun getConstants(): MutableMap<String, Any> {
    return mutableMapOf("API_BASE_URL" to BuildConfig.API_BASE_URL)
  }
}
