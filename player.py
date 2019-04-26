#!/usr/bin/env python3
# coding: utf8

import os
import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst as gst
import sys
import time
import requests
# Todo: поделиться треком

class Player:
    def __init__(self, gui):
        self.gui = gui
        self.is_playing = True
        gst.init(sys.argv)

        player = gst.ElementFactory.make('playbin', 'player')
        player.set_property('volume', self.gui.volume)

        sink = gst.ElementFactory.make('autoaudiosink', 'audio_sink')

        if not sink or not player:
            raise RuntimeError('Could not create GST audio pipeline')

        player.set_property('audio-sink', sink)

        self.player = player

        self.terminate = False

    def play(self, yar, track, info, batch, duration, len_last_played):
        tid, aid = track
        url = yar.gettrack(tid, aid)

        self.player.set_property('uri', url)
        self.player.set_state(gst.State.PLAYING)

        yar.started(tid, aid, batch)

        start_time = time.time()
        bus = self.player.get_bus()
        reason = 'trackFinished'

        self.gui.set_song_info(info[2], info[0], info[1], int(duration / 1000), info[3])

        while True:
            if self.gui.timeline_released:
                self.go_to_time(self.gui.timeline)
                self.gui.reset_flags()

            if not self.gui.timeline_pressed:
                ret, played_time = self.player.query_position(gst.Format.TIME)
                if played_time != 0:
                    self.gui.set_time(int(played_time / 10 ** 9))

            self.player.set_property('volume', self.gui.volume)

            msg = bus.timed_pop_filtered(100 * gst.MSECOND, gst.MessageType.ERROR | gst.MessageType.EOS)

            if self.gui.prev_clicked:
                if len_last_played >= 2:
                    break
                else:
                    self.gui.reset_flags()

            if self.gui.pause_clicked:
                self.is_playing = not self.is_playing
                if self.is_playing:
                    self.player.set_state(gst.State.PLAYING)
                else:
                    self.player.set_state(gst.State.PAUSED)
                self.gui.reset_flags()

            if self.gui.next_clicked:
                reason = 'skip'
                self.gui.reset_flags()
                break

            if self.gui.like_clicked:
                evTime = time.time()
                dur = evTime - start_time
                yar.feedback('like', dur, tid, aid, batch)
                self.gui.reset_flags()
                self.gui.set_is_liked(True)

            if self.gui.save_clicked:
                filename = "%s/saved/%s - %s.mp3" % (os.getcwd(), info[2], info[0])

                myfile = requests.get(url)
                with open(filename, "wb") as file:
                    file.write(myfile.content)
                self.gui.reset_flags()
                self.gui.set_is_saved(True)

            if self.gui.share_clicked:
                print(url)
                self.gui.reset_flags()

            if self.gui.dislike_clicked:
                reason = 'dislike'
                self.gui.reset_flags()
                break

            if msg is None:
                continue

            if msg.type == gst.MessageType.ERROR:
                break
            if msg.type == gst.MessageType.EOS:
                if self.gui.is_repeated:
                    self.go_to_time(0)
                else:
                    self.gui.set_time(0)
                    break

        self.player.set_state(gst.State.NULL)
        stop_time = time.time()
        dur = stop_time - start_time

        # print("real " + str(duration))  # Это настоящее
        # print("fact " + str(dur))  # Это фактическое
        # print("player " + str(played_time))  # Это плеера

        yar.feedback(reason, dur, tid, aid, batch)

    def go_to_time(self, seconds):
        self.player.get_state(gst.CLOCK_TIME_NONE)
        self.player.set_state(gst.State.PAUSED)
        self.player.seek_simple(gst.Format.TIME, gst.SeekFlags.FLUSH, seconds * gst.SECOND)
        self.player.get_state(gst.CLOCK_TIME_NONE)
        pos = self.player.query_position(gst.Format.TIME)[1]
        self.player.seek(1, gst.Format.TIME,
                         gst.SeekFlags.FLUSH, gst.SeekType.SET, pos,
                         gst.SeekType.NONE, -1)
        self.player.set_state(gst.State.PLAYING)
        self.gui.reset_flags()
