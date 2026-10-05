// Copyright 2013 The Flutter Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package io.flutter.plugins.videoplayer.platformview;

import android.content.Context;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.annotation.VisibleForTesting;
import androidx.media3.common.MediaItem;
import androidx.media3.common.util.UnstableApi;
import androidx.media3.exoplayer.DefaultLoadControl;
import androidx.media3.exoplayer.ExoPlayer;
import io.flutter.plugins.videoplayer.ExoPlayerEventListener;
import io.flutter.plugins.videoplayer.VideoAsset;
import io.flutter.plugins.videoplayer.VideoPlayer;
import io.flutter.plugins.videoplayer.VideoPlayerCallbacks;
import io.flutter.plugins.videoplayer.VideoPlayerOptions;
import io.flutter.view.TextureRegistry.SurfaceProducer;

/**
 * A subclass of {@link VideoPlayer} that adds functionality related to platform view as a way of
 * displaying the video in the app.
 */
public class PlatformViewVideoPlayer extends VideoPlayer {
  // TODO: Migrate to stable API, see https://github.com/flutter/flutter/issues/147039.
  @UnstableApi
  @VisibleForTesting
  public PlatformViewVideoPlayer(
      @NonNull VideoPlayerCallbacks events,
      @NonNull MediaItem mediaItem,
      @NonNull VideoPlayerOptions options,
      @NonNull ExoPlayerProvider exoPlayerProvider) {
    super(events, mediaItem, options, /* surfaceProducer */ null, exoPlayerProvider);
  }

  /**
   * Creates a platform view video player.
   *
   * @param context application context.
   * @param events event callbacks.
   * @param asset asset to play.
   * @param options options for playback.
   * @return a video player instance.
   */
  // TODO: Migrate to stable API, see https://github.com/flutter/flutter/issues/147039.
  @UnstableApi
  @NonNull
  public static PlatformViewVideoPlayer create(
      @NonNull Context context,
      @NonNull VideoPlayerCallbacks events,
      @NonNull VideoAsset asset,
      @NonNull VideoPlayerOptions options) {
    return new PlatformViewVideoPlayer(
        events,
        asset.getMediaItem(),
        options,
        () -> {
          ExoPlayer.Builder builder = new ExoPlayer.Builder(context);
          // Kairos TV: junta 5 segundos de video antes de arrancar (y antes de
          // seguir después de un corte), en vez de los 2,5 s de fábrica. Así un
          // microcorte de la señal no se nota. Ver ../../README.md.
          DefaultLoadControl.Builder kairosBuffer =
              new DefaultLoadControl.Builder()
                  .setBufferDurationsMs(
                      DefaultLoadControl.DEFAULT_MIN_BUFFER_MS,
                      DefaultLoadControl.DEFAULT_MAX_BUFFER_MS,
                      /* bufferForPlaybackMs= */ 5000,
                      /* bufferForPlaybackAfterRebufferMs= */ 5000);
          builder.setLoadControl(kairosBuffer.build());
          if (options.backBufferDurationMs != null) {
            if (options.backBufferDurationMs < 0) {
              throw new IllegalArgumentException("backBufferDurationMs must be at least 0");
            }
            if (options.backBufferDurationMs > 0) {
              // Clamp the value to ensure it fits within the int range expected by
              // DefaultLoadControl.
              int backBufferInt =
                  (int) Math.min(options.backBufferDurationMs.longValue(), Integer.MAX_VALUE);
              DefaultLoadControl loadControl =
                  kairosBuffer
                      .setBackBuffer(backBufferInt, /* retainBackBufferFromKeyframe= */ true)
                      .build();
              builder.setLoadControl(loadControl);
            }
          }
          androidx.media3.exoplayer.trackselection.DefaultTrackSelector trackSelector =
              new androidx.media3.exoplayer.trackselection.DefaultTrackSelector(context);
          builder
              .setTrackSelector(trackSelector)
              .setMediaSourceFactory(asset.getMediaSourceFactory(context));
          return builder.build();
        });
  }

  @NonNull
  @Override
  protected ExoPlayerEventListener createExoPlayerEventListener(
      @NonNull ExoPlayer exoPlayer, @Nullable SurfaceProducer surfaceProducer) {
    return new PlatformViewExoPlayerEventListener(exoPlayer, videoPlayerEvents);
  }
}
