# Release numbering

The last published release is `0.2.5-RC1`. The next production candidate is
`0.2.5-RC2`, followed by `0.2.5-RC3` if another candidate is needed, or `0.2.5`
when the release is accepted. Feature descriptions belong in release notes.

Android's internal `versionCode` is separate from this public label. The next
build uses `128115`, higher than the previously distributed `128113` and
`128114` builds, so Android can install it as an update using the same signing
certificate. Increase this internal number for each new distributed build.

The `none` and `cpu` diagnostic variants append `-stopcpu` and `-cpu` to the
public label. The default `cpu-audio` production variant uses `0.2.5-RC2`.

Previously built APKs retain their embedded labels (`0.2.13` and `0.2.14`
with descriptive suffixes). Changing the source does not rename those APKs.
