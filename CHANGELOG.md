# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Embed base64-encoded images inline. Support starting with JPEG and BMP.
  ([#99](https://github.com/HazyResearch/pdftotree/pull/99), [@HiromuHota][HiromuHota])

### Fixed
- List a missing "ocrx_line" in the ocr-capabilities metadata field.
  ([#94](https://github.com/HazyResearch/pdftotree/issues/94), [@HiromuHota][HiromuHota])
- Use the centroid for `isContained` check not to miss cell values.
  ([#96](https://github.com/HazyResearch/pdftotree/issues/96), [@HiromuHota][HiromuHota])
- Treat non-breaking space as a white space to prevent "Out of order" warnings.
  ([#98](https://github.com/HazyResearch/pdftotree/pull/98), [@HiromuHota][HiromuHota])
- Escape text only once.
  ([#100](https://github.com/HazyResearch/pdftotree/pull/100), [@HiromuHota][HiromuHota])

## 0.5.0 - 2020-10-13

### Added
- Support for Python 3.8.
  ([#86](https://github.com/HazyResearch/pdftotree/pull/86), [@HiromuHota][HiromuHota])

### Changed
- Switch the output format from "HTML-like" to hOCR.
  ([#62](https://github.com/HazyResearch/pdftotree/pull/62), [@HiromuHota][HiromuHota])
- Loosen Keras' version restriction, which is now unnecessarily strict.
  ([#68](https://github.com/HazyResearch/pdftotree/pull/68), [@HiromuHota][HiromuHota])
- Greedily extract contents from PDF even if it looks scanned.
  ([#71](https://github.com/HazyResearch/pdftotree/pull/71), [@HiromuHota][HiromuHota])
- Upgrade Keras to 2.4.0 or later (and TensorFlow 2.2 or later).
  ([#86](https://github.com/HazyResearch/pdftotree/pull/86), [@HiromuHota][HiromuHota])

### Removed
- Remove "favor_figures" option and extract everything.
  ([#77](https://github.com/HazyResearch/pdftotree/pull/77), [@HiromuHota][HiromuHota])
- Remove "dry_run" option.
  ([#89](https://github.com/HazyResearch/pdftotree/pull/89), [@HiromuHota][HiromuHota])

### Fixed
- Fix a bug that an html file is not created at a given path.
  ([#64](https://github.com/HazyResearch/pdftotree/pull/64), [@HiromuHota][HiromuHota])
- Extract LTChar even if they are not children of LTTextLine.
  ([#79](https://github.com/HazyResearch/pdftotree/pull/79), [@HiromuHota][HiromuHota])

## 0.4.1 - 2020-09-21

### Fixed
- Temporarily add `chardet` to requirements until
  [pdfminer/pdfminer.six#213](https://github.com/pdfminer/pdfminer.six/issues/213) is fixed.
  ([#47](https://github.com/HazyResearch/pdftotree/issues/47), [@lukehsiao][lh])
- Fix ValueError when a Node instance is a single element.
  ([#49](https://github.com/HazyResearch/pdftotree/pull/49), [@mgoo][mgoo])

[lh]: https://github.com/lukehsiao
[mgoo]: https://github.com/mgoo
[HiromuHota]: https://github.com/HiromuHota