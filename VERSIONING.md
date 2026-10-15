# Release numbering

The last published release is `0.2.5-RC3`. The next test candidate is
`0.2.5-RC4-test5`, with Android versionCode `128122` (previous test: `128121`; published RC3: `128117`).
It uses the existing production certificate and package, so it can update an
existing RC2/RC3 installation while keeping settings and saves.

The next public release can be `0.2.5-RC4`, or `0.2.5` when accepted.
Increase the internal versionCode for each newly distributed build.
Diagnostic variants append `-stopcpu` or `-cpu`; the default cpu-audio candidate
uses `0.2.5-RC4-test5`. Existing APKs retain their embedded version labels.
