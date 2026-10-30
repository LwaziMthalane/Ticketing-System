[app]

title = G-Yeza Helpdesk
package.name = gyezahelpdesk
package.domain = za.co.gyeza

source.dir = .
source.include_exts = py,kv,json,txt,png,jpg

version = 1.0.0

# KivyMD master now depends on materialshapes (which needs pycairo), and
# python-for-android installs pure-python packages with --no-deps, so they must be
# listed by hand. This is the line the KivyMD README recommends for buildozer,
# with KivyMD pinned to a fixed commit so tomorrow's master can't break the build.
requirements = python3,kivy,https://github.com/kivymd/KivyMD/archive/4a2617ea24e13ef2540c37edb95a54ef02e78707.zip,materialyoucolor==3.0.3,materialshapes,pycairo,pillow,exceptiongroup,asyncgui,asynckivy

orientation = portrait
fullscreen = 0

#
# Android
#
android.api = 33
android.minapi = 21
# (str) Presplash of the application
presplash.filename = presplash.png

# (str) Icon of the application
icon.filename = icon.png

# (string) Presplash background color (for android toolchain)
# Supported formats are: #RRGGBB #AARRGGBB or one of the following names:
# red, blue, green, black, white, gray, cyan, magenta, yellow, lightgray,
# darkgray, grey, lightgrey, darkgrey, aqua, fuchsia, lime, maroon, navy,
# olive, purple, silver, teal.
android.presplash_color = #FFFFFF

# ONE architecture per build. Current python-for-android master crashes when it
# installs pip packages for a second architecture in the same run (broken pip in
# the shared venv). The GitHub workflow overrides this line per job
# (arm64-v8a and armeabi-v7a) so you still get both APKs.
android.archs = arm64-v8a

android.private_storage = True
android.allow_backup = True
android.skip_update = False
android.accept_sdk_license = True

# Consistent debug signing for updates (the workflow re-signs with this key)
android.keystore = android/debug.keystore
android.keystore.password = android
android.keyalias = androiddebugkey
android.keyalias.password = android

#
# python-for-android
#
p4a.fork = kivy
p4a.branch = master
p4a.commit = HEAD


[buildozer]

log_level = 2
warn_on_root = 1
